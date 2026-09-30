"""Typed output of each pipeline slot. These are the contract between backend stages and the UI."""
from typing import Literal

from pydantic import BaseModel, Field

Label = Literal["supported", "refuted", "not_enough_info"]


class TaggedToken(BaseModel):
    token: str
    tag: str  # Penn Treebank tag, e.g. NNP, VBD


class Sentiment(BaseModel):
    polarity: float  # -1 (negative) .. 1 (positive)
    subjectivity: float  # 0 (objective) .. 1 (subjective); a rough "sensationalism" signal


class PreprocessOut(BaseModel):
    original: str
    sentences: list[str]
    tokens: list[str]
    pos: list[TaggedToken] = Field(default_factory=list)
    lemmas: list[str] = Field(default_factory=list)  # lowercased lemma per token, aligned with `tokens`
    normalized: list[str]  # lowercased lemmas, stop-words and punctuation removed
    sentiment: Sentiment | None = None


class Entity(BaseModel):
    text: str
    label: str
    start: int
    end: int


class Triple(BaseModel):
    subject: str
    predicate: str
    object: str


class NerOut(BaseModel):
    entities: list[Entity]
    noun_chunks: list[str] = Field(default_factory=list)  # chunking
    triples: list[Triple] = Field(default_factory=list)  # subject-verb-object from the dependency parse


class Keyword(BaseModel):
    term: str
    score: float
    kind: str = "term"  # term | phrase (PMI collocation)


class KeywordsOut(BaseModel):
    keywords: list[Keyword]
    query: str  # final retrieval query built from entities + keywords


class EvidenceSentence(BaseModel):
    text: str
    score: float = Field(ge=0, le=1)


class Topic(BaseModel):
    id: int
    label: str  # top words joined, e.g. "film · american · directed"
    words: list[str]


class Evidence(BaseModel):
    id: str
    title: str
    source: str
    url: str | None = None
    score: float
    sentences: list[EvidenceSentence]
    topic: Topic | None = None  # dominant LDA topic of the page


class MapPoint(BaseModel):
    x: float
    y: float
    kind: str  # claim | evidence
    label: str
    score: float | None = None


class Projection(BaseModel):
    """2-D PCA of the claim and evidence sentence embeddings, over a sample of corpus sentences as backdrop."""

    points: list[MapPoint]
    background: list[tuple[float, float]]
    explained_variance: float


class RetrievalOut(BaseModel):
    evidence: list[Evidence]
    query: str | None = None  # the text actually searched (after any expansion)
    score_entropy: float | None = None  # entropy of the normalised retrieval score distribution
    projection: Projection | None = None


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
