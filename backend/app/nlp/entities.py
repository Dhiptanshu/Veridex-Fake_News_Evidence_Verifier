"""Named entities, noun chunks and subject-verb-object triples from spaCy's statistical pipeline."""
from app.nlp import resources
from app.schemas.stages import Entity, NerOut, Triple

_SUBJ = {"nsubj", "nsubjpass"}
_OBJ = {"dobj", "attr", "oprd", "dative"}


def _span_text(token) -> str:
    """The head noun with its left-side modifiers ('an American television spy thriller'), no trailing clauses."""
    return " ".join(t.text for t in token.doc[token.left_edge.i : token.i + 1] if not t.is_punct) or token.text


def extract(text: str) -> NerOut:
    doc = resources.spacy_nlp()(text)
    entities = [Entity(text=e.text, label=e.label_, start=e.start_char, end=e.end_char) for e in doc.ents]
    chunks = [c.text for c in doc.noun_chunks]
    triples: list[Triple] = []
    for tok in doc:
        if tok.dep_ not in _SUBJ or tok.head.pos_ not in {"VERB", "AUX"}:
            continue
        verb = tok.head
        objs = [c for c in verb.children if c.dep_ in _OBJ]
        for prep in (c for c in verb.children if c.dep_ == "prep"):
            objs += [c for c in prep.children if c.dep_ == "pobj"]
        for obj in objs:
            pred = verb.lemma_ if verb.pos_ == "VERB" else verb.text
            triples.append(Triple(subject=_span_text(tok), predicate=pred, object=_span_text(obj)))
    return NerOut(entities=entities, noun_chunks=chunks, triples=triples)
