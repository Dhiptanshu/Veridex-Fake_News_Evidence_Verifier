"""Word importance by occlusion: delete one word at a time and measure how far the verdict probability falls.

A word is important if removing it makes the verifier less sure of its verdict. This is model-agnostic, needs no
gradients, and each score is directly checkable by re-running the model without the word.
"""
import numpy as np

from app.schemas.stages import Attribution, Citation, WordScore
from app.verification import text as vtext

MAX_EVIDENCE_WORDS = 60  # keep the number of model passes bounded: 1 + claim words + evidence words


def occlude(predictor, claim: str, cite: Citation, target: str) -> Attribution:
    ti = vtext.LABELS.index(target)
    cw = claim.split()
    ew = cite.text.split()[:MAX_EVIDENCE_WORDS]

    def pair(c_words: list[str], e_words: list[str]) -> tuple[str, str]:
        return " ".join(c_words), vtext.fmt_evidence([{"title": cite.title, "text": " ".join(e_words)}])

    pairs = [pair(cw, ew)]
    pairs += [pair(cw[:j] + cw[j + 1 :], ew) for j in range(len(cw))]
    pairs += [pair(cw, ew[:j] + ew[j + 1 :]) for j in range(len(ew))]
    p = predictor.predict(pairs)[:, ti]
    drops = np.clip(p[0] - p[1:], 0.0, None)
    top = float(drops.max()) if len(drops) else 0.0
    scores = drops / top if top > 1e-6 else np.zeros_like(drops)
    return Attribution(
        cite=cite.n, target=target,  # type: ignore[arg-type]
        claim=[WordScore(word=w, score=round(float(s), 3)) for w, s in zip(cw, scores[: len(cw)])],
        evidence=[WordScore(word=w, score=round(float(s), 3)) for w, s in zip(ew, scores[len(cw) :])],
    )
