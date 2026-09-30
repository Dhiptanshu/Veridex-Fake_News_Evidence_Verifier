"""Lazy, cached access to NLTK data and the spaCy model, so importing the app stays fast."""
from functools import lru_cache
from pathlib import Path

import nltk

ROOT = Path(__file__).resolve().parents[3]
NLTK_DIR = ROOT / "data" / "nltk_data"
INDEX_DIR = ROOT / "data" / "indexes"
SPACY_MODEL = "en_core_web_sm"

nltk.data.path.insert(0, str(NLTK_DIR))

_SETUP_HINT = "Run `python ml/setup_nlp.py` to download the NLP resources."


@lru_cache(maxsize=1)
def stopwords() -> frozenset[str]:
    try:
        from nltk.corpus import stopwords as sw

        # "won"/"ma" are contraction fragments ("won't" -> wo + n't) in this list, but as whole tokens
        # they are real content words in claims ("X won two awards"), so keep them.
        return frozenset(sw.words("english")) - {"won", "ma"}
    except LookupError as exc:
        raise RuntimeError(f"NLTK stopwords missing. {_SETUP_HINT}") from exc


@lru_cache(maxsize=1)
def lemmatizer():
    from nltk.stem import WordNetLemmatizer

    return WordNetLemmatizer()


@lru_cache(maxsize=1)
def spacy_nlp():
    import spacy

    try:
        return spacy.load(SPACY_MODEL)
    except OSError as exc:
        raise RuntimeError(f"spaCy model {SPACY_MODEL!r} missing. {_SETUP_HINT}") from exc


def wordnet_pos(penn_tag: str) -> str:
    """Map a Penn Treebank tag to a WordNet POS letter (default noun)."""
    return {"J": "a", "V": "v", "R": "r"}.get(penn_tag[:1], "n")
