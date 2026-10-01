import httpx
import pytest

from app.core.config import settings
from app.pipeline.orchestrator import run_pipeline
from app.retrieval import hybrid, live
from app.schemas.pipeline import VerifyRequest

INTROS = {
    "Marie Curie": "Marie Curie was a Polish physicist and chemist. She won the Nobel Prize in Physics in 1903. She also won the Nobel Prize in Chemistry in 1911.",
    "Paris": "Paris is the capital and most populous city of France. The city lies on the river Seine and is a global centre of art.",
}


@pytest.fixture()
def fake_wikipedia(monkeypatch):
    calls = []

    def fake_get(params):
        calls.append(params)
        if params.get("list") == "search":
            return {"query": {"search": [{"title": "Marie Curie"}, {"title": "Paris"}]}}
        wanted = params["titles"].split("|")
        return {"query": {"pages": [{"title": t, "extract": INTROS[t]} for t in wanted if t in INTROS]}}

    monkeypatch.setattr(live, "_get", fake_get)
    return calls


def test_intro_sentences_drops_fragments_and_caps_length():
    s = live.intro_sentences("Hi there. This one is a proper sentence. " + "Word " * 5 + ". " * 30)
    assert "Hi there." not in s and "This one is a proper sentence." in s


def test_live_search_ranks_sentences_and_groups_them_by_page(tiny_resources, fake_wikipedia):
    out = live.live_search(hybrid.get_resources(), "Marie Curie won the Nobel Prize in Chemistry", ["Marie Curie"], project=False)
    assert out.evidence[0].title == "Marie Curie"
    assert out.evidence[0].url == "https://en.wikipedia.org/wiki/Marie_Curie"
    assert out.evidence[0].source == "wikipedia (live)"
    assert "Chemistry" in out.evidence[0].sentences[0].text
    assert sum(len(e.sentences) for e in out.evidence) == 5
    assert any(c.get("list") == "search" for c in fake_wikipedia)


def test_live_search_refuses_to_run_without_contact_details(monkeypatch):
    monkeypatch.setattr(settings, "wikipedia_contact", "")
    with pytest.raises(RuntimeError, match="FNEV_WIKIPEDIA_CONTACT"):
        live.search_titles("anything")


def test_user_agent_carries_the_configured_contact(monkeypatch):
    monkeypatch.setattr(settings, "wikipedia_contact", "someone@example.org")
    assert "someone@example.org" in live._headers()["User-Agent"]


def test_network_failure_becomes_a_clear_error(monkeypatch):
    monkeypatch.setattr(settings, "wikipedia_contact", "someone@example.org")

    def boom(*a, **k):
        raise httpx.ConnectError("no network")

    monkeypatch.setattr(live.httpx, "get", boom)
    with pytest.raises(RuntimeError, match="Could not reach Wikipedia"):
        live.search_titles("anything")


async def test_pipeline_runs_end_to_end_in_live_mode(tiny_resources, fake_wikipedia):
    events = [e async for e in run_pipeline(VerifyRequest(claim="Marie Curie won the Nobel Prize.", options={"retrieval": "live_wikipedia"}))]
    assert events[-1].type == "pipeline_end"
    ret = next(e for e in events if e.type == "stage_end" and e.slot == "retrieval").payload
    assert ret["evidence"][0]["source"] == "wikipedia (live)"
    assert next(e for e in events if e.type == "stage_end" and e.slot == "explanation").payload["citations"]
