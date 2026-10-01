"""Summaries of the retrieved evidence.

* mmr_summary: extractive. Picks sentences by Maximal Marginal Relevance (relevant to the claim, not redundant with
  those already chosen), so every word of the summary is a verbatim evidence word.
* BartSummarizer: abstractive (DistilBART fine-tuned on CNN/DailyMail). It paraphrases, so unlike MMR it can drift from
  the source; ml/eval_explanation.py measures that with a faithfulness score.
"""
import re
from functools import lru_cache
from pathlib import Path

import numpy as np

from app.nlp import resources
from app.retrieval.tfidf import get_index

SUMMARIZER_DIR = resources.ROOT / "data" / "models" / "distilbart-cnn-6-6"
SUMMARIZER_NAME = "sshleifer/distilbart-cnn-6-6"


def dedupe(sentences: list[str]) -> list[str]:
    seen: set[str] = set()
    out = []
    for s in sentences:
        key = " ".join(s.lower().split())
        if key not in seen:
            seen.add(key)
            out.append(s)
    return out


def mmr_summary(claim: str, sentences: list[str], k: int = 3, lam: float = 0.7) -> list[str]:
    """Up to `k` sentences, in their original (retrieval) order. lam trades relevance (1.0) against novelty (0.0)."""
    sentences = dedupe(sentences)
    if len(sentences) <= 1:
        return sentences
    index = get_index()
    q = index.encode([claim])
    mat = index.encode(sentences)
    rel = (mat @ q.T).toarray().ravel()
    sim = (mat @ mat.T).toarray()
    chosen: list[int] = []
    while len(chosen) < min(k, len(sentences)):
        best, best_score = None, -np.inf
        for i in range(len(sentences)):
            if i in chosen:
                continue
            redundancy = max((sim[i, j] for j in chosen), default=0.0)
            score = lam * rel[i] - (1 - lam) * redundancy
            if score > best_score:
                best, best_score = i, score
        chosen.append(best)  # type: ignore[arg-type]
    return [sentences[i] for i in sorted(chosen)]


class BartSummarizer:
    def __init__(self, directory: Path = SUMMARIZER_DIR):
        import torch
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        if not directory.exists():
            raise FileNotFoundError(f"{directory} not found. Run `python ml/setup_nlp.py --summarizer` to download it.")
        self.torch = torch
        self.tok = AutoTokenizer.from_pretrained(directory)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(directory).eval()

    def summarize(self, texts: list[str]) -> list[str]:
        enc = self.tok(texts, truncation=True, max_length=512, padding=True, return_tensors="pt")
        with self.torch.no_grad():
            out = self.model.generate(
                **enc, max_new_tokens=70, min_new_tokens=15, num_beams=4, no_repeat_ngram_size=3, forced_bos_token_id=0
            )
        return [re.sub(r"\s+([.,;:!?])", r"\g<1>", t).strip() for t in self.tok.batch_decode(out, skip_special_tokens=True)]


@lru_cache(maxsize=1)
def get_bart() -> BartSummarizer:
    return BartSummarizer()
