"""Evaluate the explanation generator on the FEVER test claims, using the saved per-sentence BERT scores.

    python ml/eval_explanation.py [--n-summary 250] [--n-attr 100] [--n-samples 30] [--no-bart]

1. Citation quality (all verifiable test claims, no model needed): do the cited sentences contain gold evidence?
   Verdict-driven "decisive" selection vs simply citing the top-ranked retrieved sentences.
2. Summary quality (sample): ROUGE-1/2/L and BLEU against the gold evidence text, and faithfulness (share of summary
   content words that occur in the retrieved evidence) for: top-1 retrieved, top-3 retrieved, MMR extractive, DistilBART.
3. Word-attribution faithfulness (sample): deleting the 2 words occlusion ranks highest should lower the verdict
   probability more than deleting 2 random words.
4. docs/results/explanation_samples.md: random examples for a manual read-through.
Writes docs/results/explanation.json.
"""
import argparse
import json
import random
import re
import sys
from pathlib import Path

import joblib
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.explain import select, summarize  # noqa: E402
from app.explain.clean import tidy  # noqa: E402
from app.nlp import resources  # noqa: E402
from app.schemas.stages import Evidence, EvidenceSentence, RetrievalOut, SentenceVerdict, VerificationOut  # noqa: E402
from app.verification import stack  # noqa: E402
from app.verification.text import LABELS  # noqa: E402

OUT = ROOT / "data" / "kaggle" / "verify_out"
WORD = re.compile(r"[a-z0-9]+")


def load_rows() -> list[dict]:
    with (ROOT / "data" / "processed" / "verif_test.jsonl").open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh]


def gold_texts_by_claim() -> dict[int, list[set[str]]]:
    """claim id -> list of alternative gold evidence sets, each a set of sentence texts."""
    from app.data import corpus

    claims = corpus.load_claims("test")
    needed = {r.page for c in claims for s in c.evidence_sets for r in s}
    pages = {p.id: p.sentences for p in corpus.iter_pages() if p.id in needed}
    return {c.id: [{pages[r.page][r.sent_id] for r in s} for s in c.evidence_sets] for c in claims}


def build_verdicts(rows: list[dict]) -> list[VerificationOut]:
    sent = np.load(OUT / "agg_testfull.npy")
    concat = np.load(OUT / "preds_bert_test_retrieved.npy")
    top = np.array([r["retrieved"][0]["score"] for r in rows], dtype=np.float32)
    probs = joblib.load(ROOT / "data" / "models" / "stacker.joblib").predict_proba(stack.batch_features(sent, concat, top))
    out = []
    for r, p, sp in zip(rows, probs, sent):
        k = int(p.argmax())
        out.append(VerificationOut(
            label=LABELS[k], confidence=float(p[k]), probabilities=dict(zip(LABELS, map(float, p))), per_evidence=[],
            per_sentence=[
                SentenceVerdict(evidence_id=it["page"], title=it["title"], text=it["text"], retrieval_score=min(1.0, it["score"]),
                                supported=float(q[0]), refuted=float(q[1]), neutral=float(q[2]))
                for it, q in zip(r["retrieved"], sp)
            ],
        ))
    return out


def retrieval_of(r: dict) -> RetrievalOut:
    by: dict[str, Evidence] = {}
    for it in r["retrieved"]:
        ev = by.setdefault(it["page"], Evidence(id=it["page"], title=it["title"], source="wikipedia", score=min(1.0, it["score"]), sentences=[]))
        ev.sentences.append(EvidenceSentence(text=it["text"], score=min(1.0, it["score"])))
    return RetrievalOut(evidence=list(by.values()))


def citation_quality(rows, verdicts, gold) -> dict:
    """Share of claims where a cited sentence is gold, and sentence-level precision/recall of the citations."""
    systems = {
        "decisive (verifier-driven)": lambda r, v: [c.text for c in select.select_citations(v, retrieval_of(r))],
        "top-1 retrieved": lambda r, v: [r["retrieved"][0]["text"]],
        "top-2 retrieved": lambda r, v: [it["text"] for it in r["retrieved"][:2]],
    }
    res: dict = {}
    for name, pick in systems.items():
        hit = prec = rec = n = n_ok = hit_ok = 0
        sizes = []
        for r, v in zip(rows, verdicts):
            sets = gold[r["id"]]
            if r["label"] == "not_enough_info" or not sets:
                continue
            cited = pick(r, v)
            sizes.append(len(cited))
            all_gold = set().union(*sets)
            best_cover = max(len(s & set(cited)) / len(s) for s in sets)
            n += 1
            hit += bool(set(cited) & all_gold)
            prec += len(set(cited) & all_gold) / max(len(set(cited)), 1)
            rec += best_cover
            if v.label == r["label"]:
                n_ok += 1
                hit_ok += bool(set(cited) & all_gold)
        res[name] = {
            "claims": n, "mean_citations": round(float(np.mean(sizes)), 2), "hit_rate": round(hit / n, 4),
            "precision": round(prec / n, 4), "gold_set_coverage": round(rec / n, 4),
            "hit_rate_when_verdict_correct": round(hit_ok / max(n_ok, 1), 4),
        }
    return res


def content_words(text: str) -> list[str]:
    stop = resources.stopwords()
    return [w for w in WORD.findall(text.lower()) if w not in stop]


def summary_metrics(rows, verdicts, gold, n: int, use_bart: bool, seed: int = 13) -> dict:
    from nltk.translate.bleu_score import SmoothingFunction, corpus_bleu
    from rouge_score import rouge_scorer

    pool = [i for i, r in enumerate(rows) if r["label"] != "not_enough_info" and gold[r["id"]] and r["gold"]]
    idx = random.Random(seed).sample(pool, min(n, len(pool)))
    scorer = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)
    bart = summarize.get_bart() if use_bart else None

    systems: dict[str, list[str]] = {
        "top-1 retrieved": [], "top-3 retrieved": [], "MMR, all 5 retrieved": [], "MMR extractive (served)": [],
    }
    if bart:
        systems["DistilBART abstractive (served)"] = []
    refs, evid, on_page = [], [], {k: [] for k in systems}
    bart_inputs = []
    for i in idx:
        r = rows[i]
        sents = [tidy(it["text"]) for it in r["retrieved"]]
        page_of = {tidy(it["text"]): it["page"] for it in r["retrieved"]}
        gold_pages = {g["page"] for g in r["gold"]}
        refs.append(" ".join(tidy(s["text"]) for s in r["gold"]))
        evid.append(" ".join(sents))
        cands = [tidy(x) for _, x in select.summary_candidates(verdicts[i], retrieval_of(r))]
        picks = {
            "top-1 retrieved": sents[:1], "top-3 retrieved": sents[:3],
            "MMR, all 5 retrieved": summarize.mmr_summary(r["claim"], sents),
            "MMR extractive (served)": summarize.mmr_summary(r["claim"], cands),
        }
        for name, chosen in picks.items():
            systems[name].append(" ".join(chosen))
            on_page[name].append(float(np.mean([page_of.get(x) in gold_pages for x in chosen])) if chosen else 0.0)
        bart_inputs.append(" ".join(summarize.dedupe(cands)))
    if bart:
        for i in range(0, len(idx), 8):
            systems["DistilBART abstractive (served)"] += bart.summarize(bart_inputs[i : i + 8])
            print(f"  bart {min(i + 8, len(idx))}/{len(idx)}", flush=True)

    smooth = SmoothingFunction().method1
    out = {"claims": len(idx), "reference": "gold evidence sentences of the claim (first gold set)"}
    for name, hyps in systems.items():
        r1 = r2 = rl = 0.0
        for h, ref in zip(hyps, refs):
            s = scorer.score(ref, h)
            r1, r2, rl = r1 + s["rouge1"].fmeasure, r2 + s["rouge2"].fmeasure, rl + s["rougeL"].fmeasure
        n_ = len(hyps)
        faith = [
            (sum(w in set(content_words(ev)) for w in content_words(h)) / max(len(content_words(h)), 1)) for h, ev in zip(hyps, evid)
        ]
        bleu = corpus_bleu([[ref.split()] for ref in refs], [h.split() for h in hyps], smoothing_function=smooth)
        out[name] = {
            "rouge1_f": round(r1 / n_, 4), "rouge2_f": round(r2 / n_, 4), "rougeL_f": round(rl / n_, 4), "bleu": round(bleu, 4),
            "faithfulness": round(float(np.mean(faith)), 4), "mean_words": round(float(np.mean([len(h.split()) for h in hyps])), 1),
        }
        if on_page.get(name):  # extractive systems only: share of chosen sentences that come from a gold evidence page
            out[name]["from_gold_page"] = round(float(np.mean(on_page[name])), 4)
    return out


def attribution_check(rows, verdicts, n: int, seed: int = 13) -> dict:
    """Delete the 2 most important words (by occlusion) vs 2 random words and compare the drop in verdict probability."""
    from app.explain import attribution
    from app.verification import models
    from app.verification import text as vt

    pred = models.BertPredictor(vt.MODEL_DIR / "bert_fever", T=1.0)
    rng = random.Random(seed)
    pool = [i for i, v in enumerate(verdicts) if v.label != "not_enough_info" and v.per_sentence]
    drops_top, drops_rand = [], []
    for i in rng.sample(pool, min(n, len(pool))):
        r, v = rows[i], verdicts[i]
        cite = select.select_citations(v, retrieval_of(r))[0]
        att = attribution.occlude(pred, r["claim"], cite, v.label)
        cw, ew = r["claim"].split(), cite.text.split()[: attribution.MAX_EVIDENCE_WORDS]
        scored = [("c", j, s.score) for j, s in enumerate(att.claim)] + [("e", j, s.score) for j, s in enumerate(att.evidence)]
        if len(scored) < 4:
            continue
        ti = vt.LABELS.index(v.label)

        def prob(drop: list[tuple[str, int]]) -> float:
            c = [w for j, w in enumerate(cw) if ("c", j) not in drop]
            e = [w for j, w in enumerate(ew) if ("e", j) not in drop]
            return float(pred.predict([(" ".join(c), vt.fmt_evidence([{"title": cite.title, "text": " ".join(e)}]))])[0][ti])

        base = prob([])
        top2 = [(k, j) for k, j, _ in sorted(scored, key=lambda t: -t[2])[:2]]
        rand2 = [(k, j) for k, j, _ in rng.sample(scored, 2)]
        drops_top.append(base - prob(top2))
        drops_rand.append(base - prob(rand2))
    return {
        "claims": len(drops_top), "mean_drop_top2_words": round(float(np.mean(drops_top)), 4),
        "mean_drop_random_2_words": round(float(np.mean(drops_rand)), 4),
        "top2_larger_in": round(float(np.mean([a > b for a, b in zip(drops_top, drops_rand)])), 4),
    }


def write_samples(rows, verdicts, n: int, seed: int = 13) -> None:
    from app.stages.explanation import explain

    rng = random.Random(seed)
    lines = ["# Explanation samples (for manual review)\n",
             "Random FEVER test claims through the real verifier and the grounded explainer. `gold` is the label FEVER assigns.\n"]
    for i in rng.sample(range(len(rows)), n):
        r, v = rows[i], verdicts[i]
        ex = explain(r["claim"], v, retrieval_of(r), "mmr")
        mark = "correct" if v.label == r["label"] else "WRONG"
        lines += [f"## {r['claim']}", f"- verdict **{v.label}** ({v.confidence:.0%}) vs gold **{r['label']}** ({mark})",
                  f"- rationale: {ex.rationale}", f"- summary: {ex.summary}"]
        if ex.attribution:
            top = sorted(ex.attribution.claim + ex.attribution.evidence, key=lambda w: -w.score)[:3]
            lines.append("- most important words: " + ", ".join(f"{w.word} ({w.score:.2f})" for w in top))
        lines.append("")
    (ROOT / "docs" / "results" / "explanation_samples.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-summary", type=int, default=250)
    ap.add_argument("--n-attr", type=int, default=100)
    ap.add_argument("--n-samples", type=int, default=30)
    ap.add_argument("--no-bart", action="store_true")
    ap.add_argument("--only-summaries", action="store_true", help="keep citation/attribution results from the previous run")
    a = ap.parse_args()

    rows = load_rows()
    verdicts = build_verdicts(rows)
    gold = gold_texts_by_claim()
    previous = ROOT / "docs" / "results" / "explanation.json"
    out = json.loads(previous.read_text(encoding="utf-8")) if a.only_summaries and previous.exists() else {}
    out["test_claims"] = len(rows)
    if not a.only_summaries:
        out["citations"] = citation_quality(rows, verdicts, gold)
        print(json.dumps(out["citations"], indent=2), flush=True)
    out["summaries"] = summary_metrics(rows, verdicts, gold, a.n_summary, not a.no_bart)
    print(json.dumps(out["summaries"], indent=2), flush=True)
    if not a.only_summaries:
        out["attribution"] = attribution_check(rows, verdicts, a.n_attr)
        print(json.dumps(out["attribution"], indent=2), flush=True)
    write_samples(rows, verdicts, a.n_samples)
    (ROOT / "docs" / "results" / "explanation.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("wrote docs/results/explanation.json and explanation_samples.md")


if __name__ == "__main__":
    main()
