from typing import Any, Literal

from pydantic import BaseModel, Field

SLOTS = ["preprocess", "ner", "keywords", "retrieval", "verification", "explanation"]


class VerifyRequest(BaseModel):
    claim: str = Field(min_length=3, max_length=2000)
    # slot -> implementation name; unspecified slots use their default.
    options: dict[str, str] = Field(default_factory=dict)


class StageInfo(BaseModel):
    slot: str
    name: str
    label: str
    description: str
    family: Literal["classical", "neural", "hybrid", "placeholder"]
    is_default: bool
    placeholder: bool


class PipelineEvent(BaseModel):
    """One streamed message. `type` drives the UI state machine."""

    type: Literal["pipeline_start", "stage_start", "stage_end", "pipeline_end", "error"]
    slot: str | None = None
    impl: str | None = None
    placeholder: bool = False
    elapsed_ms: float | None = None
    payload: dict[str, Any] | None = None
    message: str | None = None
