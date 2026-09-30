"""Kaggle GPU kernel: score every (claim, single retrieved sentence) pair with the fine-tuned BERT.

Input  : datasets dhiptanshumalik/fnev-verif (verif_{val,test}.jsonl) and dhiptanshumalik/fnev-bert (bert_fever/)
Output : /kaggle/working/agg_{val,test}full.npy  float32 (n_claims, 5, 3) raw softmax probabilities (no calibration)

Same pair construction as ml/eval_aggregation.py: the claim's top-5 retrieved sentences, each formatted by
fmt_evidence (identical to backend/app/verification/text.py), padded by repeating the last one if fewer than 5.
"""
import glob
import json
import time
from pathlib import Path

import numpy as np
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

K = 5


def find(pattern: str) -> Path:
    hits = glob.glob(f"/kaggle/input/**/{pattern}", recursive=True)
    assert hits, f"{pattern} not found under /kaggle/input"
    return Path(hits[0])


def fmt_evidence(items: list[dict]) -> str:
    return " ".join(f"{i['title']}: {i['text']}" for i in items)


def main() -> None:
    model_dir = find("model.safetensors").parent  # Kaggle unpacks the uploaded zip; locate the weights rather than assume a folder name
    tok = AutoTokenizer.from_pretrained(model_dir)
    model = AutoModelForSequenceClassification.from_pretrained(model_dir).cuda().half().eval()
    for split in ("val", "test"):
        rows = [json.loads(line) for line in find(f"verif_{split}.jsonl").open(encoding="utf-8")]
        pairs = [(r["claim"], fmt_evidence([s])) for r in rows for s in (r["retrieved"] + [r["retrieved"][-1]] * K)[:K]]
        order = np.argsort([len(c) + len(e) for c, e in pairs])
        out = np.zeros((len(pairs), 3), dtype=np.float32)
        t0 = time.time()
        with torch.no_grad():
            for i in range(0, len(pairs), 256):
                idx = order[i : i + 256]
                enc = tok([pairs[j][0] for j in idx], [pairs[j][1] for j in idx], truncation="only_second", max_length=256,
                          padding=True, return_tensors="pt").to("cuda")
                out[idx] = torch.softmax(model(**enc).logits.float(), dim=-1).cpu().numpy()
        np.save(f"/kaggle/working/agg_{split}full.npy", out.reshape(len(rows), K, 3))
        print(split, len(rows), "claims", len(pairs), "pairs", f"{time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
