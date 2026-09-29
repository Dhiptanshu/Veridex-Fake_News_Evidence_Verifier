"""Phase-1 stages. They exercise the full contract end-to-end so the UI can be built early.

Stages flagged `placeholder = True` return no real analysis: they emit clearly-labelled stand-ins
(never made-up facts or evidence) and are replaced by real implementations in later phases.
"""
import asyncio
import math
import re
from collections import Counter

from app.core.config import settings
from app.schemas.stages import (
    Entity, Evidence, EvidenceSentence, EvidenceVerdict, ExplanationOut, Keyword, KeywordsOut,
    NerOut, PreprocessOut, RetrievalOut, VerificationOut,
)
from app.stages.base import Stage, StageContext, register

STOPWORDS = frozenset(
    "a an the and or but if of to in on at by for with from as is are was were be been being it its this that "
    "these those he she they we you i his her their our your not no do does did has have had will would can could".split()
)
_TOKEN = re.compile(r"[A-Za-z0-9]+(?:['\-][A-Za-z0-9]+)*")
_SENT = re.compile(r"(?<=[.!?])\s+")


async def _pause() -> None:
    await asyncio.sleep(settings.placeholder_delay_s)


def _entropy(scores: list[float]) -> float:
    total = sum(scores)
    if total <= 0:
        return 0.0
    return -sum((s / total) * math.log2(s / total) for s in scores if s > 0)


@register
class RegexPreprocess(Stage):
    slot, name, default = "preprocess", "regex", True
    label = "Regex tokenizer"
    description = "Sentence split, regex tokenization, lowercasing and stop-word removal."

    async def run(self, ctx: StageContext) -> PreprocessOut:
        text = ctx.claim.strip()
        tokens = _TOKEN.findall(text)
        normalized = [t.lower() for t in tokens if t.lower() not in STOPWORDS]
        return PreprocessOut(
            original=text, sentences=[s for s in _SENT.split(text) if s], tokens=tokens, normalized=normalized
        )


@register
class CapitalizedNer(Stage):
    slot, name, default = "ner", "capitalized", True
    label = "Capitalised spans"
    description = "Heuristic: runs of capitalised words that are not stop-words."
    placeholder = True

    async def run(self, ctx: StageContext) -> NerOut:
        await _pause()
        entities = []
        for m in re.finditer(r"\b[A-Z][\w\-]*(?:\s+[A-Z][\w\-]*)*", ctx.claim):
            if m.group().lower() in STOPWORDS:
                continue
            entities.append(Entity(text=m.group(), label="SPAN", start=m.start(), end=m.end()))
        return NerOut(entities=entities)


@register
class FrequencyKeywords(Stage):
    slot, name, default = "keywords", "frequency", True
    label = "Term frequency"
    description = "Most frequent non-stop-word terms; entities are prepended to form the retrieval query."
    placeholder = True

    async def run(self, ctx: StageContext) -> KeywordsOut:
        await _pause()
        pre: PreprocessOut = ctx.results["preprocess"]  # type: ignore[assignment]
        ner: NerOut = ctx.results["ner"]  # type: ignore[assignment]
        counts = Counter(pre.normalized)
        total = sum(counts.values()) or 1
        keywords = [Keyword(term=t, score=round(c / total, 4)) for t, c in counts.most_common(8)]
        query = " ".join([e.text for e in ner.entities] + [k.term for k in keywords])
        return KeywordsOut(keywords=keywords, query=query)


@register
class PlaceholderRetriever(Stage):
    slot, name, default = "retrieval", "placeholder", True
    label = "Placeholder retriever"
    description = "No index connected yet. Returns a single labelled stand-in item."
    family = "placeholder"
    placeholder = True

    async def run(self, ctx: StageContext) -> RetrievalOut:
        await _pause()
        item = Evidence(
            id="placeholder-0", title="No evidence index connected", source="placeholder", score=0.0,
            sentences=[EvidenceSentence(
                text="Real evidence appears here once the retriever from Phases 2-4 is connected.", score=0.0
            )],
        )
        return RetrievalOut(evidence=[item], score_entropy=_entropy([1.0]))


@register
class PlaceholderVerifier(Stage):
    slot, name, default = "verification", "placeholder", True
    label = "Placeholder verifier"
    description = "No model loaded yet. Reports an uninformative uniform distribution."
    family = "placeholder"
    placeholder = True

    async def run(self, ctx: StageContext) -> VerificationOut:
        await _pause()
        ret: RetrievalOut = ctx.results["retrieval"]  # type: ignore[assignment]
        third = round(1 / 3, 4)
        return VerificationOut(
            label="not_enough_info",
            confidence=third,
            probabilities={"supported": third, "refuted": third, "not_enough_info": third},
            per_evidence=[
                EvidenceVerdict(evidence_id=e.id, supported=third, refuted=third, neutral=third)
                for e in ret.evidence
            ],
        )


@register
class PlaceholderExplainer(Stage):
    slot, name, default = "explanation", "placeholder", True
    label = "Placeholder explainer"
    description = "No generator loaded yet."
    family = "placeholder"
    placeholder = True

    async def run(self, ctx: StageContext) -> ExplanationOut:
        await _pause()
        return ExplanationOut(
            summary="Placeholder: no evidence summary is generated yet.",
            rationale="The pipeline ran end-to-end with placeholder stages, so no verdict is being claimed.",
            cited_evidence_ids=[],
        )
