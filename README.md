# Fake News Evidence Verifier

NLP Lab project (Semester VII). Given a claim, the system retrieves evidence, verifies the claim against it,
and explains the verdict. See [docs/PLAN.md](docs/PLAN.md) for the full plan and syllabus mapping.

**Status: Phase 1 (foundation).** The pipeline runs end-to-end and streams to the UI. Stages marked
`placeholder` return labelled stand-ins, not real analysis; they are replaced phase by phase.

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
