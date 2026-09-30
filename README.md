# Fake News Evidence Verifier

NLP Lab project (Semester VII). Given a claim, the system retrieves evidence, verifies the claim against it,
and explains the verdict. See [docs/PLAN.md](docs/PLAN.md) for the full plan and syllabus mapping.

**Status: Phase 3 (classical NLP) done.** Preprocessing, NER, keywords and retrieval are real and run on the FEVER
subset; verification and explanation are still labelled placeholders (Phases 5 and 6).

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
| retrieval | TF-IDF over pages + title match, sentences re-ranked | TF-IDF only |
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
