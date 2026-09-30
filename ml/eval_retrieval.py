"""Evaluate TF-IDF retrieval variants (an ablation). Tunes the title boost on val, reports on test.

    python ml/eval_retrieval.py [--limit N]

Writes docs/results/retrieval_tfidf.json.
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.data import corpus  # noqa: E402
from app.eval import retrieval as ev  # noqa: E402
from app.nlp import entities, text, wordnet  # noqa: E402
from app.retrieval.tfidf import TfidfIndex  # noqa: E402

BOOSTS = [0.0, 0.1, 0.2, 0.3, 0.5, 1.0]


def features(index: TfidfIndex, claims):
    """Per-claim inputs shared by all variants: n-gram title matches, NER title matches, WordNet-expanded query."""
    t0 = time.time()
    ngram = [index.titles_in_text(c.claim) for c in claims]
    ner = [index.titles_for_entities(e.text for e in entities.extract(c.claim).entities) for c in claims]
    expanded = []
    for c in claims:
        a = text.analyze(c.claim)
        extra = wordnet.expand(a.lemmas, [p.tag for p in a.pos])
        expanded.append(c.claim + " " + " ".join(extra))
    print(f"  features for {len(claims)} claims in {time.time() - t0:.0f}s")
    return ngram, ner, expanded


def rank(index, claims, queries, boosted, boost, k=20):
    hits = index.rank_pages(queries, boosted, boost, k=k)
    return [[index.page_ids[h.page_idx] for h in row] for row in hits], hits


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="use only the first N verifiable claims per split")
    a = ap.parse_args()

    index = TfidfIndex.load()
    splits = {}
    for name in ("val", "test"):
        cs = ev.verifiable(corpus.load_claims(name))
        splits[name] = cs[: a.limit] if a.limit else cs
    print({k: len(v) for k, v in splits.items()}, "verifiable claims")

    print("val features")
    v_claims = splits["val"]
    v_ngram, v_ner, v_exp = features(index, v_claims)
    v_both = [x | y for x, y in zip(v_ngram, v_ner)]
    v_queries = [c.claim for c in v_claims]

    tuned: dict[str, float] = {}
    grid: dict[str, dict[str, float]] = {}
    for name, boosted in [("ngram_title", v_ngram), ("ner_title", v_ner), ("ngram+ner_title", v_both)]:
        grid[name] = {}
        for b in BOOSTS:
            pages, _ = rank(index, v_claims, v_queries, boosted, b)
            grid[name][str(b)] = ev.summarize_pages(v_claims, pages)["page_recall@5"]
        tuned[name] = max(BOOSTS, key=lambda b: grid[name][str(b)])
        print(f"  {name}: val page_recall@5 by boost {grid[name]} -> {tuned[name]}")

    print("test features")
    t_claims = splits["test"]
    t_ngram, t_ner, t_exp = features(index, t_claims)
    t_both = [x | y for x, y in zip(t_ngram, t_ner)]
    plain = [c.claim for c in t_claims]
    best = "ngram+ner_title"
    variants = {
        "claim_only": (plain, None, 0.0),
        "ngram_title": (plain, t_ngram, tuned["ngram_title"]),
        "ner_title": (plain, t_ner, tuned["ner_title"]),
        "ngram+ner_title": (plain, t_both, tuned["ngram+ner_title"]),
        "ngram+ner_title+wordnet": (t_exp, t_both, tuned["ngram+ner_title"]),
    }
    results = {}
    for name, (queries, boosted, boost) in variants.items():
        pages, hits = rank(index, t_claims, queries, boosted, boost)
        m = ev.summarize_pages(t_claims, pages)
        sent_rank = []
        for c, h in zip(t_claims, hits):
            sh = index.rank_sentences(c.claim, h[:10], k=5)
            sent_rank.append([(index.page_ids[s.page_idx], s.sent_id) for s in sh])
        m.update(ev.summarize_sentences(t_claims, sent_rank))
        m["title_boost"] = boost
        results[name] = m
        print(f"  {name}: {m}")

    out = {
        "method": "tfidf (title x2 + text, 1-2 grams, sublinear tf), cosine; sentence rerank within top-10 pages",
        "test_claims": len(t_claims),
        "val_claims": len(v_claims),
        "corpus_note": "subset corpus (~70k pages): optimistic versus full Wikipedia",
        "val_boost_grid_page_recall@5": grid,
        "test": results,
    }
    (ROOT / "docs" / "results" / "retrieval_tfidf.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("wrote docs/results/retrieval_tfidf.json")


if __name__ == "__main__":
    main()
