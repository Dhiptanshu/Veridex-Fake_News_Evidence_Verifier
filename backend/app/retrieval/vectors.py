"""Sentence vector stores: one matrix (rows follow SentenceLayout) plus the function that embeds a query.

Three kinds share one interface so retrievers and the evaluation can treat them uniformly:
  * word-vector stores (Word2Vec trained on the corpus, GloVe pretrained): IDF-weighted average of word vectors
  * dense transformer stores (MiniLM, BGE): sentence-transformer embeddings computed on Kaggle
"""
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import numpy as np

from app.nlp import resources

VECTOR_DIR = resources.INDEX_DIR
_TOKEN = re.compile(r"[a-z0-9]+")


@dataclass
class VectorStore:
    name: str
    matrix: np.ndarray  # (n_rows, dim) float16/32, L2-normalised rows
    encode: Callable[[list[str]], np.ndarray]  # queries -> (n, dim) float32, L2-normalised
    encode_docs: Callable[[list[str]], np.ndarray] | None = None  # passages, when they are embedded differently from queries
    _f32: np.ndarray | None = field(default=None, repr=False)

    def matrix32(self) -> np.ndarray:
        if self._f32 is None:
            self._f32 = np.asarray(self.matrix, dtype=np.float32)
        return self._f32

    def scores(self, query_vec: np.ndarray, rows: np.ndarray) -> np.ndarray:
        return self.matrix[rows].astype(np.float32) @ query_vec

    def search_all(self, query_vecs: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray]:
        """Global top-k rows for each query by brute-force cosine. Returns (rows, scores), each (n_queries, k)."""
        sims = query_vecs @ self.matrix32().T
        k = min(k, sims.shape[1])
        top = np.argpartition(-sims, k - 1, axis=1)[:, :k]
        order = np.argsort(-np.take_along_axis(sims, top, axis=1), axis=1)
        top = np.take_along_axis(top, order, axis=1)
        return top, np.take_along_axis(sims, top, axis=1)


# ---------------------------------------------------------------------------------------------------------------
# word-vector averaging (Word2Vec / GloVe)


def tokens(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


def sentence_vector(toks: Iterable[str], kv, idf: dict[str, float], default_idf: float) -> np.ndarray:
    vecs, weights = [], []
    for t in toks:
        if t in kv.key_to_index:
            vecs.append(kv[t])
            weights.append(idf.get(t, default_idf))
    if not vecs:
        return np.zeros(kv.vector_size, dtype=np.float32)
    v = (np.asarray(vecs, dtype=np.float32) * np.asarray(weights, dtype=np.float32)[:, None]).sum(axis=0)
    n = np.linalg.norm(v)
    return v / n if n > 0 else v


def idf_table(vectorizer) -> tuple[dict[str, float], float]:
    """Unigram IDF from the retrieval TF-IDF model, so weighting is consistent across retrievers."""
    idf = {w: float(vectorizer.idf_[i]) for w, i in vectorizer.vocabulary_.items() if " " not in w}
    return idf, float(vectorizer.idf_.max())


def word_vector_store(name: str, kv, matrix: np.ndarray, idf: dict[str, float], default_idf: float) -> VectorStore:
    def encode(texts: list[str]) -> np.ndarray:
        return np.stack([sentence_vector(tokens(t), kv, idf, default_idf) for t in texts]) if texts else np.empty((0, kv.vector_size), np.float32)

    return VectorStore(name, matrix, encode)


# ---------------------------------------------------------------------------------------------------------------
# dense transformer embeddings

DENSE_MODELS = {
    "minilm": {"model": "sentence-transformers/all-MiniLM-L6-v2", "query_prefix": ""},
    "bge_small": {
        "model": "BAAI/bge-small-en-v1.5",
        "query_prefix": "Represent this sentence for searching relevant passages: ",
    },
}


@lru_cache(maxsize=4)
def _sentence_transformer(model_name: str):
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name, device="cpu")


def dense_store(key: str, matrix: np.ndarray) -> VectorStore:
    spec = DENSE_MODELS[key]

    def encode(texts: list[str]) -> np.ndarray:
        model = _sentence_transformer(spec["model"])
        return model.encode(
            [spec["query_prefix"] + t for t in texts], batch_size=128, normalize_embeddings=True,
            show_progress_bar=False, convert_to_numpy=True,
        ).astype(np.float32)

    def encode_docs(texts: list[str]) -> np.ndarray:
        model = _sentence_transformer(spec["model"])  # passages get no query instruction
        return model.encode(texts, batch_size=128, normalize_embeddings=True, show_progress_bar=False, convert_to_numpy=True).astype(np.float32)

    return VectorStore(key, matrix, encode, encode_docs)


def load_matrix(filename: str, directory: Path = VECTOR_DIR) -> np.ndarray:
    path = directory / filename
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. See README (Phase 4) for how to build it.")
    return np.load(path, mmap_mode="r")
