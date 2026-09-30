"""Row layout shared by every sentence-level vector matrix.

Row order is the order of `app.data.corpus.iter_sentences`: pages in corpus order, then non-empty sentences in
sentence-id order. Embeddings produced on Kaggle (ml/kaggle/embed) and the word-vector matrices built locally all
follow it, so a (page, sentence) pair maps to the same row everywhere.
"""
from dataclasses import dataclass

import numpy as np


@dataclass
class SentenceLayout:
    page_start: np.ndarray  # (n_pages + 1,) first row of each page; page_start[-1] == n_rows
    sent_ids: np.ndarray  # (n_rows,) FEVER sentence id of each row

    @classmethod
    def from_pages(cls, page_sentences: list[list[str]]) -> "SentenceLayout":
        starts = [0]
        ids: list[int] = []
        for sents in page_sentences:
            ids.extend(i for i, s in enumerate(sents) if s)
            starts.append(len(ids))
        return cls(np.asarray(starts, dtype=np.int64), np.asarray(ids, dtype=np.int32))

    @property
    def n_rows(self) -> int:
        return int(self.page_start[-1])

    def rows_of_pages(self, page_idxs: list[int]) -> np.ndarray:
        if not page_idxs:
            return np.empty(0, dtype=np.int64)
        return np.concatenate([np.arange(self.page_start[p], self.page_start[p + 1]) for p in page_idxs])

    def page_of_rows(self, rows: np.ndarray) -> np.ndarray:
        return np.searchsorted(self.page_start, rows, side="right") - 1
