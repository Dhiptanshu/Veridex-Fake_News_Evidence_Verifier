# Fake News Evidence Verifier

NLP Lab project (Semester VII). Given a claim, the system retrieves evidence, verifies the claim against it,
and explains the verdict. See [docs/PLAN.md](docs/PLAN.md) for the full plan and syllabus mapping.

**Status: Phase 4 (semantic retrieval) done.** Preprocessing, NER, keywords and retrieval (lexical, word-vector and
transformer) are real and run on the FEVER subset; verification and explanation are still labelled placeholders
(Phases 5 and 6).

## Run

```bash
# API (http://127.0.0.1:8000, docs at /docs)
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"     # Windows; use .venv/bin/python on macOS/Linux
.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000
.venv/Scripts/python -m pytest                       # tests

# UI (http://localhost:5173, proxies /api to the API)
cd frontend
npm install
npm run dev
```

## Data (Phase 2)

Real FEVER claims + a bounded Wikipedia evidence corpus. Nothing is synthetic.

```bash
# 1. download raw files into data/raw/ (about 1.7 GB, gitignored)
cd data/raw
curl -LO https://fever.ai/download/fever/train.jsonl
curl -LO https://fever.ai/download/fever/shared_task_dev.jsonl
curl -LO https://fever.ai/download/fever/wiki-pages.zip

# 2. build data/processed/ (about 5 min; streams the zip, never extracts it)
python ml/build_subset.py            # --n-train 40000 --n-val 4000 --n-distractors 60000 --seed 13
```

| Output | Content |
|---|---|
| `claims_{train,val,test}.jsonl` | claim, label, gold evidence sets (`page`, `sent_id`) |
| `corpus.jsonl` | pages with cleaned sentences (index = FEVER sentence id), `gold` flag |
| `stats.json` | split and corpus statistics, shown on the UI's Data tab |

Splits: `train`/`val` are carved from FEVER `train.jsonl`; `test` is FEVER's labelled `shared_task_dev.jsonl`
(balanced 3 ways). Verifiable claims whose gold sentences are missing from the corpus are dropped and counted in
`stats.json`.

**Caveat:** the corpus holds about 70k of Wikipedia's 5.4M pages, so retrieval metrics on it are optimistic compared
with searching all of Wikipedia. Report them as "on the subset".

The Data tab (`/api/data/stats`, `/api/data/claims`) lets you browse the real claims and their evidence.

## Classical NLP and retrieval (Phase 3)

```bash
python ml/setup_nlp.py            # NLTK data -> data/nltk_data, spaCy en_core_web_sm
python ml/build_indexes.py        # data/indexes/tfidf.joblib + pmi.joblib (about 90 s)
python ml/eval_retrieval.py       # ablation on val/test -> docs/results/retrieval_tfidf.json (about 10 min)
python ml/train_claim_baseline.py # claim-only classifiers -> docs/results/claim_only_baseline.json
```

| Slot | Default | Alternatives (switchable in the UI's Pipeline options) |
|---|---|---|
| preprocess | NLTK tokens, POS, WordNet lemmas, TextBlob sentiment | regex tokenizer |
| ner | spaCy entities, noun chunks, SVO triples (dependency parse) | capitalised-span heuristic |
| keywords | TF-IDF weights filtered by POS | TF-IDF + PMI phrases, term frequency |
| retrieval | BGE-small dense search + title bonus (Phase 4) | TF-IDF (+title), TF-IDF only, MiniLM, TF-IDF + MiniLM, TF-IDF + Word2Vec, TF-IDF + GloVe |
| verification, explanation | placeholder (Phases 5 and 6) | |

Retrieval on the 13,202 verifiable test claims, on the subset corpus (Recall@k = all pages or sentences of some
gold evidence set are in the top k):

| Variant | Page R@5 | Page MRR | Sentence R@5 |
|---|---|---|---|
| TF-IDF, claim only | 0.823 | 0.728 | 0.706 |
| + title match from claim n-grams | 0.924 | 0.892 | 0.724 |
| + title match from NER entities too (default) | 0.930 | 0.901 | 0.724 |
| + WordNet query expansion | 0.930 | 0.906 | 0.729 |

Finding pages is largely solved by lexical search plus title matching; picking the right *sentence* (0.72) is the
weak link, which Phase 4's semantic models target. The title boost (0.2) was tuned on val, not test.

Claim-only baseline (no evidence; test accuracy, chance = 0.333): bag-of-words 0.504, TF-IDF 1-2 grams 0.528. An
evidence-based verifier has to beat this.

## Semantic retrieval (Phase 4)

Sentence vectors for all 371,974 corpus sentences, from four models. Two transformer encoders are computed on a
Kaggle GPU (about 3 minutes); the word-vector models are built locally.

```bash
# 1. dense embeddings on Kaggle (needs ~/.kaggle credentials); outputs emb_minilm.npy and emb_bge_small.npy
cd data/kaggle/corpus && cp ../../processed/corpus.jsonl . && kaggle datasets create -p .     # once
cd ml/kaggle/embed && kaggle kernels push -p .                                                # GPU kernel
kaggle kernels output dhiptanshumalik/fnev-embed -p data/kaggle/out && cp data/kaggle/out/emb_*.npy data/indexes/

# 2. local builds
python ml/build_wordvecs.py       # Word2Vec (trained on the corpus) + GloVe 100d -> sent_w2v.npy, sent_glove.npy
python ml/build_topics.py         # LDA, 20 topics -> topics.joblib, docs/results/topics.json
python ml/build_projection.py     # PCA (2 components) for the semantic map

# 3. evaluation (about 1 hour each on CPU)
python ml/eval_semantic.py        # -> docs/results/retrieval_semantic.json
python ml/eval_title_bonus.py     # -> docs/results/retrieval_title_bonus.json
```

The Kaggle kernel embeds `"<title>. <sentence>"` so pronoun-led sentences keep their subject. Row order matches
`app/retrieval/layout.py` and was checked against the local corpus.

Sentence retrieval on the 13,202 verifiable test claims (candidate pages from TF-IDF + title match; hit = all
sentences of some gold evidence set are in the top k):

| Retriever | Recall@1 | Recall@5 |
|---|---|---|
| TF-IDF (Phase 3) | 0.425 | 0.724 |
| Word2Vec (trained here) alone | 0.320 | 0.626 |
| GloVe 100d alone | 0.322 | 0.613 |
| TF-IDF + Word2Vec (40/60) | 0.507 | 0.769 |
| TF-IDF + GloVe (40/60) | 0.482 | 0.758 |
| MiniLM alone | 0.634 | 0.874 |
| TF-IDF + MiniLM (20/80) | 0.649 | 0.881 |
| BGE-small alone | 0.700 | 0.899 |
| BGE-small, global search over all sentences | 0.702 | 0.904 |
| **BGE-small + title bonus 0.02 (default)** | **0.708** | **0.908** |

Findings:
- Averaged word vectors alone are *worse* than TF-IDF; they only help when fused with it. Sentence-level
  transformers are far better: Recall@5 rises from 0.72 to 0.91.
- Once BGE is used, TF-IDF adds nothing (the tuned fusion weight is 0) and candidate pages from TF-IDF add nothing over
  global dense search. What still helps a little is knowing which page the claim names: a 0.02 bonus for sentences on
  title-matched pages gave +0.006 Recall@1 and +0.005 Recall@5 on test (tuned on val).
- Fusion weights and the bonus were tuned on val, not test.

**Topics and map.** LDA assigns each page a dominant topic (shown as a chip on evidence cards); the topics are coherent
(films, albums, football, species, war, ...) but LDA is unsupervised, so a chip can be loosely matched, for example
generic "country" vocabulary is labelled with India. PCA projects the claim and evidence onto a 2-D map; two components
keep only about 6% of the variance, so the UI says distances are approximate.

## Adding a pipeline stage

1. Create a class in `backend/app/stages/` that subclasses `Stage`, sets `slot`, `name`, `label`, `family`,
   and returns the slot's output model from `app/schemas/stages.py`.
2. Decorate it with `@register` and import the module in `app/stages/__init__.py`.
3. It appears in `GET /api/stages` and can be selected per request via `options: {"<slot>": "<name>"}`.

## Layout

```
backend/app/{api,core,schemas,stages,pipeline}   FastAPI service, stage registry, orchestrator
ml/                                              training + evaluation (Kaggle notebooks, configs)
data/                                            gitignored datasets and indexes
frontend/src/{app,features,components,theme,api} Vite + React + TypeScript + Tailwind
docs/                                            plan and report
```
