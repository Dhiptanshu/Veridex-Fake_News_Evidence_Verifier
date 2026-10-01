"""Serve the built frontend (frontend/dist) from the API, so one process / one container runs the whole app."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.nlp import resources

DEFAULT_DIST = resources.ROOT / "frontend" / "dist"


def mount_frontend(app: FastAPI, directory: Path | None = None) -> bool:
    """Mount the SPA at '/'. Call after the API routers so /api/* keeps priority. Returns False if nothing is built."""
    directory = directory or DEFAULT_DIST
    if not (directory / "index.html").exists():
        return False
    app.mount("/", StaticFiles(directory=directory, html=True), name="frontend")
    return True
