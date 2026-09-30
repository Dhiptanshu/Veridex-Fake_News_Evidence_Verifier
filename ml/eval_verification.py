"""Score the trained verification models from the Kaggle kernel's saved predictions.

    python ml/eval_verification.py [--preds data/kaggle/verify_out]

Reads preds_<model>_<split>_<mode>.npy + history.json from the kernel output and verif_<split>.jsonl from
data/processed. "retrieved" = evidence from our retriever (the real pipeline); "oracle" = gold evidence for
supported/refuted claims (upper bound). The claim-only baseline is scored on the same test claims.
Writes docs/results/verification.json and docs/results/verification_history.json.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.eval import classification as cl  # noqa: E402
from app.verification.text import LABELS  # noqa: E402

MODELS = {"bert": "BERT (fine-tuned)", "lstm": "BiLSTM + GloVe", "gru": "BiGRU + GloVe"}


def load_rows(split: str) -> list[dict]:
    with (ROOT / "data" / "processed" / f"verif_{split}.jsonl").open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh]


def score(rows: list[dict], probs: np.ndarray, with_fever: bool) -> dict:
    y = [LABELS.index(r["label"]) for r in rows]
    pred = probs.argmax(axis=1)
    names = [LABELS[i] for i in pred]
    m = cl.report([r["label"] for r in rows], names)
    m["cross_entropy"] = round(cl.cross_entropy(y, probs), 4)
    m["ece"] = round(cl.expected_calibration_error(y, probs), 4)
    if with_fever:
        m["fever_score"] = round(cl.fever_score([r["label"] for r in rows], names, [r["gold_retrieved"] for r in rows]), 4)
    return m


def scale(probs: np.ndarray, T: float) -> np.ndarray:
    z = np.log(np.clip(probs, 1e-12, 1.0)) / T
    z -= z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def fit_temperature(rows: list[dict], probs: np.ndarray) -> float:
    """Temperature that minimises cross-entropy on the validation split (one parameter, so it cannot overfit much)."""
    y = [LABELS.index(r["label"]) for r in rows]
    return float(min(np.arange(0.5, 4.01, 0.05), key=lambda T: cl.cross_entropy(y, scale(probs, T))))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preds", type=Path, default=ROOT / "data" / "kaggle" / "verify_out")
    a = ap.parse_args()

    splits = {s: load_rows(s) for s in ("val", "test")}
    sr = [r for r in splits["test"] if r["label"] != "not_enough_info"]
    out: dict = {
        "test_claims": len(splits["test"]),
        "retrieval_ceiling": {
            "gold_fully_retrieved_supported_refuted": round(sum(r["gold_retrieved"] for r in sr) / len(sr), 4),
            "note": "share of supported/refuted test claims whose whole gold evidence set is in the retrieved top 5",
        },
        "chance_accuracy": round(1 / 3, 4),
        "models": {},
    }

    import joblib

    claim_only = joblib.load(ROOT / "data" / "models" / "claim_only.joblib")
    order = [list(claim_only.classes_).index(label) for label in LABELS]
    cprobs = claim_only.predict_proba([r["claim"] for r in splits["test"]])[:, order]
    out["models"]["claim_only"] = {"label": "Claim-only TF-IDF (no evidence)", "test": {"retrieved": score(splits["test"], cprobs, False)}}

    temps: dict[str, float] = {}
    for key, label in MODELS.items():
        entry: dict = {"label": label, "val": {}, "test": {}}
        for split in ("val", "test"):
            for mode in ("retrieved", "oracle"):
                path = a.preds / f"preds_{key}_{split}_{mode}.npy"
                if path.exists():
                    entry[split][mode] = score(splits[split], np.load(path), with_fever=mode == "retrieved")
        vp = a.preds / f"preds_{key}_val_retrieved.npy"
        if vp.exists():
            T = round(fit_temperature(splits["val"], np.load(vp)), 2)
            temps[key] = T
            entry["temperature"] = T
            for split in ("val", "test"):
                for mode in ("retrieved", "oracle"):
                    path = a.preds / f"preds_{key}_{split}_{mode}.npy"
                    if path.exists():
                        entry[split][f"{mode}_calibrated"] = score(splits[split], scale(np.load(path), T), with_fever=mode == "retrieved")
        out["models"][key] = entry

    (ROOT / "docs" / "results" / "verification.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    (ROOT / "data" / "models").mkdir(parents=True, exist_ok=True)
    (ROOT / "data" / "models" / "calibration.json").write_text(json.dumps(temps, indent=2), encoding="utf-8")
    hist = a.preds / "history.json"
    if hist.exists():
        (ROOT / "docs" / "results" / "verification_history.json").write_text(hist.read_text(encoding="utf-8"), encoding="utf-8")

    print(f"{'model':<34}{'acc':>7}{'macroF1':>9}{'CE':>7}{'ECE':>7}{'FEVER':>8}   (test, retrieved evidence)")
    for key, e in out["models"].items():
        for tag in ("retrieved", "retrieved_calibrated"):
            t = e["test"].get(tag)
            if t:
                name = e["label"] + (f" [T={e['temperature']}]" if tag.endswith("calibrated") else "")
                print(f"{name:<34}{t['accuracy']:>7}{t['macro']['f1']:>9}{t['cross_entropy']:>7}{t['ece']:>7}{t.get('fever_score', '-'):>8}")
    print("oracle evidence (upper bound):", {k: e["test"]["oracle"]["accuracy"] for k, e in out["models"].items() if "oracle" in e["test"]})


if __name__ == "__main__":
    main()
