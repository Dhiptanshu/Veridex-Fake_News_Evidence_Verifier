import asyncio
import re

from app.explain import attribution, differences, rationale, select, summarize
from app.explain.clean import tidy
from app.schemas.stages import Differences, ExplanationOut, RetrievalOut, VerificationOut
from app.stages.base import Stage, StageContext, register
from app.verification import models


def explain(claim: str, ver: VerificationOut, ret: RetrievalOut, summarizer: str) -> ExplanationOut:
    citations = select.select_citations(ver, ret)
    first = citations[0] if citations else None
    retrieved = [s.text for s, _ in sorted(((s, e) for e in ret.evidence for s in e.sentences), key=lambda t: -t[0].score)]

    diff = None
    if first and ver.label == "refuted":  # a wording difference only explains a refutation; for the others it is noise
        claim_only, evidence_only = differences.differing_terms(claim, first.text, first.title)
        diff = Differences(cite=first.n, claim_only=claim_only, evidence_only=evidence_only)
    missing = differences.missing_from(claim, retrieved, [e.title for e in ret.evidence])

    attrib = None
    if first and ver.per_sentence:  # needs the sentence-level BERT; other verifiers get no word attribution
        attrib = attribution.occlude(models.load("bert"), claim, first, ver.label)

    unverified = [n for n in re.findall(r"\d[\d,.]*\d|\d", claim) if n not in " ".join(retrieved)]
    text = rationale.build(ver.label, ver.confidence, citations, diff, missing, unverified)
    candidates = [(t, tidy(x)) for t, x in select.summary_candidates(ver, ret)]
    if summarizer == "bart":
        body = summarize.dedupe([x for _, x in candidates])
        summary = summarize.get_bart().summarize([" ".join(body)])[0] if body else ""
        method = "DistilBART (abstractive)"
    else:
        title_of = {x: t for t, x in candidates}
        picked = summarize.mmr_summary(claim, [x for _, x in candidates])
        summary = " ".join(f"{title_of[x]}: {x}" for x in picked)  # name the source page of every sentence
        method = "MMR (extractive)"
    ids = list(dict.fromkeys(c.evidence_id for c in citations))
    return ExplanationOut(
        summary=summary, summary_method=method, rationale=text, cited_evidence_ids=ids,
        citations=citations, differences=diff, attribution=attrib,
    )


def _register(key: str, title: str, desc: str, summarizer: str, family: str, is_default: bool = False) -> None:
    @register
    class Explainer(Stage):
        slot = "explanation"
        name = key
        label = title
        description = desc
        default = is_default

        async def run(self, ctx: StageContext) -> ExplanationOut:
            ver: VerificationOut = ctx.results["verification"]  # type: ignore[assignment]
            ret: RetrievalOut = ctx.results["retrieval"]  # type: ignore[assignment]
            return await asyncio.to_thread(explain, ctx.claim, ver, ret, summarizer)

    Explainer.family = family
    Explainer.__name__ = f"Explainer_{key}"


_register(
    "grounded", "Grounded rationale + extractive summary", summarizer="mmr", family="classical", is_default=True,
    desc="Cites the decisive sentences, lists differing terms, shows word importance; summary picks real sentences (MMR).",
)
_register(
    "bart", "Grounded rationale + DistilBART summary", summarizer="bart", family="neural",
    desc="Same rationale, but the evidence summary is written by DistilBART (abstractive, may paraphrase).",
)
