"""Build verification data: each claim with the evidence our retriever returns for it (top 5 sentences) plus gold.

    python ml/build_verification_data.py [--limit N]

Writes data/processed/verif_{train,val,test}.jsonl. One JSON object per claim:
  id, claim, label, retrieved [{page, title, text, score}], gold [{page, title, text}] (first gold set, [] for NEI),
  gold_retrieved (true if some whole gold set is inside the retrieved sentences; needed for the FEVER score).
Retrieval is the same as the served default, so training and inference see the same kind of evidence.
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.data import corpus  # noqa: E402
from app.eval import retrieval as ev  # noqa: E402
from app.retrieval import batch, hybrid  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    res = hybrid.get_resources()
    page_row = {pid: i for i, pid in enumerate(res.index.page_ids)}
    out_dir = ROOT / "data" / "processed"

    def sentence(page_id: str, sid: int) -> dict:
        p = page_row[page_id]
        return {"page": page_id, "title": res.index.titles[p], "text": res.index.page_sentences[p][sid]}

    for split in ("val", "test", "train"):
        claims = corpus.load_claims(split)
        claims = claims[: a.limit] if a.limit else claims
        t0 = time.time()
        hits = batch.retrieve_many(
            res, [c.claim for c in claims],
            progress=lambda d, n: print(f"  {split} {d}/{n} ({time.time() - t0:.0f}s)", flush=True) if d % 2560 == 0 or d == n else None,
        )
        n_gold = n_ok = 0
        with (out_dir / f"verif_{split}.jsonl").open("w", encoding="utf-8", newline="\n") as fh:
            for c, hs in zip(claims, hits):
                retrieved = [
                    {**sentence(res.index.page_ids[h.page_idx], h.sent_id), "score": round(h.score, 4)} for h in hs
                ]
                got = {(r["page"], h.sent_id) for r, h in zip(retrieved, hs)}
                gold = [sentence(r.page, r.sent_id) for r in c.evidence_sets[0]] if c.evidence_sets else []
                ok = any({(r.page, r.sent_id) for r in s} <= got for s in c.evidence_sets)
                if c.evidence_sets:
                    n_gold += 1
                    n_ok += ok
                fh.write(json.dumps({
                    "id": c.id, "claim": c.claim, "label": c.label, "retrieved": retrieved, "gold": gold, "gold_retrieved": ok,
                }, ensure_ascii=False) + "\n")
        print(f"{split}: {len(claims)} claims, gold fully retrieved for {n_ok}/{n_gold} verifiable ({n_ok / max(n_gold, 1):.3f}) "
              f"in {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
