"""Retrieval metrics against FEVER gold evidence. Only verifiable claims (with gold evidence) are scored.

A claim counts as a hit at k if ALL of the pages (or sentences) of at least one gold evidence set are in the
top-k; FEVER evidence sets are conjunctive (multi-hop claims need every piece).
"""
from collections.abc import Sequence

from app.data.models import Claim


def verifiable(claims: Sequence[Claim]) -> list[Claim]:
    return [c for c in claims if c.evidence_sets]


def page_hit(claim: Claim, ranked_pages: Sequence[str], k: int) -> bool:
    top = set(ranked_pages[:k])
    return any({r.page for r in s} <= top for s in claim.evidence_sets)


def sentence_hit(claim: Claim, ranked_sentences: Sequence[tuple[str, int]], k: int) -> bool:
    top = set(ranked_sentences[:k])
    return any({(r.page, r.sent_id) for r in s} <= top for s in claim.evidence_sets)


def reciprocal_rank(claim: Claim, ranked_pages: Sequence[str]) -> float:
    gold = {r.page for s in claim.evidence_sets for r in s}
    for rank, page in enumerate(ranked_pages, start=1):
        if page in gold:
            return 1.0 / rank
    return 0.0


def summarize_pages(claims: Sequence[Claim], rankings: Sequence[Sequence[str]], ks=(1, 5, 10, 20)) -> dict[str, float]:
    n = len(claims)
    out = {f"page_recall@{k}": round(sum(page_hit(c, r, k) for c, r in zip(claims, rankings)) / n, 4) for k in ks}
    out["page_mrr"] = round(sum(reciprocal_rank(c, r) for c, r in zip(claims, rankings)) / n, 4)
    return out


def summarize_sentences(claims: Sequence[Claim], rankings: Sequence[Sequence[tuple[str, int]]], ks=(1, 5)) -> dict[str, float]:
    n = len(claims)
    return {f"sentence_recall@{k}": round(sum(sentence_hit(c, r, k) for c, r in zip(claims, rankings)) / n, 4) for k in ks}
