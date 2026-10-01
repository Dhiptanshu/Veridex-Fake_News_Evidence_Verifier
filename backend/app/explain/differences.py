"""Informative words that the claim and an evidence sentence do not share (a plain, checkable set difference)."""
from functools import lru_cache

from app.explain.clean import tidy
from app.nlp import resources, text
from app.retrieval.tfidf import get_index
from app.retrieval.vectors import idf_table


# Filler words that are not NLTK stop-words but never make a claim differ in substance.
FILLER = frozenset({"also", "may", "often", "however", "several", "many", "one", "well", "known", "include", "including"})


@lru_cache(maxsize=1)
def _idf() -> tuple[dict[str, float], float]:
    return idf_table(get_index().vectorizer)


def content_terms(sentence: str) -> dict[str, str]:
    """lemma -> surface form for the content words of `sentence` (stop-words and punctuation removed)."""
    a = text.analyze(tidy(sentence))
    stop = resources.stopwords()
    out: dict[str, str] = {}
    for tok, lem in zip(a.tokens, a.lemmas):
        if lem in a.normalized and tok.lower() not in stop and lem not in FILLER and len(lem) > 1:
            out.setdefault(lem, tok)
    return out


def differing_terms(claim: str, sentence: str, title: str = "", top: int = 3) -> tuple[list[str], list[str]]:
    """(in the claim but not the sentence, in the sentence but not the claim), rarest (most informative) words first.

    The page `title` counts as part of the sentence: "She won ..." on the page "Marie Curie" is about Marie Curie."""
    idf, default = _idf()
    c, e = content_terms(claim), content_terms(f"{title}. {sentence}" if title else sentence)

    def pick(only: dict[str, str]) -> list[str]:
        ranked = sorted(only, key=lambda lem: -idf.get(lem, default))
        return [only[lem] for lem in ranked[:top]]

    return pick({k: v for k, v in c.items() if k not in e}), pick({k: v for k, v in e.items() if k not in c})


def missing_from(claim: str, sentences: list[str], titles: list[str] | None = None, top: int = 3) -> list[str]:
    """Informative claim words that appear in none of `sentences` (or their page titles)."""
    idf, default = _idf()
    have: set[str] = set()
    for s in [*sentences, *(titles or [])]:
        have |= set(content_terms(s))
    only = {k: v for k, v in content_terms(claim).items() if k not in have}
    return [only[lem] for lem in sorted(only, key=lambda lem: -idf.get(lem, default))[:top]]
