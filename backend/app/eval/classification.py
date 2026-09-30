"""Classification metrics for the verdict task (accuracy, precision, recall, F1, confusion matrix)."""
from collections.abc import Sequence

import numpy as np
from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support

LABELS = ["supported", "refuted", "not_enough_info"]


def report(y_true: Sequence[str], y_pred: Sequence[str]) -> dict:
    p, r, f, support = precision_recall_fscore_support(y_true, y_pred, labels=LABELS, zero_division=0)
    mp, mr, mf, _ = precision_recall_fscore_support(y_true, y_pred, labels=LABELS, average="macro", zero_division=0)
    return {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "macro": {"precision": round(float(mp), 4), "recall": round(float(mr), 4), "f1": round(float(mf), 4)},
        "per_class": {
            lab: {"precision": round(float(p[i]), 4), "recall": round(float(r[i]), 4), "f1": round(float(f[i]), 4), "support": int(support[i])}
            for i, lab in enumerate(LABELS)
        },
        "confusion_matrix": {"labels": LABELS, "rows_true_cols_pred": confusion_matrix(y_true, y_pred, labels=LABELS).tolist()},
    }


def cross_entropy(y_idx: Sequence[int], probs: np.ndarray) -> float:
    """Mean negative log-likelihood of the true class (natural log)."""
    p = np.clip(probs[np.arange(len(y_idx)), np.asarray(y_idx)], 1e-12, 1.0)
    return float(-np.log(p).mean())


def expected_calibration_error(y_idx: Sequence[int], probs: np.ndarray, bins: int = 10) -> float:
    """Average gap between confidence and accuracy, weighted by how many predictions fall in each confidence bin."""
    conf, pred = probs.max(axis=1), probs.argmax(axis=1)
    correct = (pred == np.asarray(y_idx)).astype(float)
    edges = np.linspace(0, 1, bins + 1)
    ece = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (conf > lo) & (conf <= hi)
        if m.any():
            ece += m.mean() * abs(correct[m].mean() - conf[m].mean())
    return float(ece)


def fever_score(labels: Sequence[str], preds: Sequence[str], gold_retrieved: Sequence[bool]) -> float:
    """FEVER score: the label must be right AND, for supported/refuted claims, a complete gold evidence set retrieved."""
    ok = [
        y == p and (y == "not_enough_info" or g)
        for y, p, g in zip(labels, preds, gold_retrieved)
    ]
    return float(np.mean(ok))
