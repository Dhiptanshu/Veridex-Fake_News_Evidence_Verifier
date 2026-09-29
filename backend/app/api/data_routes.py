"""Read-only views over data/processed so the UI can show the real claims and evidence."""
from functools import lru_cache

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.data import corpus
from app.data.models import CorpusPage, Label, Split

router = APIRouter(prefix="/api/data", tags=["data"])


class EvidenceView(BaseModel):
    page: str
    title: str
    sent_id: int
    text: str


class ClaimView(BaseModel):
    id: int
    claim: str
    label: Label
    evidence_sets: list[list[EvidenceView]]


class ClaimPage(BaseModel):
    total: int
    items: list[ClaimView]


@lru_cache(maxsize=1)
def _pages() -> dict[str, CorpusPage]:
    return {p.id: p for p in corpus.iter_pages()}


@lru_cache(maxsize=3)
def _claims(split: Split):
    return corpus.load_claims(split)


def _require_data() -> None:
    if not (corpus.PROCESSED_DIR / "stats.json").exists():
        raise HTTPException(404, "No processed data. Run `python ml/build_subset.py` first (see README).")


@router.get("/stats")
def stats() -> dict:
    _require_data()
    return corpus.load_stats()


@router.get("/claims", response_model=ClaimPage)
def claims(
    split: Split = "test",
    label: Label | None = None,
    q: str | None = Query(None, min_length=2, max_length=100),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> ClaimPage:
    _require_data()
    pages = _pages()
    rows = [
        c for c in _claims(split)
        if (label is None or c.label == label) and (q is None or q.lower() in c.claim.lower())
    ]
    items = []
    for c in rows[offset : offset + limit]:
        sets = [
            [
                EvidenceView(page=r.page, title=pages[r.page].title, sent_id=r.sent_id, text=pages[r.page].sentences[r.sent_id])
                for r in s
            ]
            for s in c.evidence_sets
        ]
        items.append(ClaimView(id=c.id, claim=c.claim, label=c.label, evidence_sets=sets))
    return ClaimPage(total=len(rows), items=items)
