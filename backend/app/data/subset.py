"""Build the bounded evidence corpus + claim splits from raw FEVER files.

Corpus = every page cited by a sampled claim's gold evidence ("gold" pages) + a deterministic random sample
of other pages ("distractors"), so retrieval is a real search problem and not a lookup.
"""
import hashlib
import json
import statistics
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from app.data import fever, wiki
from app.data.models import Claim, CorpusPage

WIKI_PAGES_TOTAL = 5_416_537  # pages in FEVER's wiki-pages.zip; only used to size the distractor sampling rate


@dataclass(frozen=True)
class SubsetConfig:
    raw_dir: Path
    out_dir: Path
    n_train: int = 40_000
    n_val: int = 4_000
    n_distractors: int = 60_000
    seed: int = 13
    total_pages: int = WIKI_PAGES_TOTAL  # size of the raw dump, used to set the distractor sampling rate


def _hash(page_id: str, seed: int) -> int:
    return int(hashlib.md5(f"{seed}:{page_id}".encode()).hexdigest()[:12], 16)


def collect_pages(
    zip_path: Path, gold: set[str], n_distractors: int, seed: int, total_pages: int = WIKI_PAGES_TOTAL
) -> dict[str, CorpusPage]:
    """One streaming pass over the dump. Distractors are the `n_distractors` non-gold pages with the smallest hash."""
    rate = min(1.0, 1.5 * n_distractors / total_pages)
    threshold = int(rate * 16**12)
    pages: dict[str, CorpusPage] = {}
    candidates: list[tuple[int, CorpusPage]] = []
    for raw in wiki.iter_raw_pages(zip_path):
        pid = wiki.page_id_of(raw)
        if pid is None:
            continue
        is_gold = pid in gold
        h = _hash(pid, seed)
        if not is_gold and h >= threshold:
            continue
        sentences = wiki.parse_lines(json.loads(raw).get("lines", ""))
        if not any(sentences):
            continue  # empty pages carry no evidence
        page = CorpusPage(id=pid, title=wiki.display_title(pid), sentences=sentences, gold=is_gold)
        if is_gold:
            pages[pid] = page
        else:
            candidates.append((h, page))
    for _, page in sorted(candidates, key=lambda t: t[0])[:n_distractors]:
        pages[page.id] = page
    return pages


def keep_answerable(claims: list[Claim], pages: dict[str, CorpusPage]) -> tuple[list[Claim], int]:
    """Drop verifiable claims whose gold evidence is not fully present in the corpus. Returns (kept, n_dropped)."""

    def sentence_ok(page: str, sent_id: int) -> bool:
        p = pages.get(page)
        return p is not None and sent_id < len(p.sentences) and bool(p.sentences[sent_id])

    kept: list[Claim] = []
    for c in claims:
        if c.label == "not_enough_info":
            kept.append(c)
            continue
        ok_sets = [s for s in c.evidence_sets if all(sentence_ok(r.page, r.sent_id) for r in s)]
        if ok_sets:
            kept.append(c.model_copy(update={"evidence_sets": ok_sets}))
    return kept, len(claims) - len(kept)


def _write_jsonl(path: Path, records) -> int:
    n = 0
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for r in records:
            fh.write(r.model_dump_json() + "\n")
            n += 1
    return n


def build(cfg: SubsetConfig) -> dict:
    train_all = fever.load_claims(cfg.raw_dir / "train.jsonl")
    test = fever.load_claims(cfg.raw_dir / "shared_task_dev.jsonl")
    train, val = fever.split_train(train_all, cfg.n_val, cfg.n_train, cfg.seed)
    splits = {"train": train, "val": val, "test": test}

    gold = fever.gold_pages([c for cs in splits.values() for c in cs])
    pages = collect_pages(cfg.raw_dir / "wiki-pages.zip", gold, cfg.n_distractors, cfg.seed, cfg.total_pages)

    dropped: dict[str, int] = {}
    for name in splits:
        splits[name], dropped[name] = keep_answerable(splits[name], pages)

    # Keep the corpus minimal: gold pages that no surviving claim cites become plain pages, not gold.
    cited = fever.gold_pages([c for cs in splits.values() for c in cs])
    for p in pages.values():
        p.gold = p.id in cited

    cfg.out_dir.mkdir(parents=True, exist_ok=True)
    for name, claims in splits.items():
        _write_jsonl(cfg.out_dir / f"claims_{name}.jsonl", claims)
    _write_jsonl(cfg.out_dir / "corpus.jsonl", pages.values())

    stats = compute_stats(cfg, splits, pages, dropped)
    (cfg.out_dir / "stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    return stats


def compute_stats(cfg: SubsetConfig, splits: dict[str, list[Claim]], pages: dict[str, CorpusPage], dropped: dict[str, int]) -> dict:
    sent_counts = [sum(1 for s in p.sentences if s) for p in pages.values()]
    return {
        "config": {"n_train": cfg.n_train, "n_val": cfg.n_val, "n_distractors": cfg.n_distractors, "seed": cfg.seed},
        "splits": {
            name: {
                "claims": len(cs),
                "labels": dict(Counter(c.label for c in cs)),
                "dropped_unanswerable": dropped[name],
                "mean_claim_words": round(statistics.mean(len(c.claim.split()) for c in cs), 2) if cs else 0.0,
            }
            for name, cs in splits.items()
        },
        "corpus": {
            "pages": len(pages),
            "gold_pages": sum(p.gold for p in pages.values()),
            "distractor_pages": sum(not p.gold for p in pages.values()),
            "sentences": sum(sent_counts),
            "mean_sentences_per_page": round(statistics.mean(sent_counts), 2) if sent_counts else 0.0,
        },
    }
