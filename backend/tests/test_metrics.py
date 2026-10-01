import json

from fastapi.testclient import TestClient

from app.api.metrics_routes import FILES, load_results
from app.main import app


def test_load_results_skips_missing_files_and_returns_parsed_json(tmp_path):
    (tmp_path / FILES["topics"]).write_text(json.dumps({"n_topics": 20}))
    assert load_results(tmp_path) == {"topics": {"n_topics": 20}}


def test_metrics_endpoint_serves_the_committed_results():
    data = TestClient(app).get("/api/metrics").json()
    assert {"verification", "stacker", "history", "retrieval_semantic"} <= data.keys()
    t = data["stacker"]["test"]
    assert 0.5 < t["accuracy"] < 1 and len(t["confusion_matrix"]["rows_true_cols_pred"]) == 3
