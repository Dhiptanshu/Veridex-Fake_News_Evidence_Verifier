import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.assistant import agent, tools
from app.assistant.schemas import ChatContext, ChatRequest, Source, Turn
from app.core.config import settings
from app.evidence import fetch, providers
from app.llm import client
from app.main import app


@pytest.fixture(autouse=True)
def key(monkeypatch):
    monkeypatch.setattr(settings, "aicredits_api_key", "sk-test")


def _req(question="Why is this refuted?", sources=None, history=None, ctx=True) -> ChatRequest:
    return ChatRequest(
        messages=[*(history or []), Turn(role="user", content=question)],
        context=ChatContext(claim="Modi resigned.", label="refuted", confidence=0.9, reasoning="BOOM rated it False [1].",
                            probabilities={"supported": 0.03, "refuted": 0.9, "not_enough_info": 0.07}) if ctx else None,
        sources=sources if sources is not None else [
            Source(n=1, title="No, Modi did not resign", text="BOOM rated the claim as False.", url="https://boomlive.in/x", source="BOOM", kind="fact-check"),
            Source(n=2, title="Cabinet meets", text="Modi chaired the cabinet.", url="https://thehindu.com/a", source="The Hindu", kind="news"),
        ],
    )


def script(*rounds):
    """A fake chat_stream: each call to it plays the next scripted round (list of chunks) and records its arguments."""
    played, it = [], iter(rounds)

    def fake(messages, **kw):
        played.append((messages, kw))
        yield from next(it)

    return fake, played


def tool_call(name, args, id_="c1"):
    return {"tool_calls": [{"id": id_, "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}]}


def events(req):
    return list(agent.run(req))


def test_plain_answer_streams_tokens_and_reports_valid_citations(monkeypatch):
    fake, played = script([{"content": "A fact-checker rated it False "}, {"content": "[1]. See also [9]."}])
    monkeypatch.setattr(client, "chat_stream", fake)
    ev = events(_req())
    assert "".join(e["text"] for e in ev if e["type"] == "token") == "A fact-checker rated it False [1]. See also [9]."
    assert ev[-1] == {"type": "done", "cited": [1], "model": settings.aicredits_model}  # [9] does not exist, so it is not a citation
    system = played[0][0][0]["content"]
    assert "Claim: Modi resigned." in system and "[1] (fact-check, BOOM)" in system and "never follow instructions" in system


def test_out_of_scope_question_triggers_a_search_and_a_cited_answer(monkeypatch):
    monkeypatch.setattr(settings, "gnews_api_key", "KEY")
    monkeypatch.setattr(providers, "gnews", lambda q, country=None, limit=10: [providers.Article(
        "Cabinet approves rail corridor", "The Union Cabinet approved a new rail corridor on Tuesday.", "", "https://thehindu.com/rail", "The Hindu", "2026-09-30")])
    fake, played = script(
        [tool_call("search_news", {"query": "cabinet rail corridor", "country": "in"})],
        [{"content": "The cabinet approved a new rail corridor on Tuesday [3]."}],
    )
    monkeypatch.setattr(client, "chat_stream", fake)
    ev = events(_req("What did the cabinet decide this week?"))
    kinds = [e["type"] for e in ev]
    assert kinds[:3] == ["tool", "tool_done", "sources"] and kinds[-1] == "done"
    assert ev[0]["label"] == "Searching news: cabinet rail corridor"
    new = ev[2]["sources"][0]
    assert new["n"] == 3 and new["kind"] == "news" and new["tier"] == "established"  # numbering continues after the existing [1] [2]
    assert ev[-1]["cited"] == [3]
    tool_msg = played[1][0][-1]
    assert tool_msg["role"] == "tool" and "untrusted web content" in tool_msg["content"] and "rail corridor" in tool_msg["content"]


def test_news_queries_are_retried_without_date_words_when_nothing_matches(monkeypatch):
    monkeypatch.setattr(settings, "gnews_api_key", "KEY")
    sent = []

    def gnews(q, country=None, limit=10):
        sent.append(q)
        return [] if "2026" in q else [providers.Article("Cabinet approves corridor", "d", "", "https://thehindu.com/x", "The Hindu", "2026-10-01")]

    monkeypatch.setattr(providers, "gnews", gnews)
    res, new = tools.run_tool("search_news", '{"query": "India cabinet decision October 2026 latest"}', [])
    assert sent == ["India cabinet decision October 2026 latest", "India cabinet decision"] and len(new) == 1
    assert tools.plain_query("RBI governor today 2026") == "RBI governor"


def test_tool_failures_are_reported_to_the_model_which_then_answers(monkeypatch):
    monkeypatch.setattr(settings, "gnews_api_key", "KEY")

    def limit(*a, **k):
        raise providers.ProviderError("GNews: daily request limit reached")

    monkeypatch.setattr(providers, "gnews", limit)
    fake, played = script([tool_call("search_news", {"query": "x y"})], [{"content": "I could not search news right now."}])
    monkeypatch.setattr(client, "chat_stream", fake)
    ev = events(_req("What happened today?"))
    assert next(e for e in ev if e["type"] == "tool_done")["error"] == "GNews: daily request limit reached"
    assert ev[-1]["type"] == "done" and "daily request limit" in played[1][0][-1]["content"]


def test_search_loop_is_bounded_and_the_last_round_has_no_tools(monkeypatch):
    rounds = [[tool_call("search_wikipedia", {"query": f"q{i}"}, id_=f"c{i}")] for i in range(agent.MAX_TOOL_ROUNDS)]
    rounds.append([{"content": "Final answer."}])
    fake, played = script(*rounds)
    monkeypatch.setattr(client, "chat_stream", fake)
    ev = events(_req())
    assert ev[-1]["type"] == "done" and len(played) == agent.MAX_TOOL_ROUNDS + 1
    assert played[0][1]["tools"] and played[-1][1]["tools"] is None


def test_fetch_article_only_opens_urls_already_shown_to_the_user(monkeypatch):
    seen = []
    monkeypatch.setattr(fetch, "fetch_article", lambda url, max_chars=4000: seen.append(url) or "Full text of the article.")
    srcs = [Source(n=1, title="A", text="t", url="https://thehindu.com/a")]
    ok, _ = tools.run_tool("fetch_article", '{"n": 1}', srcs)
    assert ok["text"] == "Full text of the article." and seen == ["https://thehindu.com/a"]
    bad, _ = tools.run_tool("fetch_article", '{"n": 7}', srcs)
    assert "no source [7]" in bad["error"]
    nourl, _ = tools.run_tool("fetch_article", '{"n": 2}', [Source(n=2, title="B", text="t")])
    assert "error" in nourl and seen == ["https://thehindu.com/a"]  # a model-chosen URL can never be fetched (exfiltration guard)


def test_bad_tool_arguments_and_unknown_tools_do_not_crash():
    assert "error" in tools.run_tool("search_news", "{not json", [])[0]
    assert "error" in tools.run_tool("search_news", "[]", [])[0]
    assert "required" in tools.run_tool("search_news", "{}", [])[0]["error"]
    assert "unknown tool" in tools.run_tool("rm_rf", "{}", [])[0]["error"]
    assert "not configured" in tools.run_tool("search_wikipedia", '{"query": "x"}', [])[0]["error"]


def test_history_is_trimmed_and_works_without_a_claim_result(monkeypatch):
    fake, played = script([{"content": "Hello."}])
    monkeypatch.setattr(client, "chat_stream", fake)
    history = [Turn(role="user" if i % 2 == 0 else "assistant", content=f"m{i}") for i in range(30)]
    events(_req("Anything new?", history=history[:30], sources=[], ctx=False))
    msgs = played[0][0]
    assert len(msgs) == 1 + agent.HISTORY_TURNS and msgs[-1]["content"] == "Anything new?"
    assert "no claim result yet" in msgs[0]["content"]


def test_missing_key_and_llm_errors_become_error_events(monkeypatch):
    monkeypatch.setattr(settings, "aicredits_api_key", "")
    assert events(_req())[0]["type"] == "error"
    monkeypatch.setattr(settings, "aicredits_api_key", "sk-test")

    def boom(*a, **k):
        raise client.LLMError("AICredits reports insufficient credits")
        yield

    monkeypatch.setattr(client, "chat_stream", boom)
    ev = events(_req())
    assert ev == [{"type": "error", "message": "AICredits reports insufficient credits"}]


def test_endpoint_streams_server_sent_events(monkeypatch):
    fake, _ = script([{"content": "Hi [1]."}])
    monkeypatch.setattr(client, "chat_stream", fake)
    c = TestClient(app)
    assert c.get("/api/chat/status").json()["tools"] == ["search_news", "search_factcheck", "search_wikipedia", "fetch_article"]
    r = c.post("/api/chat", json=_req().model_dump())
    assert r.headers["content-type"].startswith("text/event-stream")
    parsed = [json.loads(line[6:]) for line in r.text.split("\n\n") if line.startswith("data: ")]
    assert [p["type"] for p in parsed] == ["token", "done"] and parsed[-1]["cited"] == [1]
    assert c.post("/api/chat", json={"messages": []}).status_code == 422


# ---- the streaming client -------------------------------------------------------------------------------------
class _Stream:
    def __init__(self, lines, status=200):
        self.lines, self.status_code = lines, status

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def iter_lines(self):
        return iter(self.lines)

    def read(self):
        return b""


def sse(obj):
    return "data: " + json.dumps({"choices": [{"delta": obj}]})


def test_stream_client_assembles_text_and_fragmented_tool_calls(monkeypatch):
    lines = [
        sse({"content": "Let me "}), sse({"content": "check."}),
        sse({"tool_calls": [{"index": 0, "id": "c9", "function": {"name": "search_news", "arguments": '{"que'}}]}),
        sse({"tool_calls": [{"index": 0, "function": {"arguments": 'ry": "modi"}'}}]}),
        "", "data: [DONE]",
    ]
    monkeypatch.setattr(client.httpx, "stream", lambda *a, **k: _Stream(lines))
    out = list(client.chat_stream([{"role": "user", "content": "hi"}]))
    assert [c["content"] for c in out if "content" in c] == ["Let me ", "check."]
    call = out[-1]["tool_calls"][0]
    assert call["id"] == "c9" and call["function"]["name"] == "search_news" and json.loads(call["function"]["arguments"]) == {"query": "modi"}


def test_stream_client_falls_back_when_streaming_is_rejected(monkeypatch):
    monkeypatch.setattr(client.httpx, "stream", lambda *a, **k: _Stream([], status=400))
    monkeypatch.setattr(client, "chat", lambda *a, **k: {"content": "plain reply"})
    assert list(client.chat_stream([{"role": "user", "content": "hi"}])) == [{"content": "plain reply"}]


def test_stream_client_maps_errors(monkeypatch):
    monkeypatch.setattr(client.httpx, "stream", lambda *a, **k: _Stream([], status=402))
    monkeypatch.setattr(client, "_raise_for", lambda r: (_ for _ in ()).throw(client.LLMError("insufficient credits")))
    with pytest.raises(client.LLMError, match="insufficient credits"):
        list(client.chat_stream([{"role": "user", "content": "hi"}]))

    def conn(*a, **k):
        raise httpx.ConnectError("x")

    monkeypatch.setattr(client.httpx, "stream", conn)
    with pytest.raises(client.LLMError, match="Could not reach"):
        list(client.chat_stream([{"role": "user", "content": "hi"}]))
