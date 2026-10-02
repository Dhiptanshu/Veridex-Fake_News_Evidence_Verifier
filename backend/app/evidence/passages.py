"""The numbered evidence passages shown in the UI. The judge, the explanation and the assistant all cite by these numbers, so
one function defines the numbering: evidence in rank order, sentences in order, capped."""
from dataclasses import dataclass

from app.schemas.stages import Evidence, EvidenceSentence, RetrievalOut

MAX_PASSAGES = 12


@dataclass
class Passage:
    n: int
    evidence: Evidence
    sentence: EvidenceSentence

    def tag(self) -> str:
        """One line for a prompt: source, kind, tier, date and the text itself."""
        e = self.evidence
        meta = [e.kind, e.tier or "unrated" if e.kind != "wikipedia" else None, e.published, e.source]
        extra = f" | fact-checker's rating: {e.rating}" if e.rating else ""
        return f"[{self.n}] ({'; '.join(m for m in meta if m)}{extra}) {e.title}: {self.sentence.text}"


def flatten(ret: RetrievalOut, cap: int = MAX_PASSAGES) -> list[Passage]:
    out: list[Passage] = []
    for e in ret.evidence:
        for s in e.sentences:
            out.append(Passage(n=len(out) + 1, evidence=e, sentence=s))
    return out[:cap]
