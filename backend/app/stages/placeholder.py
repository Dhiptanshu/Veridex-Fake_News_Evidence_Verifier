"""Stages not built yet. They emit clearly-labelled stand-ins, never made-up verdicts or evidence.

Verification arrives in Phase 5 and explanation in Phase 6; until then the pipeline reports an uninformative
uniform distribution and says so.
"""
import asyncio

from app.core.config import settings
from app.schemas.stages import EvidenceVerdict, ExplanationOut, RetrievalOut, VerificationOut
from app.stages.base import Stage, StageContext, register


async def _pause() -> None:
    await asyncio.sleep(settings.placeholder_delay_s)


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
                EvidenceVerdict(evidence_id=e.id, supported=third, refuted=third, neutral=third) for e in ret.evidence
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
            rationale="Retrieval is real; verification and explanation are not built yet, so no verdict is being claimed.",
            cited_evidence_ids=[],
        )
