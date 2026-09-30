"""Tiny randomly-initialised verifiers written to disk, so the serving code is tested without the real models."""
from pathlib import Path

import joblib
import numpy as np
import torch
import torch.nn as nn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from transformers import BertConfig, BertForSequenceClassification, BertTokenizerFast

VOCAB_WORDS = ["marie", "curie", "nobel", "prize", "won", "paris", "capital", "france", "the", "a", "is", "in", "of"]


def write_fake_models(base: Path) -> None:
    torch.manual_seed(0)
    # BERT: one 16-d layer with a hand-made vocabulary
    bert_dir = base / "bert_fever"
    bert_dir.mkdir(parents=True, exist_ok=True)
    vocab = ["[PAD]", "[UNK]", "[CLS]", "[SEP]", "[MASK]", ":", "."] + VOCAB_WORDS
    (bert_dir / "vocab.txt").write_text("\n".join(vocab), encoding="utf-8")
    BertTokenizerFast(vocab_file=str(bert_dir / "vocab.txt"), do_lower_case=True).save_pretrained(bert_dir)
    cfg = BertConfig(vocab_size=len(vocab), hidden_size=16, num_hidden_layers=1, num_attention_heads=2, intermediate_size=32, num_labels=3)
    BertForSequenceClassification(cfg).save_pretrained(bert_dir)

    # BiLSTM / BiGRU: same state-dict layout as RnnNet in ml/kaggle/verify/train.py
    rnn_vocab = ["<pad>", "<unk>", *VOCAB_WORDS]
    for kind, cell in (("lstm", nn.LSTM), ("gru", nn.GRU)):
        rnn = cell(8, 4, batch_first=True, bidirectional=True)
        head = nn.Sequential(nn.Linear(32, 256), nn.ReLU(), nn.Dropout(0.3), nn.Linear(256, 3))
        state = {"emb.weight": torch.randn(len(rnn_vocab), 8)}
        state.update({f"rnn.{k}": v for k, v in rnn.state_dict().items()})
        state.update({f"head.{k}": v for k, v in head.state_dict().items()})
        torch.save({"state": state, "vocab": rnn_vocab}, base / f"{kind}.pt")

    # claim-only: TF-IDF + logistic regression on a toy claim set
    claims = ["marie curie won a prize", "paris is the capital of france", "the moon is cheese", "a prize was won"]
    labels = ["supported", "supported", "refuted", "not_enough_info"]
    joblib.dump(make_pipeline(TfidfVectorizer(), LogisticRegression(max_iter=200)).fit(claims, labels), base / "claim_only.joblib")

    # stacker: logistic regression over the 13 features in app.verification.stack, fitted on random data
    rng = np.random.default_rng(0)
    X = rng.random((60, 13))
    joblib.dump(LogisticRegression(max_iter=200).fit(X, np.arange(60) % 3), base / "stacker.joblib")
