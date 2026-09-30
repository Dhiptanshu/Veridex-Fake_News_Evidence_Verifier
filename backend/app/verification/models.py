"""Loaders and predictors for the trained verification models. Every predictor maps (claim, evidence text) pairs to
an (n, 3) array of probabilities over LABELS = supported / refuted / not_enough_info."""
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Protocol

import joblib
import numpy as np

from app.verification import text as vtext


def temperature(kind: str, base: Path | None = None) -> float:
    """Calibration temperature fitted on the validation split (ml/eval_verification.py); 1.0 if none was fitted."""
    path = (base or vtext.MODEL_DIR) / "calibration.json"
    if path.exists():
        return float(json.loads(path.read_text(encoding="utf-8")).get(kind, 1.0))
    return 1.0


def _calibrated(probs: np.ndarray, T: float) -> np.ndarray:
    """Temperature-scale probabilities: softmax(log p / T). T > 1 softens overconfident predictions."""
    if T == 1.0:
        return probs
    z = np.log(np.clip(probs, 1e-12, 1.0)) / T
    z -= z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


class Predictor(Protocol):
    def predict(self, pairs: list[tuple[str, str]]) -> np.ndarray: ...


# ---------------------------------------------------------------------------------------------- BERT


class BertPredictor:
    def __init__(self, directory: Path, max_len: int = 256, T: float = 1.0):
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        if not directory.exists():
            raise FileNotFoundError(f"BERT model not found at {directory}. See README (Phase 5) to download it from Kaggle.")
        self.torch = torch
        self.tok = AutoTokenizer.from_pretrained(directory)
        self.model = AutoModelForSequenceClassification.from_pretrained(directory, dtype=torch.float32).eval()
        self.max_len = max_len
        self.T = T

    def predict(self, pairs: list[tuple[str, str]]) -> np.ndarray:
        enc = self.tok(
            [c for c, _ in pairs], [e for _, e in pairs], truncation="only_second", max_length=self.max_len,
            padding=True, return_tensors="pt",
        )
        with self.torch.no_grad():
            logits = self.model(**enc).logits
        return self.torch.softmax(logits / self.T, dim=-1).numpy()


# ---------------------------------------------------------------------------------------------- BiLSTM / BiGRU


def words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


class RnnPredictor:
    """Architecture mirrors RnnNet in ml/kaggle/verify/train.py."""

    def __init__(self, path: Path, kind: str, T: float = 1.0):
        import torch
        import torch.nn as nn

        if not path.exists():
            raise FileNotFoundError(f"{path} not found. See README (Phase 5) to download it from Kaggle.")
        blob = torch.load(path, map_location="cpu", weights_only=True)
        self.vocab = {w: i for i, w in enumerate(blob["vocab"])}
        self.T = T
        self.torch = torch
        state = blob["state"]
        dim, hidden = state["emb.weight"].shape[1], state["rnn.weight_hh_l0"].shape[1]

        class Net(nn.Module):
            def __init__(self):
                super().__init__()
                self.emb = nn.Embedding(len(blob["vocab"]), dim, padding_idx=0)
                self.rnn = (nn.LSTM if kind == "lstm" else nn.GRU)(dim, hidden, batch_first=True, bidirectional=True)
                self.head = nn.Sequential(nn.Linear(8 * hidden, 256), nn.ReLU(), nn.Dropout(0.3), nn.Linear(256, 3))

            def encode(self, x):
                h, _ = self.rnn(self.emb(x))
                return h.masked_fill((x == 0).unsqueeze(-1), -1e4).max(dim=1).values

            def forward(self, c, e):
                a, b = self.encode(c), self.encode(e)
                return self.head(torch.cat([a, b, (a - b).abs(), a * b], dim=-1))

        self.net = Net()
        self.net.load_state_dict(state)
        self.net.eval()

    def _ids(self, texts: list[str], n: int):
        out = self.torch.zeros(len(texts), n, dtype=self.torch.long)
        for i, t in enumerate(texts):
            ids = [self.vocab.get(w, 1) for w in words(t)][:n]
            out[i, : len(ids)] = self.torch.tensor(ids, dtype=self.torch.long)
        return out

    def predict(self, pairs: list[tuple[str, str]]) -> np.ndarray:
        c, e = self._ids([p[0] for p in pairs], 40), self._ids([p[1] for p in pairs], 200)
        with self.torch.no_grad():
            return self.torch.softmax(self.net(c, e) / self.T, dim=-1).numpy()


# ---------------------------------------------------------------------------------------------- claim-only baseline


class ClaimOnlyPredictor:
    """TF-IDF + logistic regression on the claim text alone. Ignores the evidence on purpose: it is the baseline."""

    def __init__(self, path: Path):
        if not path.exists():
            raise FileNotFoundError(f"{path} not found. Run `python ml/train_claim_baseline.py`.")
        self.pipe = joblib.load(path)
        self.order = [list(self.pipe.classes_).index(label) for label in vtext.LABELS]

    def predict(self, pairs: list[tuple[str, str]]) -> np.ndarray:
        return self.pipe.predict_proba([c for c, _ in pairs])[:, self.order]


# ---------------------------------------------------------------------------------------------- registry


@lru_cache(maxsize=8)
def load(kind: str, base: Path | None = None) -> Predictor:
    root = base or vtext.MODEL_DIR
    if kind == "bert":  # raw probabilities: the stacker (stack.py) does the calibrating
        return BertPredictor(root / "bert_fever", T=1.0)
    if kind == "bert_concat":  # plain concatenated-evidence BERT, temperature-scaled
        return BertPredictor(root / "bert_fever", T=temperature("bert", root))
    if kind in ("lstm", "gru"):
        return RnnPredictor(root / f"{kind}.pt", kind, T=temperature(kind, root))
    if kind == "claim_only":
        return ClaimOnlyPredictor(root / "claim_only.joblib")
    raise ValueError(f"unknown verifier {kind!r}")


@lru_cache(maxsize=2)
def load_stacker(base: Path | None = None):
    path = (base or vtext.MODEL_DIR) / "stacker.joblib"
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. Run `python ml/train_stacker.py` (needs the Kaggle outputs, see README).")
    return joblib.load(path)
