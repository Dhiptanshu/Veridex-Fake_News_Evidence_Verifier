import asyncio

from app.retrieval.search import search
from app.retrieval.tfidf import get_index
from app.schemas.stages import NerOut, RetrievalOut
from app.stages.base import Stage, StageContext, register


def _entities(ctx: StageContext) -> list[str]:
    ner: NerOut = ctx.results["ner"]  # type: ignore[assignment]
    return [e.text for e in ner.entities]


@register
class TfidfRetriever(Stage):
    slot, name, default = "retrieval", "tfidf", True
    label = "TF-IDF + title match"
    description = "Cosine TF-IDF over pages, boosted when a page title is mentioned in the claim; sentences re-ranked."
    family = "classical"

    async def run(self, ctx: StageContext) -> RetrievalOut:
        return await asyncio.to_thread(search, get_index(), ctx.claim, _entities(ctx))


@register
class PlainTfidfRetriever(Stage):
    slot, name = "retrieval", "tfidf_plain"
    label = "TF-IDF only (baseline)"
    description = "Cosine TF-IDF over pages with no entity/title awareness."
    family = "classical"

    async def run(self, ctx: StageContext) -> RetrievalOut:
        return await asyncio.to_thread(search, get_index(), ctx.claim, [], use_titles=False)
