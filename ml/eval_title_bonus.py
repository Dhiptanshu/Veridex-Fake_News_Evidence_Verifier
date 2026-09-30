"""Does entity/title awareness still help a strong dense retriever?

    python ml/eval_title_bonus.py [--store bge_small] [--limit N]

Adds `bonus` to the dense score of every sentence on a page whose title the claim mentions (n-gram or NER match).
The bonus is tuned on val and reported on test. Writes docs/results/retrieval_title_bonus.json.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "ml"))

from app.data import corpus  # noqa: E402
from app.eval import retrieval as ev  # noqa: E402
from app.retrieval import hybrid  # noqa: E402

import eval_semantic as es  # noqa: E402

BONUSES = [0.0, 0.02, 0.05, 0.1, 0.2]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", default="bge_small")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    res = hybrid.get_resources()
    hybrid.get_store(res, a.store)
    splits = {}
    for name in ("val", "test"):
        cs = ev.verifiable(corpus.load_claims(name))
        splits[name] = es.Split(res, cs[: a.limit] if a.limit else cs, [a.store])

    w = {a.store: 1.0}
    val = {b: es.evaluate(res, splits["val"], w, extra_dense=a.store, title_bonus=b) for b in BONUSES}
    for b, m in val.items():
        print(f"  val bonus={b}: {m}", flush=True)
    best = max(BONUSES, key=lambda b: (val[b]["sentence_recall@5"], val[b]["sentence_recall@1"]))
    test = {b: es.evaluate(res, splits["test"], w, extra_dense=a.store, title_bonus=b) for b in sorted({0.0, best})}
    for b, m in test.items():
        print(f"  test bonus={b}: {m}", flush=True)

    out = {"store": a.store, "val_by_bonus": {str(b): m for b, m in val.items()}, "tuned_bonus": best,
           "test": {str(b): m for b, m in test.items()}, "val_claims": len(splits["val"].claims), "test_claims": len(splits["test"].claims)}
    (ROOT / "docs" / "results" / "retrieval_title_bonus.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("wrote docs/results/retrieval_title_bonus.json")


if __name__ == "__main__":
    main()
