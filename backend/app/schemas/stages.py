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
    kind: str = "wikipedia"  # news | fact-check | background (live Wikipedia) | wikipedia (offline FEVER subset)
    published: str | None = None  # ISO date for news and fact-checks
    tier: str | None = None  # source credibility tier (evidence/credibility.py); None for offline Wikipedia
    rating: str | None = None  # a fact-checker's own verdict text, when kind == "fact-check"


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
    queries: list[str] = Field(default_factory=list)  # live search queries actually sent
    timings_ms: dict[str, float] = Field(default_factory=dict)  # where retrieval time went (plan, search, fetch, rank)
    notes: list[str] = Field(default_factory=list)  # warnings shown to the user (a provider failed, quota, no results...)


class EvidenceVerdict(BaseModel):
    evidence_id: str
    supported: float
    refuted: float
    neutral: float


class SentenceVerdict(BaseModel):
    """The verifier's opinion of the claim given ONE evidence sentence on its own."""

    evidence_id: str
    title: str
    text: str
    retrieval_score: float
    supported: float
    refuted: float
    neutral: float


class VerificationOut(BaseModel):
    label: Label
    confidence: float = Field(ge=0, le=1)
    probabilities: dict[Label, float]
    per_evidence: list[EvidenceVerdict]
    per_sentence: list[SentenceVerdict] = Field(default_factory=list)  # empty for verifiers that do not score sentences
    engine: str = "bert"  # who produced the verdict: bert | llm
    reasoning: str | None = None  # the judge's own explanation, citing passages as [n]
    nuance: str | None = None  # partly_true | misleading | outdated | satire | opinion | unverifiable_future | needs_context
    missing: str | None = None  # what evidence would settle a not-enough-info verdict
    cited: list[int] = Field(default_factory=list)  # passage numbers the verdict rests on
    notes: list[str] = Field(default_factory=list)  # warnings (fell back to BERT, no usable citation...)


class Citation(BaseModel):
    n: int  # the [n] marker used in the rationale text
    evidence_id: str
    title: str
    text: str
    role: Literal["decisive", "closest", "context"]  # decisive: drove the verdict; closest: nearest evidence when nothing decides
    supported: float | None = None
    refuted: float | None = None
    neutral: float | None = None


class Differences(BaseModel):
    """Informative words that differ between the claim and the first cited sentence (a plain set difference)."""

    cite: int
    claim_only: list[str]
    evidence_only: list[str]


class WordScore(BaseModel):
    word: str
    score: float = Field(ge=0, le=1)  # relative importance for the verdict, 1 = the most important word


class Attribution(BaseModel):
    """Which words mattered, by occlusion: delete one word at a time and see how much the verdict probability drops."""

    cite: int
    target: Label
    claim: list[WordScore]
    evidence: list[WordScore]


class ExplanationOut(BaseModel):
    summary: str
    summary_method: str = "none"
    rationale: str  # plain text with [n] citation markers
    cited_evidence_ids: list[str]
    citations: list[Citation] = Field(default_factory=list)
    differences: Differences | None = None
    attribution: Attribution | None = None
