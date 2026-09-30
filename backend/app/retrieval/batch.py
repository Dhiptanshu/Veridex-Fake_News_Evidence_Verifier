"""Bulk retrieval for many claims at once (training data and evaluation). Mirrors the served default retriever:
BGE-small dense scores, a small bonus for pages whose title the claim mentions, candidates = TF-IDF+title pages plus
pages of the globally closest dense sentences."""
from dataclasses import dataclass

import numpy as np

from app.nlp import resources
from app.retrieval import hybrid
from app.retrieval.search import DEFAULT_BOOST


@dataclass
class Hit:
    page_idx: int
    sent_id: int
    score: float


def retrieve_many(
    res: hybrid.Resources, claims: list[str], *, store_name: str = "bge_small", k: int = 5, title_bonus: float = 0.02,
    k_pages: int = 10, dense_k: int = 20, chunk: int = 256, progress=None,
) -> list[list[Hit]]:
    store = hybrid.get_store(res, store_name)
    idx, nlp = res.index, resources.spacy_nlp()
    out: list[list[Hit]] = []
    for start in range(0, len(claims), chunk):
        texts = claims[start : start + chunk]
        qv = store.encode(texts)
        ents = [{e.text for e in doc.ents} for doc in nlp.pipe(texts, batch_size=64, disable=["parser", "lemmatizer"])]
        titles = [hybrid.title_pages(res, t, list(e)) for t, e in zip(texts, ents)]
        hits = idx.rank_pages(texts, titles, DEFAULT_BOOST, k=k_pages)
        dense_rows, _ = store.search_all(qv, dense_k)
        for i, text in enumerate(texts):
            pages = [h.page_idx for h in hits[i]]
            seen = set(pages)
            for p in res.layout.page_of_rows(dense_rows[i]):
                if int(p) not in seen:
                    seen.add(int(p))
                    pages.append(int(p))
            rows = res.layout.rows_of_pages(pages)
            top, scores = hybrid.rank_rows(res, text, rows, {store_name: 1.0}, {store_name: qv[i]}, titles[i], title_bonus)
            out.append([Hit(int(res.layout.page_of_rows(np.array([r]))[0]), int(res.layout.sent_ids[r]), float(s)) for r, s in zip(top[:k], scores[:k])])
        if progress:
            progress(start + len(texts), len(claims))
    return out
