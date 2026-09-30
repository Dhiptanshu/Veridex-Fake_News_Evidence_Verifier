"""Claim-only baselines: predict the verdict from the claim text alone (no evidence).

    python ml/train_claim_baseline.py

Bag-of-words and TF-IDF (1-2 grams) with logistic regression; C is tuned on val, results reported on test.
Writes docs/results/claim_only_baseline.json and data/models/claim_only.joblib. This is the bar an evidence-based verifier must clear.
"""
import json
import sys
from pathlib import Path

import joblib

from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.data import corpus  # noqa: E402
from app.eval.classification import report  # noqa: E402

CS = [0.1, 0.3, 1.0, 3.0, 10.0]


def main() -> None:
    data = {s: corpus.load_claims(s) for s in ("train", "val", "test")}
    X = {s: [c.claim for c in cs] for s, cs in data.items()}
    y = {s: [c.label for c in cs] for s, cs in data.items()}

    makers = {
        "bag_of_words": lambda C: make_pipeline(
            CountVectorizer(ngram_range=(1, 1), min_df=2),
            LogisticRegression(C=C, max_iter=2000, class_weight="balanced"),
        ),
        "tfidf_1-2gram": lambda C: make_pipeline(
            TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True),
            LogisticRegression(C=C, max_iter=2000, class_weight="balanced"),
        ),
    }

    out: dict = {
        "task": "claim text only -> supported/refuted/not_enough_info",
        "train_claims": len(X["train"]), "test_claims": len(X["test"]),
        "note": "Test is FEVER's balanced dev set (chance = 0.333); train/val are label-imbalanced.",
        "models": {},
    }
    for name, make in makers.items():
        val_f1 = {}
        for C in CS:
            model = make(C).fit(X["train"], y["train"])
            val_f1[C] = report(y["val"], model.predict(X["val"]))["macro"]["f1"]
        best = max(CS, key=val_f1.get)
        model = make(best).fit(X["train"], y["train"])
        out["models"][name] = {
            "best_C": best, "val_macro_f1_by_C": val_f1,
            "val": report(y["val"], model.predict(X["val"])),
            "test": report(y["test"], model.predict(X["test"])),
        }
        if name == "tfidf_1-2gram":  # the stronger baseline is also served as the "claim-only" verifier
            (ROOT / "data" / "models").mkdir(parents=True, exist_ok=True)
            joblib.dump(model, ROOT / "data" / "models" / "claim_only.joblib")
        t = out["models"][name]["test"]
        print(f"{name}: C={best} test acc {t['accuracy']} macro-F1 {t['macro']['f1']}")

    (ROOT / "docs" / "results" / "claim_only_baseline.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("wrote docs/results/claim_only_baseline.json")


if __name__ == "__main__":
    main()
