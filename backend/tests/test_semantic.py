import numpy as np
import pytest

from app.retrieval import hybrid
from app.retrieval.hybrid import TFIDF
from app.retrieval.layout import SentenceLayout

@pytest.fixture()
def res(tiny_resources):
    return hybrid.get_resources()


def test_layout_maps_rows_to_pages_and_sentence_ids():
    lay = SentenceLayout.from_pages([["a", "", "b"], [], ["c"]])
    assert lay.n_rows == 3 and lay.sent_ids.tolist() == [0, 2, 0]
    assert lay.page_of_rows(np.array([0, 1, 2])).tolist() == [0, 0, 2]
    assert lay.rows_of_pages([2, 0]).tolist() == [2, 0, 1]


def test_minmax_handles_constant_scores():
    assert hybrid.minmax(np.array([2.0, 2.0])).tolist() == [0.0, 0.0]
    assert hybrid.minmax(np.array([1.0, 3.0, 2.0])).tolist() == [0.0, 1.0, 0.5]


def test_global_dense_search_returns_sorted_top_k(res):
    store = res.stores["fake"]
    q = store.encode(["Nobel Prize in Chemistry"])
    rows, scores = store.search_all(q, 3)
    assert rows.shape == (1, 3) and list(scores[0]) == sorted(scores[0], reverse=True)
    assert "Chemistry" in res.row_text(rows[0][:1])[0]


@pytest.mark.parametrize("weights", [{TFIDF: 1.0}, {"fake": 1.0}, {TFIDF: 0.5, "fake": 0.5}])
def test_every_scorer_mix_ranks_the_relevant_sentence_first(res, weights):
    claim = "Marie Curie won a Nobel Prize in Chemistry"
    rows = res.layout.rows_of_pages(list(range(len(res.index.page_ids))))
    top, _ = hybrid.rank_rows(res, claim, rows, weights)
    assert "Chemistry" in res.row_text(top[:1])[0]


def test_hybrid_search_returns_grouped_evidence_without_optional_artifacts(res):
    out = hybrid.hybrid_search(res, "Marie Curie won a Nobel Prize in Chemistry", ["Marie Curie"], weights={TFIDF: 0.5, "fake": 0.5}, k_sentences=3)
    assert out.evidence[0].title == "Marie Curie"
    assert sum(len(e.sentences) for e in out.evidence) == 3
    assert all(0 <= s.score <= 1 for e in out.evidence for s in e.sentences)
    assert out.projection is None and out.evidence[0].topic is None


def test_dense_candidate_pages_can_add_pages_tfidf_missed(res):
    hits, pages = hybrid.candidate_pages(res, "Nile river Africa Egypt", [], k_pages=1, use_titles=False, dense="fake", dense_k=5)
    assert len(pages) > 1 and pages[0] == hits[0].page_idx


def test_global_search_clamps_k_to_corpus_size(res):
    store = res.stores["fake"]
    rows, _ = store.search_all(store.encode(["anything"]), 10_000)
    assert rows.shape == (1, res.layout.n_rows)


def test_title_bonus_promotes_sentences_from_named_pages(res):
    claim = "Nobel Prize in Physics"
    rows = res.layout.rows_of_pages(list(range(len(res.index.page_ids))))
    einstein = res.index.titles.index("Albert Einstein")
    plain, _ = hybrid.rank_rows(res, claim, rows, {"fake": 1.0})
    boosted, _ = hybrid.rank_rows(res, claim, rows, {"fake": 1.0}, bonus_pages={einstein}, bonus=5.0)
    assert res.layout.page_of_rows(boosted[:1])[0] == einstein
    assert res.layout.page_of_rows(plain[:1])[0] != einstein
