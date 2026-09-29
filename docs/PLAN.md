# Fake News Evidence Verifier — Project Plan

NLP Lab (Course 2604732), Semester VII, GLS University.

## 1. Idea

Given a claim or news snippet, return a verdict (**Supported / Refuted / Not Enough Info**) together with the
retrieved evidence, the sentences that decided it, and a plain-English explanation.
Every stage has a classical and a neural implementation, selectable at runtime, so the app can compare
them side by side.

```
Input → Preprocess → NER + POS + Keywords → Retriever (TF-IDF ⟷ Embeddings, hybrid)
      → Re-rank → BERT/NLI Verifier → Explanation (evidence sentences + summary + rationale)
```

## 2. Syllabus coverage

| Module (sessions) | Where it appears |
|---|---|
| I. Pipeline, entropy/cross-entropy, NLTK/spaCy/TextBlob (1–6) | Preprocess stage with a visible token trace; each library has a specific job; entropy of the retrieval score distribution; cross-entropy as training loss |
| II. BoW, TF-IDF, Word2Vec, n-grams, POS, NER, PCA, LDA, sentiment (7–12) | TF-IDF (+n-gram) retriever; BoW baseline; entity-aware queries; POS-filtered keywords; PCA plot of claim/evidence; LDA topic per article; TextBlob sentiment/subjectivity as a "sensationalism" signal |
| III. WordNet, PMI, co-occurrence, GloVe/Word2Vec, classification (13–18) | WordNet query expansion; PMI keyword ranking; Word2Vec/GloVe retriever; claim-only TF-IDF + LogReg baseline on LIAR |
| IV. RNN/LSTM/GRU, Transformers, transfer learning, NER, dependency parsing, chunking (19–24) | BiLSTM/GRU verifier baseline vs fine-tuned BERT; transformer NER; dependency-parse SVO triples; chunking |
| V. Summarization, generation, metrics, deployment (25–30) | BART/DistilBART evidence summary + templated rationale; Accuracy/P/R/F1/ROUGE/BLEU dashboard; FastAPI + Docker deployment |

Course outcomes CO1–CO5 are all covered. A GPT-style chatbot (session 26) is optional: a "follow-up question" box.

## 3. Data

- **Evidence corpus:** bounded Wikipedia subset (pages referenced by FEVER gold evidence + a large sample of distractors).
- **Labelled claims:** FEVER (Supports / Refutes / NEI + gold evidence).
- **Baseline:** LIAR (claim-only classifier).
- **Live mode:** Wikipedia search API + a news API (NewsAPI or GNews free tier). No gold labels, so metrics come from FEVER.
- Real datasets only; no invented claims or evidence.

## 4. Repository layout

```
backend/app/{api,core,schemas,stages,pipeline}   FastAPI service, stage registry, orchestrator
backend/tests
ml/                                              training + evaluation (configs, scripts, notebooks)
data/                                            gitignored: raw/, processed/, indexes/
frontend/src/{app,features,components,theme,api,lib}   Vite + React + TypeScript
docs/
```

A stage is `run(input) -> output` registered by name. Adding a retriever/verifier = one file + one config line;
the UI model switcher discovers it from `/api/stages`.

## 5. UI

- Light beige theme + matching warm-charcoal dark theme, driven by CSS design tokens; follows system, manual toggle.
- React, TypeScript, Tailwind, Framer Motion, charts via Recharts/visx.
- Live pipeline view streamed over SSE; annotated claim (NER/POS); evidence cards with highlighted sentences and
  support/refute/neutral bars; verdict gauge + explanation; classical-vs-neural compare mode; Insights tab (PCA/LDA, metrics).

## 6. Build order

1. **Foundation** — scaffold, schemas, stage registry, theme, app shell with mocked streaming pipeline. ← Phase 1
2. **Data** — FEVER download, Wikipedia subset, splits, sentence chunking.
3. **Classical NLP** — preprocessing, NER/POS, keywords (TF-IDF, PMI), TF-IDF retriever, LIAR baseline.
4. **Semantic retrieval** — Word2Vec/GloVe, sentence embeddings + vector index, hybrid; Recall@k, MRR.
5. **Verification** — BiLSTM baseline, fine-tuned BERT (Kaggle GPU), cross-entropy curves.
6. **Explanation** — sentence attribution, summarization, rationale templates.
7. **Evaluation & analysis** — metrics dashboard, PCA/LDA views, ablations.
8. **Polish & deploy** — Docker, README, lab report, demo script.

## 7. Evaluation

- Retrieval: Recall@k, MRR (TF-IDF vs embeddings vs hybrid).
- Verification: accuracy, macro P/R/F1 on FEVER dev (BiLSTM vs BERT vs claim-only baseline).
- Explanation: ROUGE/BLEU vs gold evidence + a manual check of ~30 examples.

## 8. Decisions

- Evidence: FEVER + Wikipedia subset, plus live news search.
- Compute: Kaggle GPU for training (~15–25 min for BERT-base on ~50k pairs); the app runs locally on CPU.
