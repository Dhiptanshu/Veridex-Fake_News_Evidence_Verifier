# syntax=docker/dockerfile:1
# One image: FastAPI serves the API and the built frontend. The big, reproducible artefacts (indexes, models, processed
# data) are NOT baked in; docker-compose.yml mounts them from ./data. Build: docker compose build

FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim AS app
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

# CPU-only torch first: the default wheel bundles CUDA and is about 2 GB larger.
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu

# Editable install keeps the source in /app/backend, which the app uses to locate /app/data and /app/docs.
COPY backend/pyproject.toml backend/pyproject.toml
COPY backend/app backend/app
RUN pip install -e ./backend

# NLTK data and the spaCy model are small, so they are baked in (data/nltk_data is deliberately not a mounted volume).
COPY ml ml
RUN python ml/setup_nlp.py

COPY docs docs
COPY --from=web /web/dist frontend/dist

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000"]
