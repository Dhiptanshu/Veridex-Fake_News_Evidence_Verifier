"""Stage the Kaggle dataset for the verification kernel in data/kaggle/verif.

    python ml/kaggle/verify/prepare_dataset.py
    cd data/kaggle/verif && kaggle datasets create -p .          # first time; use `datasets version` afterwards

Contents: verif_{train,val,test}.jsonl (from ml/build_verification_data.py), glove_vocab.json and glove_100.npy
(the GloVe vectors as plain arrays so the kernel needs no gensim).
"""
import json
import shutil
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "data" / "kaggle" / "verif"


def main() -> None:
    from gensim.models import KeyedVectors

    OUT.mkdir(parents=True, exist_ok=True)
    for split in ("train", "val", "test"):
        src = ROOT / "data" / "processed" / f"verif_{split}.jsonl"
        if not src.exists():
            sys.exit(f"{src} missing: run ml/build_verification_data.py first")
        shutil.copy(src, OUT / src.name)
    kv = KeyedVectors.load(str(ROOT / "data" / "indexes" / "glove.kv"))
    (OUT / "glove_vocab.json").write_text(json.dumps(list(kv.index_to_key)), encoding="utf-8")
    np.save(OUT / "glove_100.npy", kv.vectors.astype(np.float16))
    (OUT / "dataset-metadata.json").write_text(json.dumps({
        "title": "fnev-verif", "id": "dhiptanshumalik/fnev-verif", "licenses": [{"name": "CC-BY-SA-4.0"}],
    }, indent=2), encoding="utf-8")
    print("staged", sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    main()
