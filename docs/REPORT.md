# Fake News Evidence Verifier: lab report

NLP Lab, Course 2604732, B.Tech (CS&E) Semester VII, GLS University.
Code: this repository. Every number below is read from `docs/results/*.json`, produced by the scripts in `ml/`.

## 1. Problem and approach

Classifying a claim as fake or real from its wording alone is brittle and unexplained. Our system instead **retrieves
evidence, verifies the claim against it, and explains the verdict**:

```
claim -> preprocess -> entities + POS + keywords -> retrieve evidence -> BERT verification -> explanation
         (NLTK)         (spaCy, TF-IDF, PMI)        (TF-IDF / BGE)        (+ stacker)        (cited, grounded)
```

Output: *supported*, *refuted* or *not enough info*, the evidence sentences that drove it, a rationale with citations,
the words that mattered, and a summary. Each stage has a classical and a neural implementation selectable at runtime,
which is how we compare them.

## 2. Syllabus coverage

| Module (sessions) | Topic | Where it is used | Result |
|---|---|---|---|
| I (1-6) | NLP pipeline, tokenization, preprocessing | `app/nlp/text.py`: sentence/word tokenization, POS, WordNet lemmas, stop-words | live in the UI's "How it got here" |
| I | Entropy, cross-entropy | entropy of the retrieval score distribution; cross-entropy is the training loss and an evaluation metric | BERT + stacker test cross-entropy 0.636 |
| I | Word embeddings, text encoding | sentence/word vectors for retrieval and the BiLSTM | see Module III |
| I | NLTK, spaCy, TextBlob | NLTK tokens/POS/lemmas, spaCy NER and dependency parse, TextBlob sentiment/subjectivity | all three used, each for a specific job |
| II (7-12) | Bag of Words, TF-IDF | TF-IDF page and sentence retrieval; BoW and TF-IDF claim-only classifiers | claim-only: BoW 50.4%, TF-IDF 52.8% |
| II | N-grams | TF-IDF over 1-2 grams; title matching over claim n-grams | title matching: page recall@5 82.3% -> 92.4% |
| II | POS tagging, NER | POS-filtered keywords; spaCy entities drive title matching | NER + n-gram titles: MRR 0.901 |
| II | PCA, LDA | PCA 2-D semantic map of claim and evidence; LDA topic per evidence page | 20 coherent topics (`docs/results/topics.json`) |
| II | Sentiment analysis | TextBlob polarity and subjectivity of the claim shown as a signal | shown in the UI |
| III (13-18) | Word similarity, WordNet | WordNet synonym query expansion | +0.005 page MRR: marginal, so not in the default |
| III | PMI, co-occurrence | PMI collocations from the corpus as keyword phrases | "TF-IDF + PMI phrases" keyword option |
| III | Word2Vec, GloVe | Word2Vec trained on our corpus, pretrained GloVe-100; IDF-weighted sentence vectors | alone worse than TF-IDF; fused: recall@5 72.4% -> 76.9% |
| III | Text classification | claim-only BoW/TF-IDF + logistic regression on FEVER and on LIAR | FEVER 52.8% (the baseline evidence must beat); LIAR 24.7% (6 classes), 62.8% (binary) |
| IV (19-24) | RNN, LSTM, GRU | BiLSTM and BiGRU verifiers over GloVe | 53.4% / 53.8% test accuracy |
| IV | Transformers, BERT, transfer learning | `bert-base-uncased` fine-tuned on claim-evidence pairs; BGE/MiniLM sentence encoders | BERT 71.5%, with stacker 74.9% |
| IV | NER, dependency parsing | spaCy NER; subject-verb-object triples from the dependency parse | shown in the UI |
| IV | Sequence labeling, chunking | POS tags (NLTK) and noun chunks (spaCy) | shown in the UI |
| V (25-27) | Text generation, summarization, chatbots, LLM APIs | templated grounded rationale; extractive (MMR) and abstractive (DistilBART) evidence summaries; a follow-up question box (intent router + local extractive QA, optional LLM via AICredits) | see section 5 |
| V (28) | Accuracy, precision, recall, F1, BLEU | all reported, plus ROUGE, calibration error and the FEVER score | sections 4 and 5 |
| V (29-30) | Deployment | FastAPI service with streaming (SSE); one-container Docker setup (see section 7) | API + UI run locally |

## 3. Data

FEVER (Thorne et al., 2018): 185,445 human-written claims labelled supported / refuted / not enough info, with gold
Wikipedia evidence sentences. We build a **bounded evidence corpus** of 69,824 Wikipedia pages (every page cited as gold
plus a random sample of other pages), 371,974 sentences. Splits: train 39,729 / val 3,977 claims (carved from FEVER
train) and test 19,868 (FEVER's balanced labelled dev set). Real data only; nothing is synthetic.

*Caveat:* with 70k of Wikipedia's 5.4M pages, retrieval scores are optimistic compared with searching everything.

## 4. Results

**Retrieval** (13,202 verifiable test claims; hit = all sentences of some gold evidence set are in the top k):

| Retriever | Sentence recall@1 | Sentence recall@5 |
|---|---|---|
| TF-IDF | 0.425 | 0.724 |
| Word2Vec + TF-IDF | 0.507 | 0.769 |
| GloVe + TF-IDF | 0.482 | 0.758 |
| MiniLM + TF-IDF | 0.649 | 0.881 |
| BGE-small | 0.700 | 0.899 |
| BGE-small + title bonus (default) | 0.708 | 0.908 |

**Verification** (19,868 balanced test claims, chance 0.333, evidence from our own retriever):

| Verifier | Accuracy | Macro-F1 | Cross-entropy | Calibration error | FEVER score |
|---|---|---|---|---|---|
| Claim-only TF-IDF | 0.528 | 0.527 | 1.011 | 0.122 | n/a |
| BiLSTM + GloVe | 0.534 | 0.519 | 1.022 | 0.137 | 0.498 |
| BiGRU + GloVe | 0.538 | 0.513 | 1.150 | 0.194 | 0.498 |
| BERT, evidence concatenated | 0.715 | 0.711 | 0.830 | 0.147 | 0.680 |
| **BERT + stacker** | **0.749** | **0.747** | **0.636** | **0.024** | **0.714** |

Key findings: (1) the evidence adds about 22 points over the claim alone; (2) the recurrent baselines fit the training
data but barely beat the claim-only model on the balanced test set, and overfit after two epochs; (3) combining BERT's
per-sentence verdicts beats reading all evidence at once, which is brittle; (4) temperature scaling or the stacker fixes
BERT's overconfidence (calibration error 0.147 -> 0.024); (5) with gold evidence the plain BERT reaches 76.2%, so
imperfect retrieval costs about 5 points.

## 5. Explanation

The explanation never generates free text about the claim. It is assembled from checkable parts: **citations** (the
sentences the verifier itself reads as supporting or refuting), a **template** filled with quoted evidence and plain set
differences between claim and evidence, **word importance by occlusion** (delete a word, re-score the verdict), and an
evidence **summary** (extractive MMR by default, DistilBART as an option).

* **Citation quality** (13,202 claims): the decisive sentences contain gold evidence for 90.0% of claims (95.2% when the
  verdict is right); at the same count they are more precise than citing the top-2 retrieved sentences (0.60 vs 0.49).
* **Word attribution is faithful:** deleting the 2 words ranked most important lowers the verdict probability by 0.67 on
  average, against 0.07 for 2 random words; the top-2 words matter more in 98 of 100 claims.
* **Summaries** (250 claims, vs the gold evidence text; faithfulness = share of summary words found in the retrieved
  evidence):

  | Method | ROUGE-1 | ROUGE-2 | ROUGE-L | BLEU | Faithfulness | Words |
  |---|---|---|---|---|---|---|
  | top-1 retrieved | 0.778 | 0.745 | 0.770 | 0.650 | 1.000 | 21.2 |
  | top-3 retrieved | 0.505 | 0.478 | 0.499 | 0.331 | 1.000 | 63.6 |
  | MMR, all 5 retrieved | 0.489 | 0.455 | 0.478 | 0.317 | 1.000 | 63.9 |
  | MMR extractive (served) | 0.535 | 0.503 | 0.525 | 0.355 | 1.000 | 57.2 |
  | DistilBART abstractive (served) | 0.496 | 0.403 | 0.461 | 0.316 | 0.996 | 36.3 |

  Short summaries score higher ROUGE against short gold evidence, so ROUGE here compares methods rather than measuring
  absolute quality. Filtering out sentences the verifier finds irrelevant improved the extractive summary (ROUGE-1 0.488
  to 0.533).
* **Manual review of 30 random explanations** (`docs/results/explanation_samples.md`; 10 of the 30 verdicts disagreed with
  FEVER's label, consistent with the error rate in section 4) found real problems that we fixed:
  a summary glued an unrelated page's sentence ("He is Catholic.") onto the claim's subject, so summaries now use only
  verifier-relevant sentences and name the source page of each sentence; and a text-cleanup step deleted dates when
  removing pronunciation guides, producing a false "not found in any retrieved sentence". Both have regression tests.

## 5b. A second dataset: LIAR (and why FEVER does not transfer)

LIAR (Wang, 2017) has 12,836 PolitiFact statements with six truthfulness labels. Two experiments (`ml/eval_liar.py`,
`docs/results/liar.json`):

* **Claim-only text classification (Module III).** Logistic regression on bag-of-words or TF-IDF: 24.7% accuracy on the
  6 classes (always guessing the biggest class: 20.9%; uniform chance: 16.7%) and 62.8% on true-ish vs false-ish (majority
  56.4%). Adding speaker, party and subject as tokens lifts the binary result to 66.5%, which shows how much of LIAR's
  signal sits in *who said it* rather than in the text.
* **Cross-domain transfer of our pipeline.** On 500 LIAR statements with a clear truth value (mostly-true/true ->
  supported, false/pants-fire -> refuted), the FEVER-trained evidence pipeline answers "not enough info" for **490 of 500**
  and is right on 5 of the 10 it commits to (chance). A claim-only model trained on LIAR gets 70.6% on the same sample
  (majority class 56.0%).

Interpretation: the verifier is not broken; the task is different. FEVER claims are about encyclopedic facts that an
article states or contradicts, while LIAR statements are about voting records, budgets and statistics that an offline
Wikipedia subset does not contain, so "not enough info" is arguably the honest answer. It also shows that a high score on
one benchmark says little about fact-checking in general.

## 5c. From a benchmark system to a live fact-checker

The FEVER system above answers claims about Wikipedia facts. Real misinformation is mostly about **current events**, often in
India, so the deployed pipeline was rebuilt around live evidence (`backend/app/evidence`, `backend/app/verification/llm_judge.py`,
`backend/app/assistant`):

* **Evidence engine.** An LLM (rule-based fallback) writes 2-3 short search queries; GNews (with `country=in` for India),
  NewsAPI and the Google Fact Check API are searched in parallel with Wikipedia as background only. The full text of the most
  relevant articles is downloaded (`trafilatura`, SSRF-guarded), passages are ranked with BGE plus a small credibility prior
  (fact-checker > wire/major > established > unrated), duplicates from syndication are removed, and Wikipedia is capped at 2
  passages unless the news found is off-topic (best news score < 0.72, a threshold read off the benchmark).
* **LLM judge** instead of the Wikipedia-trained BERT for news. It must return strict JSON (verdict, probabilities, reasoning,
  cited passages, per-passage stances, nuance, what is missing); citations are validated, a decisive verdict without a valid
  citation is downgraded to "not enough info", and the prompt states that absence of evidence is not refutation.
* **Choosing the model** (`ml/bench_judge.py`, `docs/results/judge_bench.json`; 14 claims, 10 with a known answer, evidence
  cached so each model sees identical passages): Claude Sonnet 4.6 9/10, GPT-4o 8/10, GPT-4o-mini 8/10; all three declined to
  guess when no relevant passage was retrieved, so the two misses common to all models (a myth claim and a viral health claim)
  are **retrieval gaps**, not judge errors. The sample is small and only indicative.
* **Assistant** with tool calling (news, fact-check, Wikipedia, article reader; at most 4 rounds, URLs restricted to sources
  already shown). In a live test it searched by itself when the evidence did not contain the answer and cited the sources
  it found; an unlabeled-general-knowledge failure seen in testing led to a stricter citation rule in its prompt.
* **What this changes about the claims in this report.** The accuracy figures in sections 4 and 5 describe the *offline FEVER*
  system. No accuracy is claimed for the live pipeline beyond the small benchmark above: there is no labelled live-news dataset
  here, and LLM confidences are not calibrated.

Engineering findings: free news APIs match all query words, so long entity-quoted queries returned nothing (the cause of the
original "cannot find India news" problem); date words in model-written queries had the same effect and are now stripped on
retry; the first news request starts while the LLM is still planning; identical queries are cached and an exhausted daily quota
is remembered so no further requests are wasted. Latency on a healthy machine is about 20-30 s per claim, dominated by article
downloads and the judge call; on a memory-starved machine it doubled or more.

## 6. Limitations and ethics

* The verifier is FEVER-trained and leans on word overlap. "The capital of Australia is Sydney" is judged *supported*
  (about 90%) although the retrieved evidence says Canberra; dates and numbers are a known weakness ("died in February
  1798" is wrongly supported when the evidence says January).
* Refuted claims are the hardest class (recall 0.69); they are mostly mistaken for not-enough-info.
* Wikipedia is not neutral or complete; absence of evidence is not evidence of falsehood, which is why "not enough info"
  is a first-class verdict.
* An automated verdict can be mistaken for authority. The UI always shows the evidence, the confidence, and a warning
  when the model is uncertain, and the README states that outputs are demonstrations, not fact-checking.
* Live Wikipedia, news and LLM follow-up modes send the claim (and, for the LLM, the evidence shown) to third-party APIs; each
  is off until the user configures it, and the default follow-up answerer runs locally and sends nothing.

## 7. Reproducibility and deployment

Build order and commands are in the README (data, indexes, Kaggle GPU kernels, evaluation scripts). Backend tests:
`python -m pytest backend/tests` (no models or network needed; they use tiny stand-ins). The API (FastAPI, streaming over
Server-Sent Events) serves the built frontend, so one process runs the whole app. A `Dockerfile` and
`docker-compose.yml` package this; they were written and linted by reading but **not built or run** in this environment
(the Docker daemon was unavailable and disk space was limited), so treat them as untested.

## References

* Thorne, Vlachos, Christodoulopoulos, Mittal (2018). FEVER: a large-scale dataset for fact extraction and verification. NAACL.
* Devlin, Chang, Lee, Toutanova (2019). BERT: pre-training of deep bidirectional transformers. NAACL.
* Reimers, Gurevych (2019). Sentence-BERT. EMNLP. Xiao et al. (2023). C-Pack: packaged resources for general Chinese/English
  embeddings (BGE).
* Lewis et al. (2020). BART. ACL. Shleifer, Rush (2020). Pre-trained summarization distillation (DistilBART).
* Mikolov et al. (2013). Efficient estimation of word representations in vector space. Pennington, Socher, Manning (2014). GloVe. EMNLP.
* Blei, Ng, Jordan (2003). Latent Dirichlet allocation. JMLR. Carbonell, Goldstein (1998). The use of MMR for summarization. SIGIR.
* Guo, Pleiss, Sun, Weinberger (2017). On calibration of modern neural networks. ICML.
* Course texts: Jurafsky & Martin, *Speech and Language Processing*; Bird, Klein & Loper, *Natural Language Processing with Python*.
