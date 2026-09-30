"""Build word-vector sentence matrices: Word2Vec (trained on our corpus) and GloVe (pretrained, downloaded).

    python ml/build_wordvecs.py

Writes to data/indexes: w2v.kv, glove.kv, sent_w2v.npy, sent_glove.npy. Sentence vector = IDF-weighted average of word vectors,
one row per corpus sentence in SentenceLayout order.
"""
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import gensim.downloader as api  # noqa: E402
from gensim.models import KeyedVectors, Word2Vec  # noqa: E402

from app.data import corpus  # noqa: E402
from app.nlp import resources  # noqa: E402
from app.retrieval import vectors  # noqa: E402
from app.retrieval.tfidf import TfidfIndex  # noqa: E402

OUT = resources.INDEX_DIR
GLOVE = "glove-wiki-gigaword-100"


def main() -> None:
    t0 = time.time()
    api.BASE_DIR = str(ROOT / "data" / "gensim-data")  # keep downloads inside the project (gitignored)
    index = TfidfIndex.load()
    idf, default_idf = vectors.idf_table(index.vectorizer)

    texts = [t for _, _, t in corpus.iter_sentences()]
    tokenised = [vectors.tokens(t) for t in texts]
    print(f"{len(texts):,} sentences tokenised ({time.time() - t0:.0f}s)")

    if (OUT / "w2v.kv").exists():
        w2v_kv = KeyedVectors.load(str(OUT / "w2v.kv"))
    else:
        w2v = Word2Vec(tokenised, vector_size=100, window=5, min_count=3, sg=1, negative=10, epochs=8, workers=4, seed=13)
        w2v_kv = w2v.wv
        w2v_kv.save(str(OUT / "w2v.kv"))
    print(f"word2vec: {len(w2v_kv):,} words ({time.time() - t0:.0f}s); most similar to 'physicist': "
          f"{[w for w, _ in w2v_kv.most_similar('physicist', topn=5)]}")

    if (OUT / "glove.kv").exists():
        glove = KeyedVectors.load(str(OUT / "glove.kv"))
    else:
        glove = KeyedVectors.load_word2vec_format(api.load(GLOVE, return_path=True))
        glove.save(str(OUT / "glove.kv"))
    print(f"glove: {len(glove):,} words ({time.time() - t0:.0f}s)")

    for name, kv in (("w2v", w2v_kv), ("glove", glove)):
        mat = np.stack([vectors.sentence_vector(toks, kv, idf, default_idf) for toks in tokenised]).astype(np.float16)
        np.save(OUT / f"sent_{name}.npy", mat)
        print(f"sent_{name}.npy {mat.shape} ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
