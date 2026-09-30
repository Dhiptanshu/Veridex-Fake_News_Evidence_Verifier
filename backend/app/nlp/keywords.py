"""Keyword extraction: TF-IDF weights filtered by POS, and PMI collocations. Pure functions over prepared inputs."""
from collections import Counter

from app.nlp import pmi as pmi_mod
from app.nlp import resources
from app.nlp.text import is_content_tag
from app.retrieval.tfidf import TfidfIndex
from app.schemas.stages import Keyword, PreprocessOut



def tfidf_keywords(index: TfidfIndex, pre: PreprocessOut, top_n: int = 8) -> list[Keyword]:
    """Terms and bigrams ranked by TF-IDF weight in the claim, keeping only those built from content words (by POS)."""
    content = {p.token.lower() for p in pre.pos if is_content_tag(p.tag)}
    # sklearn drops stop-words *before* forming bigrams ("won two nobel" -> "won nobel"); keep real adjacent pairs only.
    toks = [t.lower() for t in pre.tokens]
    adjacent = {f"{a} {b}" for a, b in zip(toks, toks[1:])}
    row = index.encode([pre.original])
    names = index.feature_names()
    scored = []
    for col, weight in zip(row.indices, row.data):
        term = names[col]
        if all(w in content for w in term.split()) and (" " not in term or term in adjacent):
            scored.append((term, float(weight)))
    scored.sort(key=lambda t: -t[1])
    kept: list[tuple[str, float]] = []
    for term, w in scored:
        # A unigram already covered by a stronger kept bigram ("curie" inside "marie curie") adds nothing.
        if " " not in term and any(term in k.split() for k, _ in kept if " " in k):
            continue
        kept.append((term, w))
        if len(kept) == top_n:
            break
    return [Keyword(term=t, score=round(w, 4), kind="phrase" if " " in t else "term") for t, w in kept]


def pmi_phrases(table: pmi_mod.PmiTable, claim: str, min_pmi: float = 3.0, top_n: int = 5) -> list[Keyword]:
    """Adjacent word pairs in the claim that co-occur in the corpus far above chance."""
    stop = resources.stopwords()
    toks = pmi_mod.tokens(claim)
    out = []
    for a, b in zip(toks, toks[1:]):
        if a in stop or b in stop:
            continue
        score = table.pmi(a, b)
        if score is not None and score >= min_pmi:
            out.append(Keyword(term=f"{a} {b}", score=round(score, 2), kind="phrase"))
    out.sort(key=lambda k: -k.score)
    return out[:top_n]


def frequency_keywords(pre: PreprocessOut, top_n: int = 8) -> list[Keyword]:
    counts = Counter(pre.normalized)
    total = sum(counts.values()) or 1
    return [Keyword(term=t, score=round(c / total, 4)) for t, c in counts.most_common(top_n)]


def build_query(entities: list[str], keywords: list[Keyword]) -> str:
    seen: set[str] = set()
    parts: list[str] = []
    for text in [*entities, *(k.term for k in keywords)]:
        key = text.lower()
        if key not in seen:
            seen.add(key)
            parts.append(text)
    return " ".join(parts)
