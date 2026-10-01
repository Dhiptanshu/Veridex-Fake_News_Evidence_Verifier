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
| III | Text classification | claim-only BoW/TF-IDF + logistic regression | 52.8% (the baseline evidence must beat) |
| IV (19-24) | RNN, LSTM, GRU | BiLSTM and BiGRU verifiers over GloVe | 53.4% / 53.8% test accuracy |
| IV | Transformers, BERT, transfer learning | `bert-base-uncased` fine-tuned on claim-evidence pairs; BGE/MiniLM sentence encoders | BERT 71.5%, with stacker 74.9% |
| IV | NER, dependency parsing | spaCy NER; subject-verb-object triples from the dependency parse | shown in the UI |
| IV | Sequence labeling, chunking | POS tags (NLTK) and noun chunks (spaCy) | shown in the UI |
| V (25-27) | Text generation, summarization | templated grounded rationale; extractive (MMR) and abstractive (DistilBART) evidence summaries | see section 5 |
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

## 6. Limitations and ethics

* The verifier is FEVER-trained and leans on word overlap. "The capital of Australia is Sydney" is judged *supported*
  (about 90%) although the retrieved evidence says Canberra; dates and numbers are a known weakness ("died in February
  1798" is wrongly supported when the evidence says January).
* Refuted claims are the hardest class (recall 0.69); they are mostly mistaken for not-enough-info.
* Wikipedia is not neutral or complete; absence of evidence is not evidence of falsehood, which is why "not enough info"
  is a first-class verdict.
* An automated verdict can be mistaken for authority. The UI always shows the evidence, the confidence, and a warning
  when the model is uncertain, and the README states that outputs are demonstrations, not fact-checking.
* Live Wikipedia search sends the claim's text to Wikipedia's public API; it is off until the user configures it.

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
