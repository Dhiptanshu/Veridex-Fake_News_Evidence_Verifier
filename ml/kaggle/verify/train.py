"""Kaggle GPU kernel: train the verification models on (claim, retrieved evidence) -> supported/refuted/not_enough_info.

Models
  * BiLSTM and BiGRU baselines: GloVe-initialised (frozen), claim and evidence encoded separately, max-pooled, combined
    as [c, e, |c-e|, c*e] -> MLP.
  * BERT (bert-base-uncased): fine-tuned on the pair "claim [SEP] evidence" (transfer learning).

Input  : dataset dhiptanshumalik/fnev-verif  (verif_{train,val,test}.jsonl, glove_vocab.json, glove_100.npy)
Output : /kaggle/working  history.json, preds_<model>_<split>_<mode>.npy, bert_fever/ (fp16 weights + tokenizer),
         lstm.pt / gru.pt (+ vocab)
Modes  : "retrieved" = the evidence our retriever returns (real pipeline); "oracle" = gold evidence for supported /
         refuted claims (upper bound; not-enough-info claims keep retrieved evidence).

Training evidence: for supported/refuted claims gold sentences are merged with the retrieved ones (shuffled, at most
5) so the model sees realistic noise; not-enough-info claims use retrieved evidence. Single-sentence examples are added
too so the same model can rate one evidence sentence at a time (used for the per-evidence stance in the UI).

Keep `fmt_evidence` identical to backend/app/verification/text.py.
"""
import glob
import json
import os
import random
import re
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

LABELS = ["supported", "refuted", "not_enough_info"]
L2I = {l: i for i, l in enumerate(LABELS)}
SMOKE = os.environ.get("FNEV_SMOKE") == "1"
SEED = 13
BERT_NAME = os.environ.get("FNEV_BERT", "google/bert_uncased_L-2_H-128_A-2" if SMOKE else "bert-base-uncased")
MAX_LEN = 256
BERT_EPOCHS = 1 if SMOKE else 2
RNN_EPOCHS = 1 if SMOKE else 6
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


def find_dir() -> Path:
    if os.environ.get("FNEV_DATA"):
        return Path(os.environ["FNEV_DATA"])
    hits = glob.glob("/kaggle/input/**/verif_train.jsonl", recursive=True)
    assert hits, "verif_train.jsonl not found under /kaggle/input"
    return Path(hits[0]).parent


IN_DIR = find_dir()
OUT_DIR = Path(os.environ.get("FNEV_OUT", "/kaggle/working"))
OUT_DIR.mkdir(parents=True, exist_ok=True)


# ----------------------------------------------------------------------------------------------------- data


def fmt_evidence(items: list[dict]) -> str:
    return " ".join(f"{i['title']}: {i['text']}" for i in items)


def load(split: str) -> list[dict]:
    rows = [json.loads(line) for line in (IN_DIR / f"verif_{split}.jsonl").open(encoding="utf-8")]
    if SMOKE:
        rows = rows[:200]
    return rows


def train_examples(rows: list[dict], rng: random.Random) -> list[tuple[str, str, int]]:
    out = []
    for r in rows:
        y = L2I[r["label"]]
        if r["label"] == "not_enough_info":
            out.append((r["claim"], fmt_evidence(r["retrieved"][:5]), y))
            if r["retrieved"]:
                out.append((r["claim"], fmt_evidence(r["retrieved"][:1]), y))
        else:
            ev = list(r["gold"])
            seen = {(e["page"], e["text"]) for e in ev}
            ev += [e for e in r["retrieved"] if (e["page"], e["text"]) not in seen]
            ev = ev[:5]  # gold sentences come first, so they survive the cap
            rng.shuffle(ev)
            out.append((r["claim"], fmt_evidence(ev), y))
            if len(r["gold"]) == 1:
                out.append((r["claim"], fmt_evidence(r["gold"]), y))
    return out


def eval_examples(rows: list[dict], mode: str) -> list[tuple[str, str, int]]:
    out = []
    for r in rows:
        ev = r["gold"][:5] if (mode == "oracle" and r["label"] != "not_enough_info" and r["gold"]) else r["retrieved"][:5]
        out.append((r["claim"], fmt_evidence(ev), L2I[r["label"]]))
    return out


# ----------------------------------------------------------------------------------------------------- RNN baselines


def words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


class RnnNet(nn.Module):
    def __init__(self, emb: np.ndarray, kind: str, hidden: int = 128):
        super().__init__()
        self.emb = nn.Embedding.from_pretrained(torch.tensor(emb, dtype=torch.float32), freeze=True, padding_idx=0)
        rnn = nn.LSTM if kind == "lstm" else nn.GRU
        self.rnn = rnn(emb.shape[1], hidden, batch_first=True, bidirectional=True)
        self.head = nn.Sequential(nn.Linear(8 * hidden, 256), nn.ReLU(), nn.Dropout(0.3), nn.Linear(256, 3))

    def encode(self, x):
        h, _ = self.rnn(self.emb(x))
        return h.masked_fill((x == 0).unsqueeze(-1), -1e4).max(dim=1).values

    def forward(self, c, e):
        a, b = self.encode(c), self.encode(e)
        return self.head(torch.cat([a, b, (a - b).abs(), a * b], dim=-1))


def pad(seqs: list[list[int]], n: int) -> torch.Tensor:
    out = torch.zeros(len(seqs), n, dtype=torch.long)
    for i, s in enumerate(seqs):
        out[i, : min(len(s), n)] = torch.tensor(s[:n], dtype=torch.long)
    return out


def run_rnn(kind: str, data: dict, history: dict) -> None:
    vocab_glove = json.load((IN_DIR / "glove_vocab.json").open())
    glove = np.load(IN_DIR / "glove_100.npy").astype(np.float32)
    g_index = {w: i for i, w in enumerate(vocab_glove)}
    counts: dict[str, int] = {}
    for c, e, _ in data["train"]:
        for w in words(c) + words(e):
            counts[w] = counts.get(w, 0) + 1
    vocab = ["<pad>", "<unk>"] + [w for w, n in counts.items() if n >= 2 and w in g_index]
    w2i = {w: i for i, w in enumerate(vocab)}
    emb = np.zeros((len(vocab), glove.shape[1]), dtype=np.float32)
    for w, i in w2i.items():
        if w in g_index:
            emb[i] = glove[g_index[w]]
    print(f"[{kind}] vocab {len(vocab):,}", flush=True)

    def tensorize(ex):
        c = pad([[w2i.get(w, 1) for w in words(x[0])] for x in ex], 40)
        e = pad([[w2i.get(w, 1) for w in words(x[1])] for x in ex], 200)
        return c, e, torch.tensor([x[2] for x in ex])

    tr, va = tensorize(data["train"]), tensorize(data["val_retrieved"])
    torch.manual_seed(SEED)
    net = RnnNet(emb, kind).to(DEVICE)
    opt = torch.optim.Adam([p for p in net.parameters() if p.requires_grad], lr=1e-3)
    lossf = nn.CrossEntropyLoss()

    def predict(t):
        net.eval()
        out = []
        with torch.no_grad():
            for i in range(0, len(t[2]), 512):
                out.append(net(t[0][i : i + 512].to(DEVICE), t[1][i : i + 512].to(DEVICE)).float().cpu())
        return torch.cat(out)

    hist, best, best_state, t0 = [], -1.0, None, time.time()
    for epoch in range(1, RNN_EPOCHS + 1):
        net.train()
        perm = torch.randperm(len(tr[2]))
        total, n = 0.0, 0
        for i in range(0, len(perm), 128):
            idx = perm[i : i + 128]
            logits = net(tr[0][idx].to(DEVICE), tr[1][idx].to(DEVICE))
            loss = lossf(logits, tr[2][idx].to(DEVICE))
            opt.zero_grad()
            loss.backward()
            opt.step()
            total += loss.item() * len(idx)
            n += len(idx)
        logits = predict(va)
        vloss, vacc = lossf(logits, va[2]).item(), (logits.argmax(1) == va[2]).float().mean().item()
        hist.append({"epoch": epoch, "train_loss": round(total / n, 4), "val_loss": round(vloss, 4), "val_acc": round(vacc, 4)})
        print(f"[{kind}] {hist[-1]}", flush=True)
        if vacc > best:
            best, best_state = vacc, {k: v.detach().cpu().clone() for k, v in net.state_dict().items()}
    net.load_state_dict(best_state)
    for split in ("val", "test"):
        for mode in ("retrieved", "oracle"):
            probs = torch.softmax(predict(tensorize(eval_examples(data[f"{split}_rows"], mode))), dim=1).numpy()
            np.save(OUT_DIR / f"preds_{kind}_{split}_{mode}.npy", probs)
    torch.save({"state": best_state, "vocab": vocab}, OUT_DIR / f"{kind}.pt")
    history[kind] = {"epochs": hist, "best_val_acc": round(best, 4), "seconds": round(time.time() - t0, 1)}


# ----------------------------------------------------------------------------------------------------- BERT


def run_bert(data: dict, history: dict) -> None:
    from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup

    tok = AutoTokenizer.from_pretrained(BERT_NAME)
    model = AutoModelForSequenceClassification.from_pretrained(BERT_NAME, num_labels=3).to(DEVICE)

    def encode(ex):
        enc = tok([x[0] for x in ex], [x[1] for x in ex], truncation="only_second", max_length=MAX_LEN)
        return [{"input_ids": i, "token_type_ids": t, "labels": x[2]} for i, t, x in zip(enc["input_ids"], enc["token_type_ids"], ex)]

    def collate(batch):
        n = max(len(b["input_ids"]) for b in batch)
        ids = torch.zeros(len(batch), n, dtype=torch.long)
        tt = torch.zeros_like(ids)
        mask = torch.zeros_like(ids)
        for i, b in enumerate(batch):
            k = len(b["input_ids"])
            ids[i, :k], tt[i, :k], mask[i, :k] = torch.tensor(b["input_ids"]), torch.tensor(b["token_type_ids"]), 1
        return ids, tt, mask, torch.tensor([b["labels"] for b in batch])

    train = encode(data["train"])
    val = encode(data["val_retrieved"])
    g = torch.Generator().manual_seed(SEED)
    train_dl = DataLoader(train, batch_size=32, shuffle=True, collate_fn=collate, generator=g)
    steps = len(train_dl) * BERT_EPOCHS
    opt = torch.optim.AdamW(model.parameters(), lr=2e-5, weight_decay=0.01)
    sched = get_linear_schedule_with_warmup(opt, int(0.06 * steps), steps)
    scaler = torch.amp.GradScaler(enabled=DEVICE == "cuda")
    print(f"[bert] {BERT_NAME}: {len(train):,} train examples, {steps:,} steps", flush=True)

    def predict(examples) -> torch.Tensor:
        model.eval()
        out = []
        dl = DataLoader(examples, batch_size=128, collate_fn=collate)
        with torch.no_grad(), torch.autocast(DEVICE, dtype=torch.float16, enabled=DEVICE == "cuda"):
            for ids, tt, mask, _ in dl:
                out.append(model(input_ids=ids.to(DEVICE), token_type_ids=tt.to(DEVICE), attention_mask=mask.to(DEVICE)).logits.float().cpu())
        return torch.cat(out)

    val_y = torch.tensor([b["labels"] for b in val])
    hist_steps, hist_eval, best, step, t0 = [], [], -1.0, 0, time.time()
    eval_every = max(1, len(train_dl) // 2)
    run_loss = 0.0
    for epoch in range(1, BERT_EPOCHS + 1):
        for ids, tt, mask, y in train_dl:
            model.train()
            with torch.autocast(DEVICE, dtype=torch.float16, enabled=DEVICE == "cuda"):
                out = model(input_ids=ids.to(DEVICE), token_type_ids=tt.to(DEVICE), attention_mask=mask.to(DEVICE), labels=y.to(DEVICE))
            opt.zero_grad()
            scaler.scale(out.loss).backward()
            scaler.unscale_(opt)
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(opt)
            scaler.update()
            sched.step()
            step += 1
            run_loss += out.loss.item()
            if step % 100 == 0:
                hist_steps.append({"step": step, "train_loss": round(run_loss / 100, 4)})
                run_loss = 0.0
            if step % eval_every == 0 or step == steps:
                logits = predict(val)
                vloss = nn.functional.cross_entropy(logits, val_y).item()
                vacc = (logits.argmax(1) == val_y).float().mean().item()
                hist_eval.append({"step": step, "epoch": round(step / len(train_dl), 2), "val_loss": round(vloss, 4), "val_acc": round(vacc, 4)})
                print(f"[bert] {hist_eval[-1]} ({time.time() - t0:.0f}s)", flush=True)
                if vacc > best:
                    best = vacc
                    model.save_pretrained(OUT_DIR / "bert_best")
    model = AutoModelForSequenceClassification.from_pretrained(OUT_DIR / "bert_best").to(DEVICE)
    for split in ("val", "test"):
        for mode in ("retrieved", "oracle"):
            probs = torch.softmax(predict(encode(eval_examples(data[f"{split}_rows"], mode))), dim=1).numpy()
            np.save(OUT_DIR / f"preds_bert_{split}_{mode}.npy", probs)
    model.half().save_pretrained(OUT_DIR / "bert_fever")
    tok.save_pretrained(OUT_DIR / "bert_fever")
    import shutil

    shutil.rmtree(OUT_DIR / "bert_best", ignore_errors=True)
    history["bert"] = {"model": BERT_NAME, "train_steps": hist_steps, "evals": hist_eval, "best_val_acc": round(best, 4), "seconds": round(time.time() - t0, 1)}


def main() -> None:
    rng = random.Random(SEED)
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    rows = {s: load(s) for s in ("train", "val", "test")}
    data = {
        "train": train_examples(rows["train"], rng),
        "val_retrieved": eval_examples(rows["val"], "retrieved"),
        "val_rows": rows["val"],
        "test_rows": rows["test"],
    }
    print(f"device={DEVICE}; train examples {len(data['train']):,}; val {len(rows['val']):,}; test {len(rows['test']):,}", flush=True)
    history: dict = {"config": {"seed": SEED, "bert": BERT_NAME, "max_len": MAX_LEN, "bert_epochs": BERT_EPOCHS, "rnn_epochs": RNN_EPOCHS,
                                "train_examples": len(data["train"]), "device": DEVICE, "labels": LABELS}}
    for kind in ("lstm", "gru"):
        run_rnn(kind, data, history)
        (OUT_DIR / "history.json").write_text(json.dumps(history, indent=2))
    run_bert(data, history)
    (OUT_DIR / "history.json").write_text(json.dumps(history, indent=2))
    print("done", json.dumps({k: v.get("best_val_acc") for k, v in history.items() if k != "config"}))


if __name__ == "__main__":
    main()
