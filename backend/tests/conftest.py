"""Shared fixtures: a tiny in-memory evidence index so tests never depend on the 54 MB real one."""
import zlib

import numpy as np
import pytest

from app.core.config import settings
from app.data.models import CorpusPage
from app.nlp import pmi as pmi_mod
from app.nlp import resources
from app.nlp import topics as topics_mod
from app.retrieval import hybrid, tfidf, vectors
from app.retrieval import projection as projection_mod
from app.retrieval.layout import SentenceLayout
from app.verification import models as vmodels
from app.verification import text as vtext

from fake_models import write_fake_models

settings.placeholder_delay_s = 0

_PAGES = [
    ("Marie_Curie", ["Marie Curie was a physicist and chemist.", "She won the Nobel Prize in Physics in 1903.",
                     "She won a second Nobel Prize in Chemistry in 1911."]),
    ("Paris", ["Paris is the capital and most populous city of France.", "The city lies on the river Seine."]),
    ("Soul_Food_-LRB-film-RRB-", ["Soul Food is a 1997 American comedy-drama film.", "The film was released by Fox 2000 Pictures."]),
    ("Albert_Einstein", ["Albert Einstein was a physicist born in Germany.", "He won the Nobel Prize in Physics in 1921."]),
    ("Nile", ["The Nile is a river in Africa.", "It flows north through Egypt to the Mediterranean Sea."]),
]


DIM = 64


def hash_embed(texts: list[str]) -> np.ndarray:
    """Deterministic stand-in encoder: hashed bag of words, L2-normalised. Keeps tests independent of real models."""
    out = np.zeros((len(texts), DIM), dtype=np.float32)
    for i, t in enumerate(texts):
        for w in vectors.tokens(t):
            out[i, zlib.crc32(w.encode()) % DIM] += 1.0
    norms = np.linalg.norm(out, axis=1, keepdims=True)
    return out / np.where(norms == 0, 1, norms)


def _raise_missing(*_a, **_k):
    raise FileNotFoundError("not available in tests")


@pytest.fixture(scope="session", autouse=True)
def tiny_resources(tmp_path_factory):
    try:
        resources.spacy_nlp()
        resources.stopwords()
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"NLP resources missing ({exc}); run python ml/setup_nlp.py", allow_module_level=False)

    from app.data.wiki import display_title

    pages = [CorpusPage(id=i, title=display_title(i), sentences=s, gold=False) for i, s in _PAGES]
    index = tfidf.TfidfIndex.build(pages, min_df=1)
    table = pmi_mod.PmiTable.build((s for _, ss in _PAGES for s in ss), min_count=1)

    mp = pytest.MonkeyPatch()
    mp.setattr(tfidf.TfidfIndex, "load", staticmethod(lambda path=None: index))
    mp.setattr(pmi_mod.PmiTable, "load", staticmethod(lambda path=None: table))
    tfidf.get_index.cache_clear()
    pmi_mod.get_table.cache_clear()

    layout = SentenceLayout.from_pages(index.page_sentences)
    rows = np.arange(layout.n_rows)
    texts = [f"{index.titles[p]}. {index.page_sentences[p][s]}" for p, s in zip(layout.page_of_rows(rows), layout.sent_ids)]
    matrix = hash_embed(texts)
    res = hybrid.Resources(
        index, layout, {n: vectors.VectorStore(n, matrix, hash_embed) for n in ("bge_small", "minilm", "w2v", "glove", "fake")}
    )
    mp.setattr(hybrid, "get_resources", lambda: res)
    model_dir = tmp_path_factory.mktemp("models")
    write_fake_models(model_dir)
    mp.setattr(vtext, "MODEL_DIR", model_dir)
    vmodels.load.cache_clear()
    mp.setattr(topics_mod, "get_topics", _raise_missing)
    mp.setattr(projection_mod, "get_projector", _raise_missing)
    yield index
    mp.undo()
    vmodels.load.cache_clear()
    tfidf.get_index.cache_clear()
    pmi_mod.get_table.cache_clear()
