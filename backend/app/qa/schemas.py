from typing import Literal

from pydantic import BaseModel, Field

Label = Literal["supported", "refuted", "not_enough_info"]


class Passage(BaseModel):
    n: int  # the [n] a cited answer refers to
    title: str = Field(max_length=300)
    text: str = Field(max_length=800)
    url: str | None = None


class AskRequest(BaseModel):
    """Everything the answer may use. The UI sends back what it already shows, so the server stays stateless."""

    question: str = Field(min_length=3, max_length=300)
    claim: str = Field(max_length=2000)
    label: Label
    confidence: float = Field(ge=0, le=1)
    probabilities: dict[Label, float]
    rationale: str = Field(max_length=4000)
    passages: list[Passage] = Field(max_length=12)
    mode: Literal["auto", "local", "llm"] = "auto"


class AskResponse(BaseModel):
    answer: str
    method: str  # rationale | sources | confidence | extractive QA | llm
    cited: list[int] = []
    note: str | None = None


class AskStatus(BaseModel):
    llm_configured: bool
    llm_model: str
    local_qa_ready: bool
