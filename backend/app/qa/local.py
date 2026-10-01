"""Local extractive question answering (SQuAD 2.0 MiniLM): finds an answer span inside one evidence passage, or none."""
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np

from app.nlp import resources
from app.qa.schemas import Passage

QA_DIR = resources.ROOT / "data" / "models" / "qa-minilm-squad2"
QA_NAME = "deepset/minilm-uncased-squad2"
MAX_ANSWER_TOKENS = 30
MIN_MARGIN = 0.0  # a span must beat the model's "no answer" score to be returned


@dataclass
class Span:
    text: str
    passage_n: int
    margin: float


def best_span(start: np.ndarray, end: np.ndarray, context: np.ndarray, max_len: int = MAX_ANSWER_TOKENS):
    """Highest-scoring (start, end) inside the context tokens. Returns (score, i, j); (-inf, 0, 0) if there is none."""
    idx = np.flatnonzero(context)
    best = (-np.inf, 0, 0)
    for i in idx:
        for j in idx[(idx >= i) & (idx < i + max_len)]:
            sc = start[i] + end[j]
            if sc > best[0]:
                best = (float(sc), int(i), int(j))
    return best


class ExtractiveQA:
    def __init__(self, directory: Path = QA_DIR):
        import torch
        from transformers import AutoModelForQuestionAnswering, AutoTokenizer

        if not directory.exists():
            raise FileNotFoundError(f"{directory} not found. Run `python ml/setup_nlp.py --qa` to download it.")
        self.torch = torch
        self.tok = AutoTokenizer.from_pretrained(directory)
        self.model = AutoModelForQuestionAnswering.from_pretrained(directory).eval()

    def answer(self, question: str, passages: list[Passage]) -> Span | None:
        if not passages:
            return None
        contexts = [f"{p.title}. {p.text}" for p in passages]
        enc = self.tok(
            [question] * len(contexts), contexts, truncation="only_second", max_length=384, padding=True,
            return_offsets_mapping=True, return_tensors="pt",
        )
        offsets = enc.pop("offset_mapping")
        with self.torch.no_grad():
            out = self.model(**enc)
        best: Span | None = None
        for k, p in enumerate(passages):
            seq = np.array(enc.sequence_ids(k), dtype=object)
            context = np.array([s == 1 for s in seq])
            start, end = out.start_logits[k].numpy(), out.end_logits[k].numpy()
            score, i, j = best_span(start, end, context)
            margin = score - float(start[0] + end[0])  # versus the [CLS] "no answer" score
            if margin > MIN_MARGIN and (best is None or margin > best.margin):
                a, b = int(offsets[k][i][0]), int(offsets[k][j][1])
                best = Span(contexts[k][a:b].strip(), p.n, margin)
        return best


@lru_cache(maxsize=1)
def get_qa() -> ExtractiveQA:
    return ExtractiveQA()


def ready(directory: Path = QA_DIR) -> bool:
    return (directory / "model.safetensors").exists()
