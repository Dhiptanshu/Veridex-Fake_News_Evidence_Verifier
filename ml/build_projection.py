"""Fit the 2-D PCA basis for a dense store -> data/indexes/projection_<store>.joblib

    python ml/build_projection.py [--stores minilm bge_small]
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.retrieval import hybrid, vectors  # noqa: E402
from app.retrieval.projection import Projector  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stores", nargs="+", default=["minilm", "bge_small"])
    a = ap.parse_args()
    for name in a.stores:
        proj = Projector.fit(vectors.load_matrix(hybrid.STORE_FILES[name]))
        proj.save(name)
        print(f"{name}: explained variance of 2 components = {proj.pca.explained_variance_ratio_.sum():.3f}")


if __name__ == "__main__":
    main()
