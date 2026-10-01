"""Retrieval implementations: classical TF-IDF, word-vector hybrids and dense transformer search.

Fusion weights come from the validation grid in docs/results/retrieval_semantic.json (alpha = weight on TF-IDF).
"""
import asyncio

from app.retrieval import hybrid, live
from app.retrieval.hybrid import TFIDF
from app.retrieval.search import search
from app.retrieval.tfidf import get_index
from app.schemas.stages import NerOut, RetrievalOut
from app.stages.base import Stage, StageContext, register


def _entities(ctx: StageContext) -> list[str]:
    ner: NerOut = ctx.results["ner"]  # type: ignore[assignment]
    return [e.text for e in ner.entities]


@register
class TfidfRetriever(Stage):
    slot, name = "retrieval", "tfidf"
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


def _semantic(
    *, key: str, title: str, desc: str, weights: dict[str, float], dense: str | None = None, project: str | None = None,
    family: str = "neural", is_default: bool = False, title_bonus: float = 0.0,
) -> type[Stage]:
    """Register a retriever that fuses the given scorers over TF-IDF(+title) candidate pages."""

    @register
    class Semantic(Stage):
        slot = "retrieval"
        name = key
        label = title
        description = desc
        default = is_default

        async def run(self, ctx: StageContext) -> RetrievalOut:
            return await asyncio.to_thread(
                hybrid.hybrid_search, hybrid.get_resources(), ctx.claim, _entities(ctx),
                weights=weights, dense_for_candidates=dense, project_with=project, title_bonus=title_bonus,
            )

    Semantic.family = family
    Semantic.__name__ = f"Semantic_{key}"
    return Semantic


_semantic(
    key="dense_bge", title="BGE-small dense search", is_default=True, weights={"bge_small": 1.0}, dense="bge_small", project="bge_small",
    title_bonus=0.02,
    desc="BAAI/bge-small-en-v1.5 embeddings (Kaggle GPU) plus a small bonus for pages named in the claim; best in our evaluation.",
)
_semantic(
    key="dense_minilm", title="MiniLM dense search", weights={"minilm": 1.0}, dense="minilm", project="minilm",
    desc="all-MiniLM-L6-v2 sentence embeddings; smaller and faster than BGE, slightly less accurate.",
)
_semantic(
    key="hybrid_minilm", title="TF-IDF + MiniLM hybrid", weights={TFIDF: 0.2, "minilm": 0.8}, dense="minilm", project="minilm",
    desc="Lexical and semantic scores fused (20% TF-IDF, 80% MiniLM), the weights tuned on the validation split.",
    family="hybrid",
)
_semantic(
    key="wordvec_w2v", title="TF-IDF + Word2Vec hybrid", weights={TFIDF: 0.4, "w2v": 0.6}, family="hybrid",
    desc="Word2Vec trained on the corpus: IDF-weighted average word vectors fused with TF-IDF (40/60).",
)
_semantic(
    key="wordvec_glove", title="TF-IDF + GloVe hybrid", weights={TFIDF: 0.4, "glove": 0.6}, family="hybrid",
    desc="Pretrained GloVe (Wikipedia + Gigaword, 100-d): IDF-weighted average fused with TF-IDF (40/60).",
)


@register
class LiveWikipedia(Stage):
    slot, name = "retrieval", "live_wikipedia"
    label = "Live Wikipedia search"
    description = (
        "Searches live Wikipedia for the claim (sends the claim and its entity names to en.wikipedia.org), ranks the page "
        "introductions with BGE. Works for claims outside the offline FEVER subset; needs internet."
    )
    family = "hybrid"

    async def run(self, ctx: StageContext) -> RetrievalOut:
        return await asyncio.to_thread(live.live_search, hybrid.get_resources(), ctx.claim, _entities(ctx))
