import json

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.pipeline.orchestrator import run_pipeline
from app.schemas.pipeline import SLOTS, VerifyRequest

settings.placeholder_delay_s = 0


async def _collect(req):
    return [ev async for ev in run_pipeline(req)]


async def test_all_slots_run_in_order():
    events = await _collect(VerifyRequest(claim="Paris is the capital of France."))
    assert events[0].type == "pipeline_start" and events[-1].type == "pipeline_end"
    assert [e.slot for e in events if e.type == "stage_end"] == SLOTS


async def test_entities_and_query_flow_between_stages():
    events = await _collect(VerifyRequest(claim="Marie Curie won the Nobel Prize."))
    ner = next(e for e in events if e.type == "stage_end" and e.slot == "ner")
    assert "Marie Curie" in [x["text"] for x in ner.payload["entities"]]
    kw = next(e for e in events if e.type == "stage_end" and e.slot == "keywords")
    assert "Marie Curie" in kw.payload["query"]


async def test_unknown_impl_yields_error_event():
    events = await _collect(VerifyRequest(claim="anything here", options={"ner": "nope"}))
    assert [e.type for e in events] == ["error"]


def test_stages_catalog_has_one_default_per_slot():
    data = TestClient(app).get("/api/stages").json()
    for slot in SLOTS:
        assert sum(1 for s in data if s["slot"] == slot and s["is_default"]) == 1


def test_sse_stream_format():
    with TestClient(app).stream("POST", "/api/verify/stream", json={"claim": "Water boils at 100C."}) as r:
        assert r.headers["content-type"].startswith("text/event-stream")
        events = [json.loads(line[6:]) for line in r.iter_lines() if line.startswith("data: ")]
    assert events[-1]["type"] == "pipeline_end"


def test_validation_rejects_short_claim():
    assert TestClient(app).post("/api/verify", json={"claim": "x"}).status_code == 422
