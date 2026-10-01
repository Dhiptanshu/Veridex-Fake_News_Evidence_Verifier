"""Choosing which evidence sentences an explanation cites."""
from app.schemas.stages import Citation, RetrievalOut, SentenceVerdict, VerificationOut

MAX_DECISIVE = 3
LABEL_INDEX = {"supported": "supported", "refuted": "refuted", "not_enough_info": "neutral"}


def _prob(s: SentenceVerdict, label: str) -> float:
    return getattr(s, LABEL_INDEX[label])


def select_citations(ver: VerificationOut, ret: RetrievalOut) -> list[Citation]:
    """Decisive sentences for a supported/refuted verdict; the closest sentence when nothing settles the claim.

    A sentence is decisive when, read on its own, the verifier already leans the same way as the verdict. The best one is
    always cited; extra ones must be at least half as convincing and not weak (>= 0.3).
    """
    if not ver.per_sentence:  # verifiers that do not score sentences: fall back to the best-matching retrieved ones
        flat = sorted(((s.score, e.id, e.title, s.text) for e in ret.evidence for s in e.sentences), key=lambda t: -t[0])
        return [Citation(n=i + 1, evidence_id=pid, title=t, text=x, role="closest") for i, (_, pid, t, x) in enumerate(flat[:2])]

    if ver.label == "not_enough_info":
        best = max(ver.per_sentence, key=lambda s: s.retrieval_score)
        return [_cite(1, best, "closest")]

    ranked = sorted(ver.per_sentence, key=lambda s: -_prob(s, ver.label))
    top = _prob(ranked[0], ver.label)
    chosen = [ranked[0]] + [s for s in ranked[1:] if _prob(s, ver.label) >= max(0.3, 0.5 * top)]
    seen: set[str] = set()
    out: list[Citation] = []
    for s in chosen:
        if s.text in seen:  # the same sentence can be retrieved through two pages
            continue
        seen.add(s.text)
        out.append(_cite(len(out) + 1, s, "decisive"))
        if len(out) == MAX_DECISIVE:
            break
    return out


def _cite(n: int, s: SentenceVerdict, role: str) -> Citation:
    return Citation(
        n=n, evidence_id=s.evidence_id, title=s.title, text=s.text, role=role,  # type: ignore[arg-type]
        supported=s.supported, refuted=s.refuted, neutral=s.neutral,
    )


def summary_candidates(ver: VerificationOut, ret: RetrievalOut, minimum: int = 2) -> list[tuple[str, str]]:
    """(page title, sentence) pairs worth summarising: those the verifier reads as bearing on the claim (supported or
    refuted probability >= 0.3), topped up with the best-ranked retrieved sentences so there are at least `minimum`.

    Irrelevant retrieved sentences (often from other pages) must stay out, or a summary would present them as facts
    about the claim's subject."""
    ranked = sorted(((s.score, e.title, s.text) for e in ret.evidence for s in e.sentences), key=lambda t: -t[0])
    seen: set[str] = set()
    ordered = [(t, x) for _, t, x in ranked if not (x in seen or seen.add(x))]
    if not ver.per_sentence:
        return ordered[:3]
    bearing = {s.text for s in ver.per_sentence if s.supported + s.refuted >= 0.3}
    out = [(t, x) for t, x in ordered if x in bearing]
    for t, x in ordered:
        if len(out) >= minimum:
            break
        if (t, x) not in out:
            out.append((t, x))
    return out
