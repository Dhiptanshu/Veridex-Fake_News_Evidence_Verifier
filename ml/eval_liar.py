"""LIAR (Wang, 2017): 12.8k PolitiFact statements, 6 truthfulness labels.

    python ml/eval_liar.py [--n-transfer 500]

Data: data/raw/liar/{train,valid,test}.tsv from https://sites.cs.ucsb.edu/~william/data/liar_dataset.zip
1. Claim-only text classification (Module III): BoW and TF-IDF + logistic regression, in 6-class and binary form, with a
   metadata ablation (speaker/party/subject).
2. Cross-domain transfer: our FEVER-trained evidence pipeline (retrieve from the offline Wikipedia subset, BERT + stacker)
   on LIAR statements with a clear truth value (mostly-true/true -> supported, false/pants-fire -> refuted), versus a
   claim-only model trained on LIAR for the same task. Expect poor transfer: LIAR statements need political records and
   statistics, not an encyclopedia.
Writes docs/results/liar.json.
"""
import argparse
import csv
import json
import random
import sys
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.pipeline import make_pipeline

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

LABELS6 = ["pants-fire", "false", "barely-true", "half-true", "mostly-true", "true"]
BINARY = {"pants-fire": "false-ish", "false": "false-ish", "barely-true": "false-ish", "half-true": "true-ish", "mostly-true": "true-ish", "true": "true-ish"}
STRICT = {"mostly-true": "supported", "true": "supported", "false": "refuted", "pants-fire": "refuted"}
COLS = ["id", "label", "statement", "subject", "speaker", "job", "state", "party", "c1", "c2", "c3", "c4", "c5", "context"]
CS = [0.1, 0.3, 1.0, 3.0, 10.0]


def load(split: str) -> list[dict]:
    with (ROOT / "data" / "raw" / "liar" / f"{split}.tsv").open(encoding="utf-8") as fh:
        # a few rows lack trailing columns (speaker metadata etc.), so pad every row to full width
        return [dict(zip(COLS, row + [""] * (len(COLS) - len(row)))) for row in csv.reader(fh, delimiter="\t") if len(row) >= 3]


def with_meta(r: dict) -> str:
    """Statement plus categorical metadata as extra tokens (speaker names are a known shortcut in LIAR)."""
    return f"{r['statement']} spk_{r['speaker']} party_{r['party']} " + " ".join(f"sub_{s}" for s in r["subject"].split(","))


def classify(train, valid, test, y_fn, text_fn) -> dict:
    X = {n: [text_fn(r) for r in rs] for n, rs in (("train", train), ("valid", valid), ("test", test))}
    y = {n: [y_fn(r) for r in rs] for n, rs in (("train", train), ("valid", valid), ("test", test))}
    makers = {
        "bag_of_words": lambda C: make_pipeline(CountVectorizer(min_df=2), LogisticRegression(C=C, max_iter=2000)),
        "tfidf_1-2gram": lambda C: make_pipeline(TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True), LogisticRegression(C=C, max_iter=2000)),
    }
    out = {}
    for name, make in makers.items():
        best = max(CS, key=lambda C: accuracy_score(y["valid"], make(C).fit(X["train"], y["train"]).predict(X["valid"])))
        pred = make(best).fit(X["train"], y["train"]).predict(X["test"])
        out[name] = {"C": best, "accuracy": round(float(accuracy_score(y["test"], pred)), 4), "macro_f1": round(float(f1_score(y["test"], pred, average="macro")), 4)}
    majority = max(set(y["test"]), key=y["test"].count)
    out["majority_class_accuracy"] = round(float(np.mean([v == majority for v in y["test"]])), 4)
    return out


def transfer(train, valid, test, n: int, seed: int = 13) -> dict:
    from app.retrieval import batch, hybrid
    from app.schemas.stages import Evidence, EvidenceSentence, RetrievalOut
    from app.stages.verification import verify_stacked

    pool = [r for r in valid + test if r["label"] in STRICT]
    sample = random.Random(seed).sample(pool, min(n, len(pool)))
    gold = [STRICT[r["label"]] for r in sample]

    res = hybrid.get_resources()
    hits = batch.retrieve_many(res, [r["statement"] for r in sample])
    pred = []
    for r, hs in zip(sample, hits):
        by: dict[str, Evidence] = {}
        for h in hs:
            pid = res.index.page_ids[h.page_idx]
            ev = by.setdefault(pid, Evidence(id=pid, title=res.index.titles[h.page_idx], source="wikipedia", score=min(1.0, h.score), sentences=[]))
            ev.sentences.append(EvidenceSentence(text=res.index.page_sentences[h.page_idx][h.sent_id], score=min(1.0, max(0.0, h.score))))
        pred.append(verify_stacked(r["statement"], RetrievalOut(evidence=list(by.values()))).label)
        if len(pred) % 100 == 0:
            print(f"  transfer {len(pred)}/{len(sample)}", flush=True)

    decisive = [(g, p) for g, p in zip(gold, pred) if p != "not_enough_info"]
    chance = max(gold.count("supported"), gold.count("refuted")) / len(gold)

    strict_train = [r for r in train if r["label"] in STRICT]
    base = make_pipeline(TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True), LogisticRegression(C=1.0, max_iter=2000))
    base.fit([r["statement"] for r in strict_train], [STRICT[r["label"]] for r in strict_train])
    base_pred = base.predict([r["statement"] for r in sample])
    return {
        "claims": len(sample), "gold_balance": {k: gold.count(k) for k in ("supported", "refuted")},
        "majority_class_accuracy": round(chance, 4),
        "fever_pipeline": {
            "predicted": {k: pred.count(k) for k in ("supported", "refuted", "not_enough_info")},
            "coverage_not_nei": round(len(decisive) / len(sample), 4),
            "accuracy_when_decisive": round(float(np.mean([g == p for g, p in decisive])), 4) if decisive else None,
            "decisive_claims": len(decisive),
            "accuracy_counting_nei_as_wrong": round(float(np.mean([g == p for g, p in zip(gold, pred)])), 4),
        },
        "claim_only_trained_on_liar": {"accuracy": round(float(np.mean([g == p for g, p in zip(gold, base_pred)])), 4)},
        "note": "evidence = the offline 70k-page Wikipedia subset; LIAR statements mostly need records/statistics Wikipedia lacks",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-transfer", type=int, default=500)
    ap.add_argument("--no-transfer", action="store_true")
    a = ap.parse_args()

    train, valid, test = load("train"), load("valid"), load("test")
    out: dict = {"sizes": {"train": len(train), "valid": len(valid), "test": len(test)}, "chance_6class": round(1 / 6, 4)}
    out["six_class_text_only"] = classify(train, valid, test, lambda r: r["label"], lambda r: r["statement"])
    out["binary_text_only"] = classify(train, valid, test, lambda r: BINARY[r["label"]], lambda r: r["statement"])
    out["binary_with_metadata"] = classify(train, valid, test, lambda r: BINARY[r["label"]], with_meta)
    print(json.dumps(out, indent=2), flush=True)
    if not a.no_transfer:
        out["transfer_from_fever"] = transfer(train, valid, test, a.n_transfer)
        print(json.dumps(out["transfer_from_fever"], indent=2), flush=True)
    (ROOT / "docs" / "results" / "liar.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("wrote docs/results/liar.json")


if __name__ == "__main__":
    main()
