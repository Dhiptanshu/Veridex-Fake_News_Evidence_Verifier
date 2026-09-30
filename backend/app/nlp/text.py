"""Classical text analysis with NLTK (tokenize, POS-tag, lemmatize) and TextBlob (sentiment)."""
import re

from nltk import pos_tag, sent_tokenize, word_tokenize

from app.nlp import resources
from app.schemas.stages import PreprocessOut, Sentiment, TaggedToken

_WORD = re.compile(r"[A-Za-z0-9]")

# Penn tags that carry content: nouns, verbs, adjectives, adverbs, numbers.
CONTENT_TAG_PREFIXES = ("NN", "VB", "JJ", "RB", "CD")


def is_content_tag(tag: str) -> bool:
    return tag.startswith(CONTENT_TAG_PREFIXES)


def analyze(text: str) -> PreprocessOut:
    text = text.strip()
    sentences = sent_tokenize(text) or [text]
    tokens = [t for s in sentences for t in word_tokenize(s)]
    tagged = pos_tag(tokens)
    lem = resources.lemmatizer()
    stop = resources.stopwords()
    lemmas = [lem.lemmatize(tok.lower(), resources.wordnet_pos(tag)) for tok, tag in tagged]
    normalized = [lm for lm, tok in zip(lemmas, tokens) if _WORD.search(lm) and tok.lower() not in stop]
    return PreprocessOut(
        original=text,
        sentences=sentences,
        tokens=tokens,
        pos=[TaggedToken(token=t, tag=g) for t, g in tagged],
        lemmas=lemmas,
        normalized=normalized,
        sentiment=sentiment(text),
    )


def sentiment(text: str) -> Sentiment:
    from textblob import TextBlob

    s = TextBlob(text).sentiment
    return Sentiment(polarity=round(s.polarity, 3), subjectivity=round(s.subjectivity, 3))

