# Fake News Evidence Verifier

NLP Lab project (Semester VII). Given a claim, the system retrieves evidence, verifies the claim against it,
and explains the verdict. See [docs/PLAN.md](docs/PLAN.md) for the full plan and syllabus mapping.

**Status: Phases 1-7 done, Phase 8 (polish and deploy) mostly done.** The full pipeline is real: preprocessing, NER,
keywords, retrieval (lexical, word-vector, transformer, live Wikipedia), verification (BiLSTM/BiGRU, fine-tuned BERT)
and a grounded explanation. Open the **Insights** tab for the results. Also see [docs/REPORT.md](docs/REPORT.md) (lab report with
syllabus mapping) and [docs/DEMO.md](docs/DEMO.md) (demo script).

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
| retrieval | BGE-small dense search + title bonus (Phase 4) | TF-IDF (+title), TF-IDF only, MiniLM, TF-IDF + MiniLM, TF-IDF + Word2Vec, TF-IDF + GloVe, live Wikipedia |
| verification | BERT + stacker (Phase 5) | BERT concatenated, BiLSTM, BiGRU, claim-only TF-IDF |
| explanation | grounded rationale + extractive summary | DistilBART abstractive summary |

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

## Verification (Phase 5)

The verifier reads the claim and the evidence our retriever returns (top 5 sentences) and outputs supported / refuted /
not enough info. Training and evaluation use the *retrieved* evidence, so the numbers describe the whole pipeline, not a
gold-evidence shortcut.

```bash
python ml/build_verification_data.py            # retrieve evidence for every claim, about 35 min -> data/processed/verif_*.jsonl
python ml/kaggle/verify/prepare_dataset.py      # stage the Kaggle dataset, then: kaggle datasets create -p data/kaggle/verif
cd ml/kaggle/verify && kaggle kernels push -p . # GPU kernel: BiLSTM, BiGRU, BERT (about 35 min on a T4)
kaggle kernels output dhiptanshumalik/fnev-verify -p data/kaggle/verify_out
# copy bert_fever/, lstm.pt, gru.pt from verify_out into data/models/, then:
python ml/train_claim_baseline.py               # also saves data/models/claim_only.joblib
python ml/eval_verification.py                  # metrics, temperature scaling -> docs/results/verification.json
# per-sentence BERT scores (GPU kernel ml/kaggle/aggregate, upload the model as a dataset first), then:
python ml/eval_aggregation.py --n-val 0 --n-test 0
python ml/train_stacker.py                      # -> data/models/stacker.joblib
```

**Models.** BiLSTM and BiGRU: GloVe-initialised (frozen), claim and evidence encoded separately, max-pooled. BERT:
`bert-base-uncased` fine-tuned for 2 epochs on 75,571 claim-evidence examples (AdamW 2e-5, fp16). For supported/refuted
claims the training evidence is the gold sentences merged with retrieved ones; not-enough-info claims use retrieved
evidence; single-sentence examples are added so the model can also rate one sentence on its own.

**Final verdict ("BERT + stacker").** BERT scores the claim against each of the 5 sentences alone and against all of
them concatenated; a logistic regression on those 13 numbers (trained on the validation split, balanced class weights)
gives the final calibrated probabilities. This beat plain concatenation, which is brittle: for "Paris is the capital of
Germany" every page alone was judged *refuted*, yet the concatenated input flipped to *supported* (0.84).

Test set: 19,868 balanced claims (chance 0.333), evidence from our retriever. FEVER score = label correct **and** a
complete gold evidence set retrieved.

| Verifier | Accuracy | Macro-F1 | Cross-entropy | ECE | FEVER score |
|---|---|---|---|---|---|
| Claim-only TF-IDF (no evidence) | 0.528 | 0.527 | 1.011 | 0.122 | n/a |
| BiLSTM + GloVe | 0.534 | 0.519 | 1.022 | 0.137 | 0.498 |
| BiGRU + GloVe | 0.538 | 0.513 | 1.150 | 0.194 | 0.498 |
| BERT, evidence concatenated | 0.715 | 0.711 | 0.830 | 0.147 | 0.680 |
| BERT concatenated + temperature (T=1.6) | 0.715 | 0.711 | 0.705 | 0.049 | 0.680 |
| BERT, per-sentence max rule | 0.732 | n/a | n/a | n/a | n/a |
| **BERT + stacker (default)** | **0.749** | **0.747** | **0.636** | **0.024** | **0.714** |

With gold evidence given to the concatenated BERT the accuracy is 0.762, so retrieval costs about 5 points; gold
evidence is fully retrieved for 90.8% of supported/refuted test claims, which also caps the FEVER score.

Findings and caveats:
- **Evidence matters, but only a real model uses it.** The BiLSTM/BiGRU baselines barely beat the claim-only model on
  the balanced test set. Their 65% on val was inflated: val is 54% supported and they lean on that prior (supported
  recall 0.84, refuted recall 0.40). Both overfit after epoch 2 (val loss rises while train loss falls; curves in
  `docs/results/verification_history.json`). BERT also peaks near epoch 1.5.
- **Weakest class is refuted**, mostly mislabelled as not-enough-info (retrieved evidence often does not contradict the
  claim directly). The stacker lifted refuted recall from 0.59 to 0.69.
- **It is still a FEVER-trained model**, so it leans on lexical overlap. "The capital of Australia is Sydney" is judged
  *supported* (0.90) even though the retrieved evidence says the capital is Canberra. Treat verdicts on real-world
  claims as a demonstration, not as fact-checking.
- **Calibration:** raw BERT is overconfident (ECE 0.147); temperature scaling (fitted on val) or the stacker fixes it.
- The stacker is trained on the validation split that also chose BERT's checkpoint; test was used once.
- Prior correction for the train/test label shift was tried and changed BERT by only +0.3 points, so it is not applied.

## Explanation (Phase 6)

The explanation is assembled from checkable parts, so it cannot invent facts: **citations** (sentences the verifier itself
reads as supporting or refuting), a **template** filled with quoted evidence and set differences between claim and
evidence, **word importance by occlusion** (delete a word, re-score the verdict) and an evidence **summary** (extractive
MMR by default; `python ml/setup_nlp.py --summarizer` downloads DistilBART for the abstractive option).

```bash
python ml/eval_explanation.py     # citations, ROUGE/BLEU, faithfulness, attribution check, review samples (about 30 min)
```

On the test set: the decisive sentences contain gold evidence for 90.0% of claims (top-2 retrieved: 89.5%, but with
precision 0.49 vs 0.60); deleting the 2 words ranked most important lowers the verdict probability by 0.67 vs 0.07 for 2
random words. Reading 30 random explanations found two real bugs (an unrelated page's sentence glued into a summary, and
dates deleted by text cleanup), both fixed with regression tests. `docs/results/explanation_samples.md` has the samples;
10 of those 30 verdicts disagreed with FEVER's label. Details and the summary table are in the report.

## Live Wikipedia search and deployment (Phase 8)

* **Keys and where to put them:** see [docs/API_KEYS.md](docs/API_KEYS.md) (links, free-tier limits, privacy). Copy
  `backend/.env.example` to `backend/.env` and fill in what you want; every key is optional.
* **Live news** (retrieval options "Live news search" and "Live Wikipedia + news"): GNews or NewsAPI evidence ranked with the
  same BGE embeddings. Free plans return only headlines and short snippets, and news is a different domain from the training
  data, so verdicts from news evidence are less reliable. Needs `FNEV_GNEWS_API_KEY` or `FNEV_NEWSAPI_KEY`.
* **Ask about this result:** a follow-up box under the explanation. It routes "why / how sure / what are the sources"
  questions to the system's own results, answers factual questions with a local SQuAD 2.0 model that quotes a span from the
  evidence (or says the evidence does not answer; `python ml/setup_nlp.py --qa` downloads it), and can use Claude instead
  when `FNEV_ANTHROPIC_API_KEY` is set. Evidence passages are passed to Claude as untrusted data, and the local mode sends
  nothing off the machine.
* **Live mode** (retrieval option "Live Wikipedia search") searches Wikipedia's public API for claims outside the FEVER
  subset and ranks page introductions with BGE. Wikimedia requires contact details in the User-Agent, so it stays off
  until you set `FNEV_WIKIPEDIA_CONTACT` (your email or a URL, for example in `backend/.env`). The claim text and entity
  names are sent to en.wikipedia.org. Verdicts on real-world claims are demonstrations, not fact-checking.
* **One process serves everything:** after `npm run build` in `frontend/`, `uvicorn app.main:app` also serves the UI at `/`.
* **Docker:** `Dockerfile` and `docker-compose.yml` package this (mount `./data/{indexes,models,processed}`). They have **not
  been built or run**: the Docker daemon was not running and disk space was limited. Treat them as untested.

## LIAR (extra)

```bash
# data/raw/liar/{train,valid,test}.tsv from https://sites.cs.ucsb.edu/~william/data/liar_dataset.zip (1 MB)
python ml/eval_liar.py            # -> docs/results/liar.json
```

LIAR (Wang, 2017) has 12.8k PolitiFact statements with 6 truthfulness labels. We train claim-only text classifiers on it
(Module III) and test whether our FEVER-trained evidence pipeline transfers to it. Results are in the report and the
Insights tab.

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
