import math

from app.nlp import entities, keywords, pmi, text, wordnet
from app.retrieval import search, tfidf


def test_analyze_lemmatizes_and_keeps_content_verbs():
    a = text.analyze("Marie Curie won two Nobel Prizes.")
    assert a.normalized == ["marie", "curie", "win", "two", "nobel", "prize"]
    assert [p.tag for p in a.pos][:2] == ["NNP", "NNP"]
    assert a.sentiment is not None and -1 <= a.sentiment.polarity <= 1


def test_entities_chunks_and_triples():
    out = entities.extract("Roman Atwood is a content creator.")
    assert [(e.text, e.label) for e in out.entities] == [("Roman Atwood", "PERSON")]
    assert any(t.subject == "Roman Atwood" and t.object == "a content creator" for t in out.triples)


def test_wordnet_expansion_skips_proper_nouns_and_stopwords():
    extra = wordnet.expand(["film", "paris", "the"], ["NN", "NNP", "DT"])
    assert "movie" in extra and "paris" not in extra


def test_tfidf_keywords_are_content_words_and_adjacent(tiny_resources):
    pre = text.analyze("Marie Curie won two Nobel Prizes.")
    terms = [k.term for k in keywords.tfidf_keywords(tiny_resources, pre)]
    assert "won nobel" not in terms  # 'two' sits between them
    assert all(" " in t or t not in {"two", "the"} for t in terms)


def test_pmi_is_high_for_collocations_and_none_for_unseen_pairs():
    table = pmi.PmiTable.build(["nobel prize winner"] * 4 + ["random other words here"] * 20, min_count=1)
    assert table.pmi("nobel", "prize") > 3
    assert table.pmi("nobel", "words") is None


def test_entropy_bits():
    assert search.entropy_bits([1.0]) == 0.0
    assert math.isclose(search.entropy_bits([0.5, 0.5]), 1.0)
    assert search.entropy_bits([0.97, 0.01, 0.01, 0.01]) < search.entropy_bits([0.25] * 4)


def test_title_lookup_strips_disambiguation_and_requires_capitalised_single_words(tiny_resources):
    idx = tiny_resources
    hits = idx.titles_in_text("Fox 2000 Pictures released the film Soul Food.")
    assert {idx.titles[i] for i in hits} == {"Soul Food (film)"}
    assert idx.titles_in_text("the capital of france is big") == set()  # lone lowercase words never match titles
    assert tfidf.title_key("Soul Food (film)") == "soul food"


def test_title_boost_changes_ranking(tiny_resources):
    idx = tiny_resources
    claim = "Nobel Prize in Physics"
    plain = idx.rank_pages([claim], k=2)[0]
    boost_to = idx.titles.index("Nile")
    boosted = idx.rank_pages([claim], [{boost_to}], boost=5.0, k=2)[0]
    assert boosted[0].page_idx == boost_to and plain[0].page_idx != boost_to
