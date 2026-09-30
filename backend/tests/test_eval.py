from app.data.models import Claim, SentenceRef
from app.eval import retrieval as ev


def _claim(*sets):
    return Claim(
        id=1, claim="c", label="supported",
        evidence_sets=[[SentenceRef(page=p, sent_id=i) for p, i in s] for s in sets],
    )


def test_page_hit_requires_all_pages_of_a_set():
    c = _claim([("A", 0), ("B", 1)])
    assert not ev.page_hit(c, ["A", "X", "B"], k=2)
    assert ev.page_hit(c, ["A", "X", "B"], k=3)


def test_page_hit_accepts_any_alternative_set():
    c = _claim([("A", 0)], [("B", 0)])
    assert ev.page_hit(c, ["B"], k=1)


def test_sentence_hit_is_sentence_exact():
    c = _claim([("A", 2)])
    assert not ev.sentence_hit(c, [("A", 0), ("A", 1)], k=2)
    assert ev.sentence_hit(c, [("A", 0), ("A", 2)], k=2)


def test_reciprocal_rank_uses_first_gold_page():
    c = _claim([("A", 0)], [("B", 0)])
    assert ev.reciprocal_rank(c, ["X", "B", "A"]) == 0.5
    assert ev.reciprocal_rank(c, ["X", "Y"]) == 0.0
