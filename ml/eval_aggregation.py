"""Concatenated evidence vs aggregating per-sentence verdicts.

    python ml/eval_aggregation.py --n-val 800 --n-test 800        # quick look on a random sample
    python ml/eval_aggregation.py --n-val 0 --n-test 0            # full val/test (slow on CPU)

The fine-tuned BERT scores (claim, one retrieved sentence) pairs; per-claim verdicts are then combined with simple
rules. Rule thresholds are tuned on val and reported on test. Per-sentence probabilities are cached in
data/kaggle/verify_out/agg_<split>.npy so reruns are instant.
"""
import argparse
import json
import random
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.eval import classification as cl  # noqa: E402
from app.verification import models  # noqa: E402
from app.verification import text as vt  # noqa: E402

K = 5
CACHE = ROOT / "data" / "kaggle" / "verify_out"


def load(split: str) -> list[dict]:
    with (ROOT / "data" / "processed" / f"verif_{split}.jsonl").open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh]


def sentence_probs(rows: list[dict], pred, tag: str) -> np.ndarray:
    """(n_claims, K, 3) probabilities for each claim against each of its top-K retrieved sentences alone."""
    path = CACHE / f"agg_{tag}.npy"
    if path.exists():
        cached = np.load(path)
        if len(cached) == len(rows):
            return cached
    pairs = [(r["claim"], vt.fmt_evidence([s])) for r in rows for s in (r["retrieved"] + [r["retrieved"][-1]] * K)[:K]]
    order = np.argsort([len(c) + len(e) for c, e in pairs])
    out = np.zeros((len(pairs), 3), dtype=np.float32)
    t0 = time.time()
    for i in range(0, len(pairs), 64):
        idx = order[i : i + 64]
        out[idx] = pred.predict([pairs[j] for j in idx])
        if (i // 64) % 40 == 0:
            print(f"  {tag}: {i}/{len(pairs)} pairs ({time.time() - t0:.0f}s)", flush=True)
    out = out.reshape(len(rows), K, 3)
    np.save(path, out)
    return out


def aggregate(p: np.ndarray, theta: float, mode: str) -> np.ndarray:
    """Claim-level probabilities from per-sentence ones. p: (n, K, 3)."""
    s, r = p[:, :, 0].max(1), p[:, :, 1].max(1)
    if mode == "max":  # strongest support vs strongest refutation; weak evidence either way -> not enough info
        pred = np.where(np.maximum(s, r) < theta, 2, np.where(s >= r, 0, 1))
    else:  # "nei_mean": mean NEI probability decides NEI when it is high
        nei = p[:, :, 2].mean(1)
        pred = np.where(nei > theta, 2, np.where(s >= r, 0, 1))
    return pred


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-val", type=int, default=800)
    ap.add_argument("--n-test", type=int, default=800)
    a = ap.parse_args()

    pred = models.BertPredictor(vt.MODEL_DIR / "bert_fever", T=1.0)
    data = {}
    for split, n in (("val", a.n_val), ("test", a.n_test)):
        rows = load(split)
        if n:
            rows = random.Random(13).sample(rows, n)
        data[split] = (rows, sentence_probs(rows, pred, f"{split}{n or 'full'}"))

    def labels(rows): return [LABELS.index(r["label"]) for r in rows]
    LABELS = vt.LABELS
    concat = {s: np.load(CACHE / f"preds_bert_{s}_retrieved.npy") for s in ("val", "test")}
    # the cached concat predictions are for all claims; select the sampled rows by claim id
    full = {s: {r["id"]: i for i, r in enumerate(load(s))} for s in ("val", "test")}

    res: dict = {}
    thetas = [round(t, 2) for t in np.arange(0.3, 0.96, 0.05)]
    for mode in ("max", "nei_mean"):
        best = max(thetas, key=lambda t: (aggregate(data["val"][1], t, mode) == labels(data["val"][0])).mean())
        res[mode] = {"theta": best}
        for split in ("val", "test"):
            rows, p = data[split]
            y = labels(rows)
            res[mode][split] = round(float((aggregate(p, best, mode) == y).mean()), 4)
    for split in ("val", "test"):
        rows, _ = data[split]
        idx = [full[split][r["id"]] for r in rows]
        res.setdefault("concat", {})[split] = round(float((concat[split][idx].argmax(1) == labels(rows)).mean()), 4)
    res["n"] = {s: len(data[s][0]) for s in data}
    print(json.dumps(res, indent=2))
    (ROOT / "docs" / "results" / "verification_aggregation.json").write_text(json.dumps(res, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
