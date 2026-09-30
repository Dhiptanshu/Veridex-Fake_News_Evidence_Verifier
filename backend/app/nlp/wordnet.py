"""WordNet-based query expansion (lexical semantics: synonyms of content words)."""
from nltk.corpus import wordnet as wn

from app.nlp import resources


def synonyms(lemma: str, penn_tag: str, limit: int = 3) -> list[str]:
    """Single-word synonyms from the first (most frequent) senses of `lemma`, excluding itself."""
    pos = resources.wordnet_pos(penn_tag)
    out: list[str] = []
    for synset in wn.synsets(lemma, pos=pos)[:2]:
        for name in synset.lemma_names():
            if "_" in name or name.lower() == lemma.lower() or name.lower() in out:
                continue
            out.append(name.lower())
            if len(out) >= limit:
                return out
    return out


def expand(lemmas: list[str], tags: list[str], per_word: int = 2) -> list[str]:
    """Return extra terms to append to a query. Only nouns/verbs/adjectives are expanded."""
    stop = resources.stopwords()
    extra: list[str] = []
    for lem, tag in zip(lemmas, tags):
        if lem in stop or tag[:1] not in {"N", "V", "J"} or tag.startswith("NNP"):
            continue  # proper nouns must match literally
        extra += synonyms(lem, tag, per_word)
    return extra
