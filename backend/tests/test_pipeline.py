import json

from fastapi.testclient import TestClient

from app.main import app
from app.pipeline.orchestrator import run_pipeline
from app.schemas.pipeline import SLOTS, VerifyRequest


async def _collect(req):
    return [ev async for ev in run_pipeline(req)]


def _out(events, slot):
    return next(e for e in events if e.type == "stage_end" and e.slot == slot).payload


async def test_all_slots_run_in_order():
    events = await _collect(VerifyRequest(claim="Marie Curie won two Nobel Prizes."))
    assert events[0].type == "pipeline_start" and events[-1].type == "pipeline_end"
    assert [e.slot for e in events if e.type == "stage_end"] == SLOTS


async def test_stage_outputs_flow_through_to_retrieval():
    events = await _collect(VerifyRequest(claim="Marie Curie won two Nobel Prizes."))
    assert "Marie Curie" in [e["text"] for e in _out(events, "ner")["entities"]]
    assert "Marie Curie" in _out(events, "keywords")["query"]
    evidence = _out(events, "retrieval")["evidence"]
    assert evidence[0]["title"] == "Marie Curie"
    assert any("Nobel Prize" in s["text"] for s in evidence[0]["sentences"])
    assert evidence[0]["url"] == "https://en.wikipedia.org/wiki/Marie_Curie"


async def test_paren_titles_get_clean_urls():
    events = await _collect(VerifyRequest(claim="Fox 2000 Pictures released the film Soul Food."))
    ev = _out(events, "retrieval")["evidence"][0]
    assert ev["title"] == "Soul Food (film)"
    assert ev["url"] == "https://en.wikipedia.org/wiki/Soul_Food_%28film%29"


async def test_alternative_implementations_are_selectable():
    req = VerifyRequest(
        claim="Paris is the capital of France.",
        options={"preprocess": "regex", "ner": "capitalized", "keywords": "frequency", "retrieval": "tfidf_plain"},
    )
    events = await _collect(req)
    assert [e.impl for e in events if e.type == "stage_end"][:4] == ["regex", "capitalized", "frequency", "tfidf_plain"]
    assert _out(events, "retrieval")["evidence"][0]["title"] == "Paris"


async def test_unknown_impl_yields_error_event():
    events = await _collect(VerifyRequest(claim="anything here", options={"ner": "nope"}))
    assert [e.type for e in events] == ["error"]


def test_stages_catalog_has_one_default_per_slot():
    data = TestClient(app).get("/api/stages").json()
    for slot in SLOTS:
        assert sum(1 for s in data if s["slot"] == slot and s["is_default"]) == 1
    assert {s["name"] for s in data if s["slot"] == "keywords"} == {"tfidf", "tfidf_pmi", "frequency"}
    assert {s["name"] for s in data if s["slot"] == "retrieval"} >= {"dense_bge", "tfidf", "wordvec_w2v", "hybrid_minilm"}


def test_sse_stream_format():
    with TestClient(app).stream("POST", "/api/verify/stream", json={"claim": "Water boils at 100C."}) as r:
        assert r.headers["content-type"].startswith("text/event-stream")
        events = [json.loads(line[6:]) for line in r.iter_lines() if line.startswith("data: ")]
    assert events[-1]["type"] == "pipeline_end"


def test_validation_rejects_short_claim():
    assert TestClient(app).post("/api/verify", json={"claim": "x"}).status_code == 422
