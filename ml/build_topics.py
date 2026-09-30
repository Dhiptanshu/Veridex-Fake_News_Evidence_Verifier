"""Fit an LDA topic model on the evidence pages -> data/indexes/topics.joblib and docs/results/topics.json.

    python ml/build_topics.py [--topics 20]
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.feature_extraction.text import CountVectorizer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.data import corpus  # noqa: E402
from app.nlp.topics import TopicModel  # noqa: E402
from app.schemas.stages import Topic  # noqa: E402

# Words so common in encyclopedic text that they swamp every topic ("born", "american", "known" ...) are kept out
# of the vocabulary by max_df; these extra ones are structural rather than thematic.
EXTRA_STOP = {"said", "new", "year", "years", "one", "two", "first", "also", "later", "became", "known", "including"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--topics", type=int, default=20)
    a = ap.parse_args()
    t0 = time.time()

    pages = list(corpus.iter_pages())
    docs = [" ".join(s for s in p.sentences if s) for p in pages]
    from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

    vec = CountVectorizer(
        stop_words=list(ENGLISH_STOP_WORDS | EXTRA_STOP), max_df=0.3, min_df=10, max_features=20_000,
        token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z]{2,}\b",
    )
    X = vec.fit_transform(docs)
    print(f"{X.shape[0]:,} docs x {X.shape[1]:,} terms ({time.time() - t0:.0f}s)", flush=True)

    lda = LatentDirichletAllocation(
        n_components=a.topics, learning_method="online", batch_size=2048, max_iter=12, random_state=13, n_jobs=4,
    )
    theta = lda.fit_transform(X)
    perplexity = float(lda.perplexity(X))
    print(f"lda fit ({time.time() - t0:.0f}s), perplexity {perplexity:.0f}", flush=True)

    names = vec.get_feature_names_out()
    topics = []
    for k, comp in enumerate(lda.components_):
        words = [names[i] for i in np.argsort(-comp)[:10]]
        topics.append(Topic(id=k, label=" · ".join(words[:3]), words=words))
    model = TopicModel(topics, theta.argmax(axis=1).astype(np.int16), theta.max(axis=1).astype(np.float32), perplexity)
    model.save()

    sizes = np.bincount(model.page_topic, minlength=a.topics)
    summary = {
        "n_topics": a.topics, "perplexity": round(perplexity, 1), "pages": len(pages),
        "topics": [{"id": t.id, "label": t.label, "words": t.words, "pages": int(sizes[t.id])} for t in topics],
    }
    (ROOT / "docs" / "results" / "topics.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    for t in summary["topics"]:
        print(f"  {t['id']:>2} ({t['pages']:>5} pages): {', '.join(t['words'][:8])}")


if __name__ == "__main__":
    main()
