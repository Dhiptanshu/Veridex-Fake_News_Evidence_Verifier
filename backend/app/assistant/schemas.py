from typing import Literal

from pydantic import BaseModel, Field

Label = Literal["supported", "refuted", "not_enough_info"]


class Source(BaseModel):
    """Something the assistant may cite as [n]: an evidence passage from the current result, or a result of its own search."""

    n: int
    title: str = Field(max_length=300)
    text: str = Field(default="", max_length=1500)
    url: str | None = None
    source: str = Field(default="", max_length=120)
    kind: str = "evidence"  # evidence | news | fact-check | wikipedia | article
    date: str | None = None
    tier: str | None = None


class Turn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=6000)


class ChatContext(BaseModel):
    claim: str = Field(max_length=2000)
    label: Label
    confidence: float = Field(ge=0, le=1)
    probabilities: dict[Label, float] = {}
    reasoning: str = Field(default="", max_length=4000)
    engine: str = "llm"
    notes: list[str] = []


class ChatRequest(BaseModel):
    """The server keeps no conversation state: the client sends the history, the current result and every source seen so far."""

    messages: list[Turn] = Field(min_length=1, max_length=40)
    context: ChatContext | None = None
    sources: list[Source] = Field(default_factory=list, max_length=60)
    model: str | None = Field(default=None, max_length=80)


class ChatStatus(BaseModel):
    configured: bool
    model: str
    tools: list[str]
