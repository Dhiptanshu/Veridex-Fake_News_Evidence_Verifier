from app.explain import attribution, differences, rationale, select, summarize
from app.explain.clean import tidy
from app.schemas.stages import (
    Citation, Differences, Evidence, EvidenceSentence, RetrievalOut, SentenceVerdict, VerificationOut,
)
from app.stages.explanation import explain
from app.verification import models


def _sv(pid, title, text, s, r, n, score=0.8):
    return SentenceVerdict(evidence_id=pid, title=title, text=text, retrieval_score=score, supported=s, refuted=r, neutral=n)


def _ver(label, sentences):
    probs = {"supported": 0.0, "refuted": 0.0, "not_enough_info": 0.0}
    probs[label] = 0.8
    return VerificationOut(label=label, confidence=0.8, probabilities=probs, per_evidence=[], per_sentence=sentences)


def _ret(sentences):
    by: dict[str, Evidence] = {}
    for sv in sentences:
        ev = by.setdefault(sv.evidence_id, Evidence(id=sv.evidence_id, title=sv.title, source="wikipedia", score=0.8, sentences=[]))
        ev.sentences.append(EvidenceSentence(text=sv.text, score=sv.retrieval_score))
    return RetrievalOut(evidence=list(by.values()))


GERMANY = [
    _sv("Berlin", "Berlin", "Berlin is the capital of Germany.", 0.03, 0.81, 0.16, 0.9),
    _sv("Paris", "Paris", "Paris is the capital and most populous city of France.", 0.05, 0.62, 0.33, 0.8),
    _sv("Germany", "Germany", "The country has sixteen states.", 0.20, 0.10, 0.70, 0.7),
]


def test_refuted_cites_the_sentences_that_lean_refuted_best_first():
    cites = select.select_citations(_ver("refuted", GERMANY), _ret(GERMANY))
    assert [c.title for c in cites] == ["Berlin", "Paris"]  # the neutral sentence is not decisive
    assert [c.n for c in cites] == [1, 2] and all(c.role == "decisive" for c in cites)


def test_not_enough_info_cites_only_the_closest_sentence():
    cites = select.select_citations(_ver("not_enough_info", GERMANY), _ret(GERMANY))
    assert len(cites) == 1 and cites[0].role == "closest" and cites[0].title == "Berlin"


def test_duplicate_sentences_are_cited_once():
    dup = [_sv("A", "A", "Same sentence.", 0.9, 0.0, 0.1), _sv("B", "B", "Same sentence.", 0.85, 0.0, 0.15)]
    assert len(select.select_citations(_ver("supported", dup), _ret(dup))) == 1


def test_verifiers_without_sentence_scores_fall_back_to_best_retrieved():
    cites = select.select_citations(_ver("supported", []), _ret(GERMANY))
    assert [c.title for c in cites] == ["Berlin", "Paris"] and all(c.role == "closest" for c in cites)


def test_differing_terms_are_a_set_difference_of_informative_words(tiny_resources):
    only_claim, only_evidence = differences.differing_terms("Paris is the capital of Germany.", "Berlin is the capital of Germany.")
    assert only_claim == ["Paris"] and only_evidence == ["Berlin"]
    assert differences.missing_from("Paris is the capital of Germany.", ["Berlin is the capital of Germany."]) == ["Paris"]


def test_rationale_is_built_only_from_supplied_facts():
    cites = [Citation(n=1, evidence_id="Berlin", title="Berlin", text="Berlin is the capital of Germany.", role="decisive")]
    text = rationale.build("refuted", 0.8, cites, Differences(cite=1, claim_only=["Paris"], evidence_only=["Berlin"]), ["Paris"])
    assert "refuted (80% confidence)" in text and "[1]" in text and "Berlin is the capital of Germany." in text
    assert "reads “Berlin” [1] as conflicting with the claim" in text
    assert "the claim mentions Paris" in text and "Not found in any retrieved sentence: Paris." in text
    assert "uncertain" in rationale.build("supported", 0.5, cites, None, [])
    nei = rationale.build("not_enough_info", 0.7, cites, None, ["Paris"])
    assert "closest evidence" in nei and "none of the retrieved sentences mention: Paris" in nei


def test_long_quotes_are_shortened_at_a_word_boundary():
    q = rationale._quote("word " * 100, limit=40)
    assert q.endswith("…”") and len(q) <= 44


def test_mmr_summary_skips_redundant_sentences(tiny_resources):
    sents = ["Marie Curie won the Nobel Prize in Physics.", "Marie Curie won the Nobel Prize in Physics.",
             "She also won the Nobel Prize in Chemistry.", "The Nile is a river in Africa."]
    out = summarize.mmr_summary("Marie Curie Nobel Prize", sents, k=2)
    assert len(out) == 2 and out.count("Marie Curie won the Nobel Prize in Physics.") == 1


def test_occlusion_scores_are_normalised_and_align_with_the_words(tiny_resources):
    cite = Citation(n=1, evidence_id="Marie_Curie", title="Marie Curie", text="She won the Nobel Prize.", role="decisive")
    a = attribution.occlude(models.load("bert"), "Marie Curie won a prize", cite, "supported")
    assert [w.word for w in a.claim] == "Marie Curie won a prize".split()
    assert [w.word for w in a.evidence] == "She won the Nobel Prize.".split()
    scores = [w.score for w in a.claim + a.evidence]
    assert all(0 <= s <= 1 for s in scores) and max(scores) in (0.0, 1.0)


def test_explain_end_to_end_with_the_stacked_verifier(tiny_resources):
    from app.stages.verification import verify_stacked

    ret = _ret(GERMANY)
    ver = verify_stacked("Paris is the capital of Germany.", ret)
    out = explain("Paris is the capital of Germany.", ver, ret, "mmr")
    assert out.citations and out.rationale and out.summary
    assert out.attribution is not None and out.attribution.cite == 1
    assert all(i in {e.id for e in ret.evidence} for i in out.cited_evidence_ids)
    assert out.summary_method.startswith("MMR")


def test_tidy_removes_pronunciation_guides_but_keeps_real_parentheses():
    assert tidy("Paris (French pronunciation: [pɑʁi], [paʁi]) is the capital of France.") == "Paris is the capital of France."
    assert tidy("Berlin ([bəɹˈlɪn], [bɛɐ̯ˈliːn]) is the capital.") == "Berlin is the capital."
    assert tidy("Curie (born 7 November 1867) was a physicist.") == "Curie (born 7 November 1867) was a physicist."
    assert tidy("Plain sentence .") == "Plain sentence."
    # a guide and dates in one parenthesis: only the guide goes (regression: the whole parenthesis used to vanish)
    assert tidy("Neefe ([ˈneːfə]; 5 February 1748 -- 28 January 1798) was a composer.") == "Neefe (5 February 1748 -- 28 January 1798) was a composer."


def test_page_title_counts_as_context_so_pronoun_sentences_do_not_look_different(tiny_resources):
    only_claim, _ = differences.differing_terms("Marie Curie won a prize.", "She won the Nobel Prize.", title="Marie Curie")
    assert "Marie" not in only_claim and "Curie" not in only_claim


def test_supported_verdict_warns_about_numbers_no_evidence_mentions():
    cites = [Citation(n=1, evidence_id="A", title="A", text="A was a composer.", role="decisive")]
    text = rationale.build("supported", 0.8, cites, None, [], ["1798"])
    assert "Caution: the claim's 1798 appears in none of the retrieved sentences" in text
    assert "Caution" not in rationale.build("refuted", 0.8, cites, None, [], ["1798"])  # expected for a refutation


def test_summary_candidates_leave_out_sentences_the_verifier_finds_irrelevant():
    sents = [
        _sv("W", "Larry Wilmore", "Larry Wilmore is a comedian.", 0.01, 0.01, 0.98, 0.72),
        _sv("D", "William Denny Jr.", "He is Catholic.", 0.01, 0.01, 0.98, 0.67),
        _sv("X", "Larry Wilmore", "He produces television.", 0.70, 0.01, 0.29, 0.70),
    ]
    got = select.summary_candidates(_ver("supported", sents), _ret(sents))
    assert ("William Denny Jr.", "He is Catholic.") not in got
    assert got[0] == ("Larry Wilmore", "He produces television.")  # the one the verifier found relevant comes first
    assert len(got) >= 2  # topped up to the minimum with the best-ranked remaining sentence
