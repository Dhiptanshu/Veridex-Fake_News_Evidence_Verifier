from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.static import mount_frontend


def test_nothing_is_mounted_when_the_frontend_is_not_built(tmp_path):
    assert mount_frontend(FastAPI(), tmp_path) is False


def test_built_frontend_is_served_but_api_routes_keep_priority(tmp_path):
    (tmp_path / "index.html").write_text("<html>app</html>")
    (tmp_path / "app.js").write_text("console.log(1)")
    app = FastAPI()

    @app.get("/api/ping")
    def ping():
        return {"ok": True}

    assert mount_frontend(app, tmp_path) is True
    c = TestClient(app)
    assert c.get("/").text == "<html>app</html>"
    assert c.get("/app.js").status_code == 200
    assert c.get("/api/ping").json() == {"ok": True}
