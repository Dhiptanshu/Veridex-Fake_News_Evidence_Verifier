"""Templated rationale. Every statement is filled from data (the verdict, quoted evidence, set differences), so the text
cannot assert anything the pipeline did not actually find."""
from app.explain.clean import tidy
from app.schemas.stages import Citation, Differences

VERDICT_WORDS = {"supported": "supported", "refuted": "refuted", "not_enough_info": "not verifiable from the retrieved evidence"}


def _quote(text: str, limit: int = 220) -> str:
    text = tidy(text)
    return "“" + (text if len(text) <= limit else text[: limit - 1].rsplit(" ", 1)[0] + "…") + "”"


def _terms(words: list[str]) -> str:
    return ", ".join(words)


def build(
    label: str, confidence: float, citations: list[Citation], diff: Differences | None, missing: list[str],
    unverified_numbers: list[str] | None = None,
) -> str:
    parts = [f"The claim is {VERDICT_WORDS[label]} ({confidence:.0%} confidence)."]
    if confidence < 0.6:
        parts.append("The model is uncertain, so treat this verdict with caution.")

    if label == "not_enough_info":
        if citations:
            c = citations[0]
            parts.append(
                "No retrieved sentence clearly confirms or contradicts it. "
                f"The closest evidence is “{c.title}” [{c.n}]: {_quote(c.text)}"
            )
        if missing:
            parts.append(f"Terms from the claim that none of the retrieved sentences mention: {_terms(missing)}.")
        return " ".join(parts)

    verb = "as supporting" if label == "supported" else "as conflicting with"
    for i, c in enumerate(citations):
        lead = f"The model reads “{c.title}” [{c.n}] {verb} the claim:" if i == 0 else f"Also “{c.title}” [{c.n}]:"
        parts.append(f"{lead} {_quote(c.text)}")
    if diff and (diff.claim_only or diff.evidence_only):
        bits = []
        if diff.claim_only:
            bits.append(f"the claim mentions {_terms(diff.claim_only)}, which [{diff.cite}] does not")
        if diff.evidence_only:
            bits.append(f"[{diff.cite}] mentions {_terms(diff.evidence_only)}, which the claim does not")
        parts.append("Difference in wording: " + "; ".join(bits) + ".")
    if missing:
        parts.append(f"Not found in any retrieved sentence: {_terms(missing)}.")
    if label == "supported" and unverified_numbers:
        parts.append(
            f"Caution: the claim's {_terms(unverified_numbers)} appears in none of the retrieved sentences, "
            "so this verdict may rest on incomplete evidence."
        )
    return " ".join(parts)
