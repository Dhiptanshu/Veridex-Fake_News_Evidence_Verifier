"""Sentence-level retrieval ablation: lexical vs word-vector vs transformer vs hybrid.

    python ml/eval_semantic.py [--limit N] [--stores w2v glove minilm bge_small]

Candidate pages come from TF-IDF + title match (top 10), the same first stage as Phase 3. Fusion weights are tuned on
val, everything is reported on test. Writes docs/results/retrieval_semantic.json.
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.data import corpus  # noqa: E402
from app.eval import retrieval as ev  # noqa: E402
from app.nlp import entities  # noqa: E402
from app.retrieval import hybrid  # noqa: E402
from app.retrieval.hybrid import TFIDF  # noqa: E402
from app.retrieval.search import DEFAULT_BOOST  # noqa: E402

K_PAGES = 10
ALPHAS = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]  # weight on TF-IDF; 1 - alpha goes to the dense/word-vector scorer


def mix(store: str, alpha: float) -> dict[str, float]:
    """Fusion weights: `alpha` on TF-IDF, the rest on `store`. The endpoints are the pure scorers."""
    if alpha >= 1:
        return {TFIDF: 1.0}
    if alpha <= 0:
        return {store: 1.0}
    return {TFIDF: alpha, store: 1 - alpha}


class Split:
    def __init__(self, res, claims, stores):
        t0 = time.time()
        self.claims = claims
        idx = res.index
        boosted = [
            idx.titles_in_text(c.claim) | idx.titles_for_entities(e.text for e in entities.extract(c.claim).entities)
            for c in claims
        ]
        self.boosted = boosted
        self.hits = idx.rank_pages([c.claim for c in claims], boosted, DEFAULT_BOOST, k=20)
        self.pages = [[h.page_idx for h in row] for row in self.hits]
        self.qv = {}
        for name in stores:
            self.qv[name] = hybrid.get_store(res, name).encode([c.claim for c in claims])
        print(f"  prepared {len(claims)} claims ({time.time() - t0:.0f}s)", flush=True)


def evaluate(res, split: Split, weights, extra_dense: str | None = None, dense_k: int = 20, k_pages: int = K_PAGES, title_bonus: float = 0.0):
    ranked = []
    extra_rows = None
    if extra_dense:
        store = hybrid.get_store(res, extra_dense)
        extra_rows = np.concatenate([store.search_all(split.qv[extra_dense][i : i + 512], dense_k)[0] for i in range(0, len(split.claims), 512)])
    for i, c in enumerate(split.claims):
        pages = list(split.pages[i][:k_pages])
        if extra_rows is not None:
            for p in res.layout.page_of_rows(extra_rows[i]):
                if int(p) not in pages:
                    pages.append(int(p))
        rows = res.layout.rows_of_pages(pages)
        qvs = {n: split.qv[n][i] for n in weights if n in split.qv}
        top, _ = hybrid.rank_rows(res, c.claim, rows, weights, qvs, split.boosted[i], title_bonus)
        top = top[:5]
        pg = res.layout.page_of_rows(top)
        ranked.append([(res.index.page_ids[p], int(res.layout.sent_ids[r])) for p, r in zip(pg, top)])
    return ev.summarize_sentences(split.claims, ranked)


def dense_global(res, split: Split, name: str):
    store = hybrid.get_store(res, name)
    rows = np.concatenate([store.search_all(split.qv[name][i : i + 512], 20)[0] for i in range(0, len(split.claims), 512)])
    ranked = []
    for r in rows:
        pg = res.layout.page_of_rows(r)
        ranked.append([(res.index.page_ids[p], int(res.layout.sent_ids[x])) for p, x in zip(pg, r)])
    m = ev.summarize_sentences(split.claims, ranked)
    m["page_recall@20_sentences"] = round(sum(ev.page_hit(c, [p for p, _ in rk], 20) for c, rk in zip(split.claims, ranked)) / len(ranked), 4)
    return m


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--stores", nargs="+", default=["w2v", "glove", "minilm", "bge_small"])
    a = ap.parse_args()

    res = hybrid.get_resources()
    t0 = time.time()
    res.precompute_sentence_tfidf()
    print(f"sentence tf-idf precomputed ({time.time() - t0:.0f}s); stores: {a.stores}", flush=True)
    for s in a.stores:
        hybrid.get_store(res, s)

    splits = {}
    for name in ("val", "test"):
        cs = ev.verifiable(corpus.load_claims(name))
        cs = cs[: a.limit] if a.limit else cs
        print(name, len(cs), flush=True)
        splits[name] = Split(res, cs, a.stores)

    out: dict = {"candidate_pages": K_PAGES, "val_claims": len(splits["val"].claims), "test_claims": len(splits["test"].claims)}
    best_alpha: dict[str, float] = {}
    grid: dict[str, dict] = {}
    for s in a.stores:
        grid[s] = {}
        for al in ALPHAS:
            m = evaluate(res, splits["val"], mix(s, al))
            grid[s][str(al)] = m
        best_alpha[s] = max(ALPHAS, key=lambda al: (grid[s][str(al)]["sentence_recall@5"], grid[s][str(al)]["sentence_recall@1"]))
        print(f"  {s}: best alpha(tfidf)={best_alpha[s]} val R@5={grid[s][str(best_alpha[s])]['sentence_recall@5']}", flush=True)
    out["val_alpha_grid"] = grid
    out["tuned_alpha_tfidf"] = best_alpha

    test = splits["test"]
    results: dict[str, dict] = {"tfidf": evaluate(res, test, {TFIDF: 1.0})}
    for s in a.stores:
        results[f"{s} (rerank only)"] = evaluate(res, test, {s: 1.0})
        al = best_alpha[s]
        results[f"tfidf + {s} (alpha={al})"] = evaluate(res, test, mix(s, al))
    dense_names = [s for s in a.stores if s in ("minilm", "bge_small")]
    if dense_names:
        best_dense = max(dense_names, key=lambda s: results[f"tfidf + {s} (alpha={best_alpha[s]})"]["sentence_recall@5"])
        al = best_alpha[best_dense]
        results[f"tfidf + {best_dense} + dense candidate pages"] = evaluate(
            res, test, mix(best_dense, al), extra_dense=best_dense
        )
        for s in dense_names:
            results[f"{s} global search (no TF-IDF)"] = dense_global(res, test, s)
        out["best_dense"] = best_dense
    out["test"] = results
    for k, v in results.items():
        print(f"  {k}: {v}", flush=True)

    (ROOT / "docs" / "results" / "retrieval_semantic.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("wrote docs/results/retrieval_semantic.json")


if __name__ == "__main__":
    main()
