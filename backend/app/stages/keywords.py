import asyncio

from app.nlp import keywords as kw
from app.nlp import pmi
from app.retrieval.tfidf import get_index
from app.schemas.stages import KeywordsOut, NerOut, PreprocessOut
from app.stages.base import Stage, StageContext, register


def _inputs(ctx: StageContext) -> tuple[PreprocessOut, list[str]]:
    pre: PreprocessOut = ctx.results["preprocess"]  # type: ignore[assignment]
    ner: NerOut = ctx.results["ner"]  # type: ignore[assignment]
    return pre, [e.text for e in ner.entities]


@register
class TfidfKeywords(Stage):
    slot, name, default = "keywords", "tfidf", True
    label = "TF-IDF + POS filter"
    description = "Claim terms and bigrams weighted by corpus TF-IDF, kept only if built from content words."

    async def run(self, ctx: StageContext) -> KeywordsOut:
        pre, ents = _inputs(ctx)
        words = await asyncio.to_thread(kw.tfidf_keywords, get_index(), pre)
        return KeywordsOut(keywords=words, query=kw.build_query(ents, words))


@register
class PmiKeywords(Stage):
    slot, name = "keywords", "tfidf_pmi"
    label = "TF-IDF + PMI phrases"
    description = "TF-IDF terms plus collocations whose pointwise mutual information is high in the corpus."

    async def run(self, ctx: StageContext) -> KeywordsOut:
        pre, ents = _inputs(ctx)

        def work():
            phrases = kw.pmi_phrases(pmi.get_table(), pre.original)
            terms = kw.tfidf_keywords(get_index(), pre)
            seen = {p.term for p in phrases}
            return phrases + [t for t in terms if t.term not in seen]

        words = await asyncio.to_thread(work)
        return KeywordsOut(keywords=words, query=kw.build_query(ents, words))


@register
class FrequencyKeywords(Stage):
    slot, name = "keywords", "frequency"
    label = "Term frequency (baseline)"
    description = "Most frequent non-stop-word terms in the claim; ignores how informative they are."

    async def run(self, ctx: StageContext) -> KeywordsOut:
        pre, ents = _inputs(ctx)
        words = kw.frequency_keywords(pre)
        return KeywordsOut(keywords=words, query=kw.build_query(ents, words))
