"""Build the retrieval artefacts in data/indexes from data/processed.

    python ml/build_indexes.py

Outputs tfidf.joblib (page vectors + sentences) and pmi.joblib (collocation statistics).
"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.data import corpus  # noqa: E402
from app.nlp.pmi import PmiTable  # noqa: E402
from app.retrieval.tfidf import TfidfIndex  # noqa: E402


def main() -> None:
    t0 = time.time()
    pages = list(corpus.iter_pages())
    print(f"{len(pages):,} pages loaded ({time.time() - t0:.0f}s)")

    index = TfidfIndex.build(pages)
    index.save()
    print(f"tfidf: matrix {index.matrix.shape}, nnz {index.matrix.nnz:,} ({time.time() - t0:.0f}s)")

    pmi = PmiTable.build(s for p in pages for s in p.sentences if s)
    pmi.save()
    print(f"pmi: {len(pmi.unigrams):,} unigrams, {len(pmi.bigrams):,} bigrams kept ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
