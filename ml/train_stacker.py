"""Train the claim-level stacker on BERT's per-sentence + concatenated predictions (validation split), score on test.

    python ml/train_stacker.py

Inputs : data/kaggle/verify_out/agg_{val,test}full.npy  (per-sentence probabilities, from ml/kaggle/aggregate)
         data/kaggle/verify_out/preds_bert_{val,test}_retrieved.npy  (concatenated-evidence probabilities)
         data/processed/verif_{val,test}.jsonl
Outputs: data/models/stacker.joblib, docs/results/verification_stacker.json
Inputs to the stacker are BERT's raw (uncalibrated) probabilities; the stacker's own outputs are the calibrated ones.
Regularisation C is chosen by 5-fold cross-validation on val; test is touched once, at the end.
"""
import json
import sys
from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_predict

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.eval import classification as cl  # noqa: E402
from app.verification import stack  # noqa: E402
from app.verification.text import LABELS  # noqa: E402

OUT = ROOT / "data" / "kaggle" / "verify_out"


def load(split: str):
    rows = [json.loads(line) for line in (ROOT / "data" / "processed" / f"verif_{split}.jsonl").open(encoding="utf-8")]
    sent = np.load(OUT / f"agg_{split}full.npy")
    concat = np.load(OUT / f"preds_bert_{split}_retrieved.npy")
    top = np.array([r["retrieved"][0]["score"] if r["retrieved"] else 0.0 for r in rows], dtype=np.float32)
    return rows, stack.batch_features(sent, concat, top), np.array([LABELS.index(r["label"]) for r in rows])


def score(rows, y, probs) -> dict:
    names = [LABELS[i] for i in probs.argmax(1)]
    m = cl.report([r["label"] for r in rows], names)
    m["cross_entropy"] = round(cl.cross_entropy(y, probs), 4)
    m["ece"] = round(cl.expected_calibration_error(y, probs), 4)
    m["fever_score"] = round(cl.fever_score([r["label"] for r in rows], names, [r["gold_retrieved"] for r in rows]), 4)
    return m


def main() -> None:
    (vrows, Xv, yv), (trows, Xt, yt) = load("val"), load("test")
    make = lambda C: LogisticRegression(C=C, max_iter=2000, class_weight="balanced")  # noqa: E731
    cv = StratifiedKFold(5, shuffle=True, random_state=13)
    grid = {}
    for C in (0.1, 0.3, 1.0, 3.0, 10.0, 30.0):
        p = cross_val_predict(make(C), Xv, yv, cv=cv, method="predict_proba")
        grid[C] = {"cv_accuracy": round(float((p.argmax(1) == yv).mean()), 4), "cv_cross_entropy": round(cl.cross_entropy(yv, p), 4)}
        print(f"  C={C}: {grid[C]}")
    best = min(grid, key=lambda c: grid[c]["cv_cross_entropy"])
    model = make(best).fit(Xv, yv)
    assert list(model.classes_) == [0, 1, 2]

    out = {
        "features": stack.N_FEATURES, "best_C": best, "val_cv": grid,
        "trained_on": len(yv), "class_weight": "balanced (FEVER's test set is balanced three ways)",
        "test": score(trows, yt, model.predict_proba(Xt)),
        "test_claims": len(yt),
    }
    (ROOT / "data" / "models").mkdir(parents=True, exist_ok=True)
    joblib.dump(model, ROOT / "data" / "models" / "stacker.joblib")
    (ROOT / "docs" / "results" / "verification_stacker.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    t = out["test"]
    print(f"test: acc {t['accuracy']} macro-F1 {t['macro']['f1']} CE {t['cross_entropy']} ECE {t['ece']} FEVER {t['fever_score']}")
    print("confusion (rows true S/R/N):", t["confusion_matrix"]["rows_true_cols_pred"])


if __name__ == "__main__":
    main()
