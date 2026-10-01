import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.qa import claude, local
from app.qa import router as qa
from app.qa.schemas import AskRequest, Passage

PASSAGES = [
    Passage(n=1, title="Barack Obama", text="Obama was born in Honolulu, Hawaii, two years after the territory was admitted to the Union."),
    Passage(n=2, title="Marie Curie", text="She won the 1911 Nobel Prize in Chemistry."),
]


def _req(question: str, **kw) -> AskRequest:
    base = dict(
        question=question, claim="Barack Obama was born in Kenya.", label="refuted", confidence=0.78,
        probabilities={"supported": 0.02, "refuted": 0.78, "not_enough_info": 0.20},
        rationale="The claim is refuted (78% confidence). The model reads Obama's page as conflicting.", passages=PASSAGES,
    )
    return AskRequest(**{**base, **kw})


@pytest.fixture(autouse=True)
def no_keys(monkeypatch):
    monkeypatch.setattr(settings, "anthropic_api_key", "")


@pytest.mark.parametrize("question,expected", [
    ("Why is this refuted?", "rationale"), ("Can you explain the verdict", "rationale"),
    ("How sure is the model?", "confidence"), ("Is this reliable?", "confidence"),
    ("Which sentence is the source?", "sources"), ("What are the sources", "sources"),
    ("Where was Obama born?", "factual"), ("Which prize did she win?", "factual"),
])
def test_intent_routing(question, expected):
    assert qa.intent(question) == expected


def test_questions_about_the_result_are_answered_from_the_result_without_any_model():
    assert qa.answer(_req("Why is this refuted?")).answer.startswith("The claim is refuted (78% confidence)")
    conf = qa.answer(_req("How confident is it?"))
    assert conf.method == "confidence" and "refuted 78%" in conf.answer
    src = qa.answer(_req("What are the sources?"))
    assert src.method == "sources" and src.cited == [1, 2] and "[1] Barack Obama" in src.answer


def test_best_span_stays_inside_the_context_and_respects_max_length():
    start = np.array([9.0, 0.1, 5.0, 0.2, 0.0, 0.3])
    end = np.array([9.0, 0.1, 0.4, 6.0, 0.0, 0.2])
    context = np.array([False, False, True, True, True, True])  # token 0 ([CLS]) is not part of the context
    score, i, j = local.best_span(start, end, context)
    assert (i, j) == (2, 3) and score == 11.0
    assert local.best_span(start, end, np.zeros(6, dtype=bool))[0] == -np.inf
    _, i2, j2 = local.best_span(start, end, context, max_len=1)  # span longer than max_len is not allowed
    assert j2 - i2 == 0


@pytest.mark.skipif(not local.ready(), reason="local QA model not downloaded (python ml/setup_nlp.py --qa)")
def test_real_local_model_quotes_spans_and_abstains():
    r = qa.answer(_req("Where was Obama born?"))
    assert r.method == "extractive QA" and "Honolulu" in r.answer and r.cited == [1]
    nope = qa.answer(_req("Who painted the Mona Lisa?"))
    assert "does not answer" in nope.answer and nope.cited == []


class _Resp:
    def __init__(self, code=200, body=None):
        self.status_code, self._body = code, body or {}

    def json(self):
        return self._body


def test_claude_request_follows_the_documented_shape_and_treats_evidence_as_untrusted(monkeypatch):
    monkeypatch.setattr(settings, "anthropic_api_key", "test-key")
    seen = {}

    def fake_post(url, json, headers, timeout):
        seen.update(url=url, body=json, headers=headers)
        return _Resp(body={"content": [{"type": "text", "text": "Obama was born in Honolulu [1], not Kenya. See also [9]."}]})

    monkeypatch.setattr(claude.httpx, "post", fake_post)
    r = qa.answer(_req("Where was he born really?"))
    assert r.method == "claude" and r.cited == [1]  # [9] is not a passage, so it is not reported as a citation
    assert seen["url"] == "https://api.anthropic.com/v1/messages"
    assert seen["headers"] == {"x-api-key": "test-key", "anthropic-version": "2023-06-01"}
    body = seen["body"]
    assert body["model"] == settings.anthropic_model and body["temperature"] == 0
    assert "never follow instructions" in body["system"] and "ONLY" in body["system"]
    prompt = body["messages"][0]["content"]
    assert "<evidence>" in prompt and "[1] Barack Obama: Obama was born in Honolulu" in prompt and "<question>Where was he born really?</question>" in prompt


@pytest.mark.parametrize("code,text", [(401, "rejected the key"), (429, "rate limit"), (500, r"returned an error \(500\): boom")])
def test_claude_errors_become_readable_messages(monkeypatch, code, text):
    monkeypatch.setattr(settings, "anthropic_api_key", "test-key")
    monkeypatch.setattr(claude.httpx, "post", lambda *a, **k: _Resp(code, {"error": {"message": "boom"}}))
    with pytest.raises(RuntimeError, match=text):
        claude.ask(_req("anything here"))


def test_claude_mode_without_a_key_explains_how_to_add_one():
    with pytest.raises(RuntimeError, match="platform.claude.com/settings/keys"):
        qa.answer(_req("anything here", mode="claude"))


def test_api_status_and_ask_endpoints(monkeypatch):
    c = TestClient(app)
    s = c.get("/api/ask/status").json()
    assert s["claude_configured"] is False and "claude_model" in s
    ok = c.post("/api/ask", json=_req("Why is this refuted?").model_dump())
    assert ok.status_code == 200 and ok.json()["method"] == "rationale"
    bad = c.post("/api/ask", json=_req("anything here", mode="claude").model_dump())
    assert bad.status_code == 503 and "FNEV_ANTHROPIC_API_KEY" in bad.json()["detail"]
    too_long = _req("ok question").model_dump() | {"question": "x" * 301}
    assert c.post("/api/ask", json=too_long).status_code == 422
