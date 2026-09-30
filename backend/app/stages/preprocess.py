import asyncio
import re

from app.nlp import resources, text
from app.schemas.stages import PreprocessOut
from app.stages.base import Stage, StageContext, register

_TOKEN = re.compile(r"[A-Za-z0-9]+(?:['\-][A-Za-z0-9]+)*")
_SENT = re.compile(r"(?<=[.!?])\s+")


@register
class NltkPreprocess(Stage):
    slot, name, default = "preprocess", "nltk", True
    label = "NLTK + TextBlob"
    description = "Sentence/word tokenization, POS tags, WordNet lemmas, stop-word removal, TextBlob sentiment."

    async def run(self, ctx: StageContext) -> PreprocessOut:
        return await asyncio.to_thread(text.analyze, ctx.claim)


@register
class RegexPreprocess(Stage):
    slot, name = "preprocess", "regex"
    label = "Regex tokenizer (baseline)"
    description = "Regex tokens and stop-word removal only: no POS tags, lemmas or sentiment."

    async def run(self, ctx: StageContext) -> PreprocessOut:
        raw = ctx.claim.strip()
        tokens = _TOKEN.findall(raw)
        stop = resources.stopwords()
        norm = [t.lower() for t in tokens if t.lower() not in stop]
        return PreprocessOut(original=raw, sentences=[s for s in _SENT.split(raw) if s], tokens=tokens, normalized=norm)
