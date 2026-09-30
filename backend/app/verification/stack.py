"""Claim-level verdict from BERT's per-sentence and concatenated predictions.

BERT scores (claim, one evidence sentence) pairs and the (claim, all evidence) pair. A multinomial logistic regression
("stacker", trained on the validation split by ml/train_stacker.py) turns those into the final calibrated verdict. The
feature function is shared by training and serving so they cannot drift apart.
"""
import numpy as np

N_FEATURES = 13


def features(sent_probs: np.ndarray, concat_probs: np.ndarray, top_score: float) -> np.ndarray:
    """sent_probs: (k, 3) per-sentence [supported, refuted, not_enough_info], best-retrieved first; concat_probs: (3,)."""
    top = sent_probs[0]
    return np.concatenate([
        sent_probs.max(axis=0),   # strongest support / refutation / neutrality among the sentences
        sent_probs.mean(axis=0),  # average opinion
        top,                      # opinion of the best-ranked sentence
        concat_probs,             # opinion when the model reads all sentences together
        [top_score],              # how well the best sentence matched the claim
    ]).astype(np.float32)


def batch_features(sent_probs: np.ndarray, concat_probs: np.ndarray, top_scores: np.ndarray) -> np.ndarray:
    """Vectorised `features` for n claims: sent_probs (n, k, 3), concat_probs (n, 3), top_scores (n,)."""
    return np.concatenate([
        sent_probs.max(axis=1), sent_probs.mean(axis=1), sent_probs[:, 0, :], concat_probs, top_scores[:, None],
    ], axis=1).astype(np.float32)
