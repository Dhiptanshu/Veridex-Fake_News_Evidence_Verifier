"""Typed output of each pipeline slot. These are the contract between backend stages and the UI."""
from typing import Literal

from pydantic import BaseModel, Field

Label = Literal["supported", "refuted", "not_enough_info"]


class PreprocessOut(BaseModel):
    original: str
    sentences: list[str]
    tokens: list[str]
    normalized: list[str]  # lowercased, stop-words removed


class Entity(BaseModel):
    text: str
    label: str
    start: int
    end: int


class NerOut(BaseModel):
    entities: list[Entity]


class Keyword(BaseModel):
    term: str
    score: float


class KeywordsOut(BaseModel):
    keywords: list[Keyword]
    query: str  # final retrieval query built from entities + keywords


class EvidenceSentence(BaseModel):
    text: str
    score: float = Field(ge=0, le=1)


class Evidence(BaseModel):
    id: str
    title: str
    source: str
    url: str | None = None
    score: float
    sentences: list[EvidenceSentence]


class RetrievalOut(BaseModel):
    evidence: list[Evidence]
    score_entropy: float | None = None  # entropy of the normalised retrieval score distribution


class EvidenceVerdict(BaseModel):
    evidence_id: str
    supported: float
    refuted: float
    neutral: float


class VerificationOut(BaseModel):
    label: Label
    confidence: float = Field(ge=0, le=1)
    probabilities: dict[Label, float]
    per_evidence: list[EvidenceVerdict]


class ExplanationOut(BaseModel):
    summary: str
    rationale: str
    cited_evidence_ids: list[str]
