"""Pointwise mutual information over adjacent word pairs: PMI(a,b) = log2( p(a,b) / (p(a) p(b)) ).

High PMI means the words occur together far more often than chance, i.e. a collocation ("nobel prize").
Counts come from the evidence corpus, so the table reflects how this domain actually phrases things.
"""
import math
import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import joblib

from app.nlp import resources

PMI_PATH = resources.INDEX_DIR / "pmi.joblib"
_TOKEN = re.compile(r"[a-z0-9]+")


def tokens(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


@dataclass
class PmiTable:
    unigrams: Counter
    bigrams: Counter
    n_unigrams: int
    n_bigrams: int
    min_count: int = 5

    @classmethod
    def build(cls, sentences: Iterable[str], min_count: int = 5) -> "PmiTable":
        stop = resources.stopwords()
        uni: Counter = Counter()
        bi: Counter = Counter()
        for s in sentences:
            toks = tokens(s)
            uni.update(toks)
            for a, b in zip(toks, toks[1:]):
                if a not in stop and b not in stop:
                    bi[(a, b)] += 1
        bi = Counter({k: v for k, v in bi.items() if v >= min_count})  # keeps the table small and PMI reliable
        return cls(uni, bi, sum(uni.values()), sum(bi.values()), min_count)

    def pmi(self, a: str, b: str) -> float | None:
        c = self.bigrams.get((a, b))
        if not c:
            return None
        return math.log2((c / self.n_bigrams) / ((self.unigrams[a] / self.n_unigrams) * (self.unigrams[b] / self.n_unigrams)))

    def save(self, path: Path = PMI_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path, compress=3)

    @staticmethod
    def load(path: Path = PMI_PATH) -> "PmiTable":
        if not path.exists():
            raise FileNotFoundError(f"PMI table not found at {path}. Run `python ml/build_indexes.py`.")
        return joblib.load(path)


@lru_cache(maxsize=1)
def get_table() -> PmiTable:
    return PmiTable.load()
