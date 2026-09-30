"""Shared fixtures: a tiny in-memory evidence index so tests never depend on the 54 MB real one."""
import pytest

from app.core.config import settings
from app.data.models import CorpusPage
from app.nlp import pmi as pmi_mod
from app.nlp import resources
from app.retrieval import tfidf

settings.placeholder_delay_s = 0

_PAGES = [
    ("Marie_Curie", ["Marie Curie was a physicist and chemist.", "She won the Nobel Prize in Physics in 1903.",
                     "She won a second Nobel Prize in Chemistry in 1911."]),
    ("Paris", ["Paris is the capital and most populous city of France.", "The city lies on the river Seine."]),
    ("Soul_Food_-LRB-film-RRB-", ["Soul Food is a 1997 American comedy-drama film.", "The film was released by Fox 2000 Pictures."]),
    ("Albert_Einstein", ["Albert Einstein was a physicist born in Germany.", "He won the Nobel Prize in Physics in 1921."]),
    ("Nile", ["The Nile is a river in Africa.", "It flows north through Egypt to the Mediterranean Sea."]),
]


@pytest.fixture(scope="session", autouse=True)
def tiny_resources():
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
    yield index
    mp.undo()
    tfidf.get_index.cache_clear()
    pmi_mod.get_table.cache_clear()
