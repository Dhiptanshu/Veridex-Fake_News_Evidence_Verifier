import asyncio
import re

from app.evidence import passages as psg
from app.explain import attribution, differences, rationale, select, summarize
from app.explain.clean import tidy
from app.schemas.stages import Citation, Differences, ExplanationOut, RetrievalOut, VerificationOut
from app.stages.base import Stage, StageContext, register
from app.verification import models


NUANCE_TEXT = {'partly_true': 'Partly true: the claim gets some facts right but is wrong in a key detail.', 'misleading': 'Misleading: technically close to facts, but the framing leaves a false impression.', 'outdated': 'Outdated: this may have been true earlier but is not true now.', 'satire': 'This looks like satire rather than a factual claim.', 'opinion': 'This is an opinion rather than a checkable fact.', 'unverifiable_future': 'This concerns the future, so it cannot be verified yet.', 'needs_context': 'True or false depends on missing context.'}


def _explain_llm(claim: str, ver: VerificationOut, ret: RetrievalOut, summarizer: str) -> ExplanationOut:
    """The judge already wrote the reasoning; keep it verbatim (it cites passages as [n]) and add structure around it."""
    ps = {p.n: p for p in psg.flatten(ret)}
    wanted = list(dict.fromkeys([*ver.cited, *(int(n) for n in re.findall(r"\[(\d+)\]", ver.reasoning or ""))]))
    citations = [
        Citation(n=n, evidence_id=ps[n].evidence.id, title=ps[n].evidence.title, text=ps[n].sentence.text,
                 role="decisive" if n in ver.cited else "context",
                 supported=None, refuted=None, neutral=None)
        for n in wanted if n in ps
    ]
    parts = [ver.reasoning or ""]
    if ver.nuance in NUANCE_TEXT:
        parts.append(NUANCE_TEXT[ver.nuance])
    if ver.missing:
        parts.append(f"What would settle it: {ver.missing}")
    summary, method = "", "none"
    candidates = [(t, tidy(x)) for t, x in select.summary_candidates(ver, ret)]
    if candidates:
        title_of = {x: t for t, x in candidates}
        picked = summarize.mmr_summary(claim, [x for _, x in candidates])
        summary = " ".join(f"{title_of[x]}: {x}" for x in picked)
        method = "MMR (extractive)"
    return ExplanationOut(
        summary=summary, summary_method=method, rationale=" ".join(p for p in parts if p),
        cited_evidence_ids=list(dict.fromkeys(c.evidence_id for c in citations)), citations=citations,
    )


def explain(claim: str, ver: VerificationOut, ret: RetrievalOut, summarizer: str) -> ExplanationOut:
    if ver.engine == "llm":
        return _explain_llm(claim, ver, ret, summarizer)
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
