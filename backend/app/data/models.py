"""Records written to / read from data/processed. Plain pydantic models, one JSON object per line on disk."""
from typing import Literal

from pydantic import BaseModel

Label = Literal["supported", "refuted", "not_enough_info"]
Split = Literal["train", "val", "test"]


class SentenceRef(BaseModel):
    page: str  # raw FEVER page id, matches CorpusPage.id
    sent_id: int


class Claim(BaseModel):
    id: int
    claim: str
    label: Label
    # Alternative gold evidence sets; the claim is verifiable from any one set. Empty for not_enough_info.
    evidence_sets: list[list[SentenceRef]]


class CorpusPage(BaseModel):
    id: str  # raw FEVER page id, e.g. "Homeland_-LRB-TV_series-RRB-"
    title: str  # display title, e.g. "Homeland (TV series)"
    sentences: list[str]  # index == FEVER sentence id; missing sentences are ""
    gold: bool  # True if some sampled claim cites this page, False for a distractor
