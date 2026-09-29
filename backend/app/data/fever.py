"""Reading FEVER claim files and mapping them to our schema."""
import json
import random
from pathlib import Path

from app.data.models import Claim, Label, SentenceRef

_LABELS: dict[str, Label] = {
    "SUPPORTS": "supported",
    "REFUTES": "refuted",
    "NOT ENOUGH INFO": "not_enough_info",
}


def parse_claim(row: dict) -> Claim:
    sets: list[list[SentenceRef]] = []
    seen: set[frozenset[tuple[str, int]]] = set()
    for ev_set in row["evidence"]:
        refs = [SentenceRef(page=e[2], sent_id=e[3]) for e in ev_set if e[2] is not None and e[3] is not None]
        key = frozenset((r.page, r.sent_id) for r in refs)
        if refs and key not in seen:  # FEVER repeats identical sets, one per annotator
            seen.add(key)
            sets.append(refs)
    return Claim(id=row["id"], claim=row["claim"], label=_LABELS[row["label"]], evidence_sets=sets)


def load_claims(path: Path) -> list[Claim]:
    with path.open(encoding="utf-8") as fh:
        return [parse_claim(json.loads(line)) for line in fh if line.strip()]


def split_train(claims: list[Claim], n_val: int, n_train: int, seed: int) -> tuple[list[Claim], list[Claim]]:
    """Shuffle deterministically, carve a validation set, then take `n_train` from the rest."""
    shuffled = sorted(claims, key=lambda c: c.id)
    random.Random(seed).shuffle(shuffled)
    return shuffled[n_val : n_val + n_train], shuffled[:n_val]


def gold_pages(claims: list[Claim]) -> set[str]:
    return {ref.page for c in claims for s in c.evidence_sets for ref in s}
