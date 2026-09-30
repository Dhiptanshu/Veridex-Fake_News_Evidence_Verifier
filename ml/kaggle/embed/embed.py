"""Kaggle GPU kernel: embed every corpus sentence with several sentence encoders.

Input  : dataset dhiptanshumalik/fnev-corpus  (corpus.jsonl, produced by ml/build_subset.py)
Output : /kaggle/working/emb_<model>.npy  float16, shape (n_sentences, dim), L2-normalised
         /kaggle/working/meta.json        order check (count + first/last sentence)

Sentence order is exactly backend/app/data/corpus.iter_sentences: pages in file order, non-empty sentences in
sentence-id order. Each sentence is embedded as "<page title>. <sentence>" so pronoun-led sentences keep context.
"""
import glob
import json
import time

import numpy as np
import torch
from sentence_transformers import SentenceTransformer

MODELS = {
    "minilm": "sentence-transformers/all-MiniLM-L6-v2",
    "bge_small": "BAAI/bge-small-en-v1.5",
}


def find_corpus() -> str:
    hits = glob.glob("/kaggle/input/**/corpus.jsonl", recursive=True)
    assert hits, "corpus.jsonl not found under /kaggle/input"
    return hits[0]


def main() -> None:
    texts: list[str] = []
    with open(find_corpus(), encoding="utf-8") as fh:
        for line in fh:
            page = json.loads(line)
            for sent in page["sentences"]:
                if sent:
                    texts.append(f"{page['title']}. {sent}")
    print(f"{len(texts):,} sentences; cuda={torch.cuda.is_available()}")
    meta = {"n_sentences": len(texts), "first": texts[0], "last": texts[-1]}

    for key, name in MODELS.items():
        t0 = time.time()
        model = SentenceTransformer(name, device="cuda" if torch.cuda.is_available() else "cpu")
        model.max_seq_length = 128
        if torch.cuda.is_available():
            model.half()
        emb = model.encode(texts, batch_size=512, normalize_embeddings=True, show_progress_bar=False, convert_to_numpy=True)
        np.save(f"/kaggle/working/emb_{key}.npy", emb.astype(np.float16))
        meta[key] = {"model": name, "dim": int(emb.shape[1]), "seconds": round(time.time() - t0, 1)}
        print(key, meta[key], flush=True)

    with open("/kaggle/working/meta.json", "w") as fh:
        json.dump(meta, fh, indent=2)


if __name__ == "__main__":
    main()
