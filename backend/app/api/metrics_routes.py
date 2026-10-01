"""Serves the saved evaluation results (docs/results/*.json) to the Insights tab, unchanged."""
import json
from pathlib import Path

from fastapi import APIRouter

from app.nlp import resources

router = APIRouter(prefix="/api", tags=["metrics"])

RESULTS_DIR = resources.ROOT / "docs" / "results"

# response key -> file. A missing file is simply omitted so the UI can hide that section.
FILES = {
    "claim_only": "claim_only_baseline.json",
    "retrieval_tfidf": "retrieval_tfidf.json",
    "retrieval_semantic": "retrieval_semantic.json",
    "title_bonus": "retrieval_title_bonus.json",
    "verification": "verification.json",
    "stacker": "verification_stacker.json",
    "aggregation": "verification_aggregation.json",
    "history": "verification_history.json",
    "explanation": "explanation.json",
    "topics": "topics.json",
}


def load_results(directory: Path = RESULTS_DIR) -> dict:
    out = {}
    for key, name in FILES.items():
        path = directory / name
        if path.exists():
            out[key] = json.loads(path.read_text(encoding="utf-8"))
    return out


@router.get("/metrics")
def metrics() -> dict:
    return load_results()
