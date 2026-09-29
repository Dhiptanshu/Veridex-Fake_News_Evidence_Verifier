# Fake News Evidence Verifier

NLP Lab project (Semester VII). Given a claim, the system retrieves evidence, verifies the claim against it,
and explains the verdict. See [docs/PLAN.md](docs/PLAN.md) for the full plan and syllabus mapping.

**Status: Phase 2 (data) done.** The pipeline runs end-to-end and streams to the UI, and the real FEVER data is
built and browsable. Stages marked `placeholder` return labelled stand-ins, not real analysis; they are replaced
phase by phase.

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
