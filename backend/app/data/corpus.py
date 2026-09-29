"""Runtime readers for data/processed. Used by retrievers, training scripts and the data-inspection API."""
import json
from collections.abc import Iterator
from pathlib import Path

from app.data.models import Claim, CorpusPage, Split

PROCESSED_DIR = Path(__file__).resolve().parents[3] / "data" / "processed"


def iter_pages(path: Path | None = None) -> Iterator[CorpusPage]:
    with (path or PROCESSED_DIR / "corpus.jsonl").open(encoding="utf-8") as fh:
        for line in fh:
            yield CorpusPage.model_validate_json(line)


def iter_sentences(path: Path | None = None) -> Iterator[tuple[str, int, str]]:
    """Yield (page_id, sentence_id, text) for every non-empty sentence: the retrieval unit."""
    for page in iter_pages(path):
        for i, text in enumerate(page.sentences):
            if text:
                yield page.id, i, text


def load_claims(split: Split, processed_dir: Path | None = None) -> list[Claim]:
    path = (processed_dir or PROCESSED_DIR) / f"claims_{split}.jsonl"
    with path.open(encoding="utf-8") as fh:
        return [Claim.model_validate_json(line) for line in fh]


def load_stats(processed_dir: Path | None = None) -> dict:
    return json.loads(((processed_dir or PROCESSED_DIR) / "stats.json").read_text(encoding="utf-8"))
