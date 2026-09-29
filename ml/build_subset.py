"""Build data/processed from data/raw (FEVER claims + wiki-pages.zip).

    python ml/build_subset.py [--n-train 40000] [--n-val 4000] [--n-distractors 60000] [--seed 13]

Raw files (download from https://fever.ai/download/fever/): train.jsonl, shared_task_dev.jsonl, wiki-pages.zip
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.data.subset import SubsetConfig, build  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw-dir", type=Path, default=ROOT / "data" / "raw")
    ap.add_argument("--out-dir", type=Path, default=ROOT / "data" / "processed")
    ap.add_argument("--n-train", type=int, default=40_000)
    ap.add_argument("--n-val", type=int, default=4_000)
    ap.add_argument("--n-distractors", type=int, default=60_000)
    ap.add_argument("--seed", type=int, default=13)
    a = ap.parse_args()

    t0 = time.time()
    stats = build(SubsetConfig(a.raw_dir, a.out_dir, a.n_train, a.n_val, a.n_distractors, a.seed))
    print(json.dumps(stats, indent=2))
    print(f"done in {time.time() - t0:.0f}s -> {a.out_dir}")


if __name__ == "__main__":
    main()
