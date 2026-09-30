"""Hybrid retrieval: lexical (TF-IDF) and semantic (word-vector / transformer) scores fused per claim.

1. Candidate pages: TF-IDF + title match; optionally also the pages of the globally closest dense sentences, so the
   semantic model can rescue pages the lexical model missed.
2. Every sentence of the candidate pages is scored by each selected scorer, each score set is min-max normalised
   across the candidates, and the final score is a weighted sum.
"""
from dataclasses import dataclass, field
from functools import lru_cache

import numpy as np
from scipy import sparse

from app.retrieval import vectors
from app.retrieval.layout import SentenceLayout
from app.retrieval.search import DEFAULT_BOOST, entropy_bits, wikipedia_url
from app.retrieval.tfidf import TfidfIndex, get_index
from app.schemas.stages import Evidence, EvidenceSentence, RetrievalOut

TFIDF = "tfidf"
STORE_FILES = {"w2v": "sent_w2v.npy", "glove": "sent_glove.npy", "minilm": "emb_minilm.npy", "bge_small": "emb_bge_small.npy"}


def _softmax(x: np.ndarray, temperature: float) -> np.ndarray:
    z = np.asarray(x, dtype=np.float64) / temperature
    z = np.exp(z - z.max())
    return z / z.sum()


def minmax(x: np.ndarray) -> np.ndarray:
    lo, hi = float(x.min()), float(x.max())
    return np.zeros_like(x) if hi - lo < 1e-9 else (x - lo) / (hi - lo)


@dataclass
class Resources:
    index: TfidfIndex
    layout: SentenceLayout
    stores: dict[str, vectors.VectorStore] = field(default_factory=dict)
    sent_tfidf: sparse.csr_matrix | None = None  # optional precomputed sentence TF-IDF (used by bulk evaluation)

    def row_text(self, rows: np.ndarray) -> list[str]:
        pages = self.layout.page_of_rows(rows)
        return [self.index.page_sentences[p][s] for p, s in zip(pages, self.layout.sent_ids[rows])]

    def titled_text(self, rows: np.ndarray) -> list[str]:
        pages = self.layout.page_of_rows(rows)
        return [f"{self.index.titles[p]}. {self.index.page_sentences[p][s]}" for p, s in zip(pages, self.layout.sent_ids[rows])]

    def precompute_sentence_tfidf(self) -> None:
        rows = np.arange(self.layout.n_rows)
        self.sent_tfidf = self.index.encode(self.titled_text(rows)).tocsr()

    def tfidf_scores(self, claim_vec: sparse.csr_matrix, rows: np.ndarray) -> np.ndarray:
        mat = self.sent_tfidf[rows] if self.sent_tfidf is not None else self.index.encode(self.titled_text(rows))
        return (mat @ claim_vec.T).toarray().ravel()


def load_stores(names: list[str]) -> dict[str, vectors.VectorStore]:
    """Load the named vector stores from data/indexes (raises FileNotFoundError with build instructions)."""
    out: dict[str, vectors.VectorStore] = {}
    idf = None
    for name in names:
        mat = vectors.load_matrix(STORE_FILES[name])
        if name in vectors.DENSE_MODELS:
            out[name] = vectors.dense_store(name, mat)
        else:
            from gensim.models import KeyedVectors

            if idf is None:
                idf = vectors.idf_table(get_index().vectorizer)
            kv = KeyedVectors.load(str(vectors.VECTOR_DIR / f"{'w2v' if name == 'w2v' else 'glove'}.kv"))
            out[name] = vectors.word_vector_store(name, kv, mat, *idf)
    return out


@lru_cache(maxsize=1)
def get_resources() -> Resources:
    index = get_index()
    return Resources(index, SentenceLayout.from_pages(index.page_sentences))


def get_store(res: Resources, name: str) -> vectors.VectorStore:
    if name not in res.stores:
        res.stores.update(load_stores([name]))
    return res.stores[name]


def rank_rows(
    res: Resources, claim: str, rows: np.ndarray, weights: dict[str, float], query_vecs: dict[str, np.ndarray] | None = None,
    bonus_pages: set[int] | None = None, bonus: float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Score candidate `rows` with a weighted sum of min-max normalised scorers. Returns (rows, scores), best first.

    Sentences from `bonus_pages` (pages whose title the claim mentions) get `+bonus` on top of the fused score.
    """
    parts: list[tuple[float, np.ndarray]] = []
    for name, w in weights.items():
        if w == 0:
            continue
        if name == TFIDF:
            s = res.tfidf_scores(res.index.encode([claim]), rows)
        else:
            q = query_vecs[name] if query_vecs and name in query_vecs else get_store(res, name).encode([claim])[0]
            s = get_store(res, name).scores(q, rows)
        parts.append((w, s if len(weights) == 1 else minmax(s)))
    total = sum(w * s for w, s in parts)
    if bonus and bonus_pages:
        total = total + bonus * np.isin(res.layout.page_of_rows(rows), list(bonus_pages))
    order = np.argsort(-total)
    return rows[order], total[order]


def candidate_pages(
    res: Resources, claim: str, entity_texts: list[str], *, k_pages: int, use_titles: bool = True,
    boost: float = DEFAULT_BOOST, dense: str | None = None, dense_k: int = 20, query_vec: np.ndarray | None = None,
):
    """TF-IDF(+title) page hits, plus pages of the globally closest dense sentences when `dense` is given."""
    boosted = [res.index.titles_in_text(claim) | res.index.titles_for_entities(entity_texts)] if use_titles else None
    hits = res.index.rank_pages([claim], boosted, boost if use_titles else 0.0, k=k_pages)[0]
    pages = [h.page_idx for h in hits]
    if dense:
        store = get_store(res, dense)
        q = query_vec if query_vec is not None else store.encode([claim])[0]
        top_rows, _ = store.search_all(q[None, :], dense_k)
        for p in res.layout.page_of_rows(top_rows[0]):
            if int(p) not in pages:
                pages.append(int(p))
    return hits, pages


def title_pages(res: Resources, claim: str, entity_texts: list[str]) -> set[int]:
    """Pages whose title the claim mentions (n-gram match or NER entity)."""
    return res.index.titles_in_text(claim) | res.index.titles_for_entities(entity_texts)


def hybrid_search(
    res: Resources, claim: str, entity_texts: list[str], *, weights: dict[str, float], dense_for_candidates: str | None = None,
    k_pages: int = 10, k_sentences: int = 5, use_titles: bool = True, boost: float = DEFAULT_BOOST,
    title_bonus: float = 0.0, project_with: str | None = None,
) -> RetrievalOut:
    """Full hybrid retrieval. `project_with` names a dense store whose embeddings feed the 2-D semantic map.

    `title_bonus` is added to the score of sentences on pages whose title the claim mentions (tuned on val).
    """
    from app.nlp import topics as topics_mod
    from app.retrieval import projection as projection_mod

    needed = {n for n in weights if n != TFIDF} | ({dense_for_candidates} if dense_for_candidates else set()) | ({project_with} if project_with else set())
    qvecs = {n: get_store(res, n).encode([claim])[0] for n in needed}

    hits, pages = candidate_pages(
        res, claim, entity_texts, k_pages=k_pages, use_titles=use_titles, boost=boost, dense=dense_for_candidates,
        query_vec=qvecs.get(dense_for_candidates) if dense_for_candidates else None,
    )
    rows = res.layout.rows_of_pages(pages)
    bonus_pages = title_pages(res, claim, entity_texts) if title_bonus else None
    top_rows, top_scores = rank_rows(res, claim, rows, weights, qvecs, bonus_pages, title_bonus)
    uncertainty = entropy_bits(_softmax(top_scores[:10], temperature=0.05).tolist())
    top_rows, top_scores = top_rows[:k_sentences], top_scores[:k_sentences]
    top_pages = res.layout.page_of_rows(top_rows)

    try:
        topic_model = topics_mod.get_topics()
    except FileNotFoundError:
        topic_model = None

    by_page: dict[int, list[tuple[int, float]]] = {}
    for r, p, s in zip(top_rows, top_pages, top_scores):
        by_page.setdefault(int(p), []).append((int(res.layout.sent_ids[r]), float(s)))
    evidence = [
        Evidence(
            id=res.index.page_ids[p], title=res.index.titles[p], source="wikipedia", url=wikipedia_url(res.index.page_ids[p]),
            score=round(max(0.0, min(1.0, max(s for _, s in ss))), 4),  # best sentence score on the page
            sentences=[EvidenceSentence(text=res.index.page_sentences[p][sid], score=round(max(0.0, min(1.0, s)), 4)) for sid, s in ss],
            topic=topic_model.for_page(p) if topic_model else None,
        )
        for p, ss in by_page.items()
    ]
    evidence.sort(key=lambda e: -e.sentences[0].score)

    projection = None
    if project_with and len(top_rows):
        try:
            store = get_store(res, project_with)
            labels = [
                (f"{res.index.titles[p]}: {res.index.page_sentences[p][int(res.layout.sent_ids[r])][:70]}", float(sc))
                for r, p, sc in zip(top_rows, top_pages, top_scores)
            ]
            projection = projection_mod.get_projector(project_with).project(
                qvecs[project_with], claim[:70], np.asarray(store.matrix[top_rows], dtype=np.float32), labels,
            )
        except FileNotFoundError:
            projection = None
    return RetrievalOut(
        evidence=evidence, query=claim, score_entropy=round(uncertainty, 3), projection=projection,
    )
