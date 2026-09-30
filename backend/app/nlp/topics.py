"""LDA topic model over evidence pages (Module II: dimensionality reduction with LDA).

Each page is a bag of words; LDA explains it as a mixture of `n_topics` latent topics. We keep the dominant topic per
page so evidence cards can show what subject the page is about.
"""
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np

from app.nlp import resources
from app.schemas.stages import Topic

TOPICS_PATH = resources.INDEX_DIR / "topics.joblib"


@dataclass
class TopicModel:
    topics: list[Topic]
    page_topic: np.ndarray  # (n_pages,) dominant topic id per page, aligned with TfidfIndex.page_ids
    page_weight: np.ndarray  # (n_pages,) probability of that dominant topic
    perplexity: float

    def for_page(self, page_idx: int) -> Topic:
        return self.topics[int(self.page_topic[page_idx])]

    def save(self, path: Path = TOPICS_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path, compress=3)

    @staticmethod
    def load(path: Path = TOPICS_PATH) -> "TopicModel":
        if not path.exists():
            raise FileNotFoundError(f"{path} not found. Run `python ml/build_topics.py`.")
        return joblib.load(path)


@lru_cache(maxsize=1)
def get_topics() -> TopicModel:
    return TopicModel.load()
