# Demo script (about 7 minutes)

Start the API and the UI (see the README), open the app, and have the Pipeline options panel closed.
All claims below were run through the real pipeline; the verdicts are what the system produced, including its mistakes.

## 1. The idea (30 s)
"Most fake-news projects only label text. This one retrieves evidence from Wikipedia, checks the claim against it with
BERT, and explains why, citing the sentences and showing which words mattered."

## 2. A claim that is supported
**Marie Curie won two Nobel Prizes.** -> supported (about 86%).
- Watch the stages light up left to right: preprocess, entities, keywords, retrieve, verify, explain.
- Point out: entities highlighted in the claim (spaCy), the cited sentences marked [1] [2] in the evidence list, the
  semantic map (claim and evidence sit close together, inside the corpus cloud).
- In "Why": click a [1] chip and the page scrolls to that evidence.

## 3. A claim that is refuted, with the reason
**Barack Obama was born in Kenya.** -> refuted (about 78%).
- In "Why", the word heat map: "Kenya" and "born" are the darkest. Explain occlusion: each word was deleted in turn and
  the verdict was re-scored.
- "Wording differs" chips show the claim says Kenya, the evidence does not.

## 4. Not enough information
**Tilda Swinton is a vegan.** -> not enough info (about 85%).
- The rationale says nothing in the retrieved sentences settles it and lists the claim term that appears nowhere ("vegan").

## 5. Uncertainty is shown
**Paris is the capital of Germany.** -> refuted, only about 50%, with the warning "the model is uncertain".
- Mention: plain concatenation of the evidence flipped this to *supported* (0.84); judging each sentence separately and
  combining the scores (the stacker) fixed it. This is the finding behind the 71.5% -> 74.9% accuracy gain.

## 6. An honest failure
**The capital of Australia is Sydney.** -> supported (about 90%), which is WRONG: the retrieved evidence itself says
Canberra. FEVER-trained models lean on word overlap. Say this out loud; it shows we understand the limits.

## 6b. Ground truth in one click
Open **Real FEVER claims** in the claim box, pick one, and run it: the header shows FEVER's own label next to the system's verdict
(a green tick when they agree). It is the quickest way to show the 74.9% number is a real, checkable thing.

## 7. Compare methods live (Compare tab)
Open **Compare**, keep "Default" in Pipeline A and "Claim only (ignores evidence)" in Pipeline B, and run
*Marie Curie won two Nobel Prizes.* The claim-only model has no evidence to cite; the default shows its sources. Add a third
pipeline (TF-IDF retrieval) to show retrieval quality. The old Options panel in Verify offers the same switches per run.

## 7a. Batch (30 s)
Paste three lines such as `Marie Curie won two Nobel Prizes.,supported` and `Paris is the capital of Germany.,refuted`, run the
batch, and point at the accuracy figure and the CSV export. Every run is also in **History**.

## 7 (original). Compare methods live (Pipeline options)
- Verification: pick **Claim-only TF-IDF (baseline)** and re-run the Marie Curie claim. It ignores the evidence, so the
  per-evidence bars go flat. Then BiLSTM, then back to BERT + stacker.
- Retrieval: switch **BGE-small dense** to **TF-IDF only** and compare the evidence returned.
- Explanation: **DistilBART** replaces the extractive summary with a generated one (slower, may paraphrase).

## 7b. Ask a follow-up (45 s)
Under "Why", use the **Ask about this result** box.
- Click **How confident is the model?** and **What are the sources?**: answered from the system's own results, no model call.
- Type a factual question, for example *Where was Obama born?* (Obama claim): the local QA model quotes "Honolulu, Hawaii" from
  the evidence and shows which passage it came from. Then ask something the evidence cannot answer (*Who painted the Mona Lisa?*): it says so instead of guessing.
- If an AICredits key is configured, switch the mode to LLM and ask a reasoning question. Mention the privacy note under the box.

## 7c. Live evidence (optional, needs keys; see docs/API_KEYS.md)
Pipeline options -> Retrieval -> **Live Wikipedia search** or **Live news search**. Point out the source labels and dates in the
evidence cards, and that news-based verdicts are less reliable (different domain, short snippets).

## 8. Data tab (30 s)
Real FEVER claims with their gold evidence, 69,824 Wikipedia pages, label balance per split.

## 9. Insights tab (1 minute)
- "Does evidence help?": claim-only 52.8% vs BERT + stacker 74.9%.
- "Finding the right sentence": TF-IDF 72.4% recall@5 -> BGE 90.8%.
- Training curves: validation loss rises after epoch 1-2 (overfitting), which is why we kept the best checkpoint.
- Confusion matrix: refuted claims are most often mistaken for not-enough-info.

## 10. Theme (10 s)
Toggle light beige / warm dark.

## Questions to expect
- *Why not just fine-tune BERT on the claim?* The claim-only model reaches 52.8%; the evidence is what adds the rest.
- *Is the 74.9% comparable to published FEVER numbers?* Not directly: the corpus is a 70k-page subset, so retrieval is
  easier than on all of Wikipedia (see README caveat).
- *Can it fact-check today's news?* Only the **Live Wikipedia search** retriever can leave the FEVER subset, and it needs
  `FNEV_WIKIPEDIA_CONTACT` set. Verdicts on real-world claims are a demonstration, not fact-checking.
