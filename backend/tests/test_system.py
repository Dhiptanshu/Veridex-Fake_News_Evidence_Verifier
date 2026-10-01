import json

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


def test_status_lists_resources_and_services_with_fix_hints(monkeypatch):
    monkeypatch.setattr(settings, "gnews_api_key", "")
    data = TestClient(app).get("/api/system/status").json()
    assert {"bert", "stacker", "tfidf", "qa"} <= {c["key"] for c in data["resources"]}
    gnews = next(c for c in data["services"] if c["key"] == "gnews")
    assert gnews["ready"] is False and "FNEV_GNEWS_API_KEY" in gnews["fix"]
    missing = [c for c in data["resources"] if not c["ready"]]
    assert all(c["fix"] for c in missing)  # every missing resource says how to build it


def test_status_never_contains_key_values(monkeypatch):
    for name, secret in (("gnews_api_key", "sk-gnews-secret-1"), ("newsapi_key", "sk-news-secret-2"),
                         ("aicredits_api_key", "sk-ai-secret-3"), ("wikipedia_contact", "me@secret-contact.test")):
        monkeypatch.setattr(settings, name, secret)
    body = TestClient(app).get("/api/system/status").text
    assert "secret" not in body
    services = {c["key"]: c for c in json.loads(body)["services"]}
    assert all(services[k]["ready"] for k in ("gnews", "newsapi", "aicredits", "wikipedia"))
