import asyncio
import re

from app.nlp import entities, resources
from app.schemas.stages import Entity, NerOut
from app.stages.base import Stage, StageContext, register


@register
class SpacyNer(Stage):
    slot, name, default = "ner", "spacy", True
    label = "spaCy (statistical)"
    description = "Named entities, noun chunks and subject-verb-object triples from spaCy's CNN pipeline."

    async def run(self, ctx: StageContext) -> NerOut:
        return await asyncio.to_thread(entities.extract, ctx.claim)


@register
class CapitalizedNer(Stage):
    slot, name = "ner", "capitalized"
    label = "Capitalised spans (baseline)"
    description = "Heuristic: runs of capitalised words that are not stop-words. No labels, no parse."

    async def run(self, ctx: StageContext) -> NerOut:
        stop = resources.stopwords()
        found = []
        for m in re.finditer(r"\b[A-Z][\w\-]*(?:\s+[A-Z][\w\-]*)*", ctx.claim):
            if m.group().lower() in stop:
                continue
            found.append(Entity(text=m.group(), label="SPAN", start=m.start(), end=m.end()))
        return NerOut(entities=found)
