"""Two-stage TF-IDF retrieval over the evidence corpus.

1. Page ranking: cosine similarity between the claim and each page's TF-IDF vector (title + text, unigrams and
   bigrams), plus an optional bonus for pages whose *title* is mentioned in the claim (entity-aware search).
2. Sentence ranking: within the top pages, rank individual sentences (prefixed with the page title so that
   pronoun-led sentences like "He was born in 1970." still match).
"""
import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer

from app.data.models import CorpusPage
from app.nlp import resources

INDEX_PATH = resources.INDEX_DIR / "tfidf.joblib"
_DISAMBIG = re.compile(r"\s*\([^)]*\)\s*$")
_TOKEN = re.compile(r"[A-Za-z0-9][\w'\-]*")


def title_key(title: str) -> str:
    """'Soul Food (film)' -> 'soul food'."""
    return _DISAMBIG.sub("", title).strip().lower()


def _page_document(page: CorpusPage) -> str:
    return f"{page.title}. {page.title}. " + " ".join(s for s in page.sentences if s)


@dataclass
class PageHit:
    page_idx: int
    score: float


@dataclass
class SentenceHit:
    page_idx: int
    sent_id: int
    score: float


@dataclass
class TfidfIndex:
    vectorizer: TfidfVectorizer
    matrix: sparse.csr_matrix  # pages x features, rows L2-normalised
    page_ids: list[str]
    titles: list[str]
    page_sentences: list[list[str]]
    title_lookup: dict[str, list[int]] = field(default_factory=dict)  # title_key -> page indices

    # ---- build / persist -------------------------------------------------------------------------------------
    @classmethod
    def build(cls, pages: Iterable[CorpusPage], max_features: int = 600_000, min_df: int = 2) -> "TfidfIndex":
        pages = list(pages)
        vec = TfidfVectorizer(
            lowercase=True, stop_words="english", ngram_range=(1, 2), min_df=min_df, max_features=max_features,
            sublinear_tf=True, dtype=np.float32,
        )
        matrix = vec.fit_transform(_page_document(p) for p in pages).tocsr()
        lookup: dict[str, list[int]] = defaultdict(list)
        for i, p in enumerate(pages):
            lookup[title_key(p.title)].append(i)
        return cls(
            vectorizer=vec, matrix=matrix, page_ids=[p.id for p in pages], titles=[p.title for p in pages],
            page_sentences=[p.sentences for p in pages], title_lookup=dict(lookup),
        )

    def save(self, path: Path = INDEX_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path, compress=3)

    @staticmethod
    def load(path: Path = INDEX_PATH) -> "TfidfIndex":
        if not path.exists():
            raise FileNotFoundError(f"TF-IDF index not found at {path}. Run `python ml/build_indexes.py`.")
        return joblib.load(path)

    def feature_names(self) -> np.ndarray:
        if getattr(self, "_names", None) is None:
            self._names = self.vectorizer.get_feature_names_out()
        return self._names

    # ---- title matching --------------------------------------------------------------------------------------
    def titles_in_text(self, claim: str, max_n: int = 6) -> set[int]:
        """Pages whose title appears as a word n-gram in the claim. Lone words must be capitalised non-stopwords."""
        stop = resources.stopwords()
        toks = _TOKEN.findall(claim)
        found: set[int] = set()
        for n in range(1, max_n + 1):
            for i in range(len(toks) - n + 1):
                gram = toks[i : i + n]
                if n == 1 and (not gram[0][0].isupper() or gram[0].lower() in stop):
                    continue
                if all(g.lower() in stop for g in gram):
                    continue
                found.update(self.title_lookup.get(" ".join(gram).lower(), ()))
        return found

    def titles_for_entities(self, entities: Iterable[str]) -> set[int]:
        found: set[int] = set()
        for e in entities:
            found.update(self.title_lookup.get(title_key(e), ()))
        return found

    # ---- ranking ---------------------------------------------------------------------------------------------
    def encode(self, texts: list[str]) -> sparse.csr_matrix:
        return self.vectorizer.transform(texts)

    def rank_pages(
        self, queries: list[str], boosted: list[set[int]] | None = None, boost: float = 0.0, k: int = 20, chunk: int = 256,
    ) -> list[list[PageHit]]:
        """Top-k pages per query. `boosted[i]` are page indices that get `+boost` for query i."""
        out: list[list[PageHit]] = []
        q = self.encode(queries)
        for start in range(0, q.shape[0], chunk):
            scores = (q[start : start + chunk] @ self.matrix.T).toarray()
            for r in range(scores.shape[0]):
                row = scores[r]
                if boosted and boost and boosted[start + r]:
                    idx = np.fromiter(boosted[start + r], dtype=np.int64)
                    row[idx] += boost
                top = np.argpartition(-row, min(k, row.size - 1))[:k]
                top = top[np.argsort(-row[top])]
                out.append([PageHit(int(i), float(row[i])) for i in top])
        return out

    def rank_sentences(self, claim: str, page_hits: list[PageHit], k: int = 5) -> list[SentenceHit]:
        """Best `k` sentences across the given pages, scored by cosine to the claim (title-prefixed)."""
        texts: list[str] = []
        keys: list[tuple[int, int]] = []
        for hit in page_hits:
            title = self.titles[hit.page_idx]
            for sid, sent in enumerate(self.page_sentences[hit.page_idx]):
                if sent:
                    texts.append(f"{title}. {sent}")
                    keys.append((hit.page_idx, sid))
        if not texts:
            return []
        sims = (self.encode(texts) @ self.encode([claim]).T).toarray().ravel()
        order = np.argsort(-sims)[:k]
        return [SentenceHit(keys[i][0], keys[i][1], float(sims[i])) for i in order]


@lru_cache(maxsize=1)
def get_index() -> TfidfIndex:
    return TfidfIndex.load()
