"""PCA (Module II: dimensionality reduction) of sentence embeddings down to 2-D for the semantic map in the UI.

The PCA basis is fitted once on a sample of corpus sentences; at query time the claim and the retrieved evidence are
projected into that same plane, with a fixed sample of corpus sentences drawn as backdrop.
"""
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
from sklearn.decomposition import PCA

from app.nlp import resources
from app.schemas.stages import MapPoint, Projection

N_FIT = 30_000
N_BACKGROUND = 1_500


@dataclass
class Projector:
    pca: PCA
    background: np.ndarray  # (N_BACKGROUND, 2)

    @staticmethod
    def path(store: str) -> Path:
        return resources.INDEX_DIR / f"projection_{store}.joblib"

    @classmethod
    def fit(cls, matrix: np.ndarray, seed: int = 13) -> "Projector":
        rng = np.random.default_rng(seed)
        rows = np.sort(rng.choice(matrix.shape[0], size=min(N_FIT, matrix.shape[0]), replace=False))
        pca = PCA(n_components=2, random_state=seed).fit(np.asarray(matrix[rows], dtype=np.float32))
        bg_rows = np.sort(rng.choice(matrix.shape[0], size=min(N_BACKGROUND, matrix.shape[0]), replace=False))
        return cls(pca, pca.transform(np.asarray(matrix[bg_rows], dtype=np.float32)))

    def save(self, store: str) -> None:
        self.path(store).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, self.path(store), compress=3)

    @classmethod
    def load(cls, store: str) -> "Projector":
        if not cls.path(store).exists():
            raise FileNotFoundError(f"{cls.path(store)} not found. Run `python ml/build_projection.py`.")
        return joblib.load(cls.path(store))

    def project(self, claim_vec: np.ndarray, claim_label: str, evidence_vecs: np.ndarray, evidence: list[tuple[str, float]]) -> Projection:
        pts = self.pca.transform(np.vstack([claim_vec[None, :], evidence_vecs]).astype(np.float32))
        points = [MapPoint(x=round(float(pts[0, 0]), 4), y=round(float(pts[0, 1]), 4), kind="claim", label=claim_label)]
        for (label, score), (x, y) in zip(evidence, pts[1:]):
            points.append(MapPoint(x=round(float(x), 4), y=round(float(y), 4), kind="evidence", label=label, score=round(score, 4)))
        return Projection(
            points=points,
            background=[(round(float(x), 4), round(float(y), 4)) for x, y in self.background],
            explained_variance=round(float(self.pca.explained_variance_ratio_.sum()), 4),
        )


@lru_cache(maxsize=4)
def get_projector(store: str) -> Projector:
    return Projector.load(store)
