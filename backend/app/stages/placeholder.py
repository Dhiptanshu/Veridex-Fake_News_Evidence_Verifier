"""Stages not built yet. They emit clearly-labelled stand-ins, never made-up verdicts or evidence.

The explanation generator arrives in Phase 6; until then the pipeline says so.
"""
import asyncio

from app.core.config import settings
from app.schemas.stages import ExplanationOut
from app.stages.base import Stage, StageContext, register


async def _pause() -> None:
    await asyncio.sleep(settings.placeholder_delay_s)


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
            rationale="The verdict above comes from the verification model; a written explanation is not built yet.",
            cited_evidence_ids=[],
        )
