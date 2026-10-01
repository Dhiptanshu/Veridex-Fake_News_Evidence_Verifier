import asyncio

import numpy as np

from app.schemas.stages import EvidenceVerdict, RetrievalOut, SentenceVerdict, VerificationOut
from app.stages.base import Stage, StageContext, register
from app.verification import models, stack
from app.verification import text as vtext


def verify(kind: str, claim: str, ret: RetrievalOut) -> VerificationOut:
    """Verdict from the best `MAX_EVIDENCE` sentences overall, plus a stance for each evidence page on its own."""
    sentences = sorted(
        ((s.score, e.title, s.text) for e in ret.evidence for s in e.sentences), key=lambda t: -t[0]
    )[: vtext.MAX_EVIDENCE]
    predictor = models.load(kind)
    pairs = [(claim, vtext.fmt_evidence([{"title": t, "text": x} for _, t, x in sentences]))]
    pairs += [
        (claim, vtext.fmt_evidence([{"title": e.title, "text": s.text} for s in e.sentences])) for e in ret.evidence
    ]
    probs = predictor.predict(pairs)
    overall = probs[0]
    k = int(np.argmax(overall))
    return VerificationOut(
        label=vtext.LABELS[k],  # type: ignore[arg-type]
        confidence=round(float(overall[k]), 4),
        probabilities={lab: round(float(p), 4) for lab, p in zip(vtext.LABELS, overall)},  # type: ignore[misc]
        per_evidence=[
            EvidenceVerdict(evidence_id=e.id, supported=round(float(p[0]), 4), refuted=round(float(p[1]), 4), neutral=round(float(p[2]), 4))
            for e, p in zip(ret.evidence, probs[1:])
        ],
    )


def _top_sentences(ret: RetrievalOut) -> list[tuple[float, str, str, str]]:
    """The best `MAX_EVIDENCE` sentences overall as (score, page id, title, text), best first."""
    flat = [(s.score, e.id, e.title, s.text) for e in ret.evidence for s in e.sentences]
    return sorted(flat, key=lambda t: -t[0])[: vtext.MAX_EVIDENCE]


def verify_stacked(claim: str, ret: RetrievalOut) -> VerificationOut:
    """BERT reads the claim with each top sentence alone and with all of them together; a logistic-regression stacker
    (trained on the validation split) turns those scores into the final, calibrated verdict."""
    top = _top_sentences(ret)
    predictor = models.load("bert")
    pairs = [(claim, vtext.fmt_evidence([{"title": t, "text": x}])) for _, _, t, x in top]
    pairs.append((claim, vtext.fmt_evidence([{"title": t, "text": x} for _, _, t, x in top])))
    probs = predictor.predict(pairs)
    sent, concat = probs[:-1], probs[-1]
    overall = models.load_stacker().predict_proba(stack.features(sent, concat, top[0][0])[None, :])[0]
    k = int(np.argmax(overall))

    # Stance of each evidence page: its most decisive sentence (largest supported/refuted probability) on its own.
    per_page: dict[str, np.ndarray] = {}
    for (_, page_id, _, _), p in zip(top, sent):
        if page_id not in per_page or max(p[0], p[1]) > max(per_page[page_id][0], per_page[page_id][1]):
            per_page[page_id] = p
    neutral = np.array([0.0, 0.0, 1.0])
    per_sentence = [
        SentenceVerdict(
            evidence_id=pid, title=t, text=x, retrieval_score=round(float(sc), 4),
            supported=round(float(p[0]), 4), refuted=round(float(p[1]), 4), neutral=round(float(p[2]), 4),
        )
        for (sc, pid, t, x), p in zip(top, sent)
    ]
    return VerificationOut(
        per_sentence=per_sentence,
        label=vtext.LABELS[k],  # type: ignore[arg-type]
        confidence=round(float(overall[k]), 4),
        probabilities={lab: round(float(p), 4) for lab, p in zip(vtext.LABELS, overall)},  # type: ignore[misc]
        per_evidence=[
            EvidenceVerdict(
                evidence_id=e.id, supported=round(float((per_page.get(e.id, neutral))[0]), 4),
                refuted=round(float((per_page.get(e.id, neutral))[1]), 4), neutral=round(float((per_page.get(e.id, neutral))[2]), 4),
            )
            for e in ret.evidence
        ],
    )


def _register(kind: str, title: str, desc: str, family: str, is_default: bool = False, stacked: bool = False) -> None:
    @register
    class Verifier(Stage):
        slot = "verification"
        name = kind
        label = title
        description = desc
        default = is_default

        async def run(self, ctx: StageContext) -> VerificationOut:
            ret: RetrievalOut = ctx.results["retrieval"]  # type: ignore[assignment]
            if stacked:
                return await asyncio.to_thread(verify_stacked, ctx.claim, ret)
            return await asyncio.to_thread(verify, kind, ctx.claim, ret)

    Verifier.family = family
    Verifier.__name__ = f"Verifier_{kind}"


_register(
    "bert", "BERT + stacker (best)", family="neural", is_default=True, stacked=True,
    desc="Fine-tuned bert-base reads the claim with each evidence sentence and with all of them; a logistic-regression stacker combines the scores.",
)
_register(
    "bert_concat", "BERT, evidence concatenated", family="neural",
    desc="The same fine-tuned BERT reading the claim and all top sentences in one pass (temperature-calibrated). Less accurate.",
)
_register("lstm", "BiLSTM (GloVe)", family="neural", desc="Recurrent baseline: claim and evidence encoded separately by a BiLSTM over GloVe vectors.")
_register("gru", "BiGRU (GloVe)", family="neural", desc="Same as the BiLSTM baseline with GRU cells.")
_register(
    "claim_only", "Claim-only TF-IDF (baseline)", family="classical",
    desc="Logistic regression on the claim text alone. Never looks at the evidence; shows how much the evidence adds.",
)
