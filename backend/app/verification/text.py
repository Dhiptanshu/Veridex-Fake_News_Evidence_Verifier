"""How evidence is turned into model input. Must stay identical to `fmt_evidence` in ml/kaggle/verify/train.py."""
from pathlib import Path

from app.nlp import resources

LABELS = ["supported", "refuted", "not_enough_info"]
MODEL_DIR = resources.ROOT / "data" / "models"
MAX_EVIDENCE = 5  # sentences fed to the verifier, best first


def fmt_evidence(items: list[dict]) -> str:
    return " ".join(f"{i['title']}: {i['text']}" for i in items)


def model_path(name: str, base: Path | None = None) -> Path:
    return (base or MODEL_DIR) / name
