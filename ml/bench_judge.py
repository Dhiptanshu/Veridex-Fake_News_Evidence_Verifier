"""Compare LLM judge models on live-gathered evidence.

    python ml/bench_judge.py [--models openai/gpt-4o-mini openai/gpt-4o anthropic/claude-sonnet-4.6] [--refresh]

Evidence is gathered once per claim (uses news-API quota) and cached in data/cache/judge_bench.json, so trying more models or
prompt changes does not spend any. Claims with a known answer are scored; '?' claims (recent events whose truth is not known
here) are only shown for eyeballing. Prints a table and writes docs/results/judge_bench.json.
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.evidence import engine  # noqa: E402
from app.llm import client  # noqa: E402
from app.nlp import entities  # noqa: E402
from app.retrieval import hybrid  # noqa: E402
from app.schemas.stages import RetrievalOut  # noqa: E402
from app.verification import llm_judge  # noqa: E402

S, R, N, Q = "supported", "refuted", "not_enough_info", "?"
CLAIMS = [
    ("The Eiffel Tower is located in Paris.", S), ("Marie Curie won two Nobel Prizes.", S),
    ("The Taj Mahal is located in Agra.", S), ("Mahatma Gandhi was born in Porbandar.", S),
    ("The Eiffel Tower is in Berlin.", R), ("Albert Einstein was born in France.", R),
    ("The Great Wall of China is visible from space with the naked eye.", R), ("Mumbai is the capital of India.", R),
    ("Drinking hot water kills the coronavirus.", R), ("Tilda Swinton ate a sandwich yesterday.", N),
    ("India won the T20 World Cup.", Q), ("RBI cut the repo rate in its latest policy meeting.", Q),
    ("Modi held talks with Trump on trade.", Q), ("The Eiffel Tower chief is stepping down.", Q),
]
CACHE = ROOT / "data" / "cache" / "judge_bench.json"


def evidence_for(res, claim: str, refresh: bool, cache: dict) -> RetrievalOut:
    if claim in cache and not refresh:
        return RetrievalOut.model_validate(cache[claim])
    ents = [e.text for e in entities.extract(claim).entities]
    out = engine.gather(res, claim, ents, "", project=False)
    cache[claim] = out.model_dump()
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=["openai/gpt-4o-mini", "openai/gpt-4o", "anthropic/claude-sonnet-4.6"])
    ap.add_argument("--refresh", action="store_true")
    a = ap.parse_args()
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    res = hybrid.get_resources()
    rets = {}
    for claim, _ in CLAIMS:
        try:
            rets[claim] = evidence_for(res, claim, a.refresh, cache)
            CACHE.write_text(json.dumps(cache), encoding="utf-8")
        except RuntimeError as exc:
            print(f"[no evidence] {claim}: {exc}")
    results: dict = {m: [] for m in a.models}
    for model in a.models:
        for claim, gold in CLAIMS:
            if claim not in rets:
                continue
            t = time.time()
            try:
                v = llm_judge.judge(claim, rets[claim], model=model)
                row = {"claim": claim, "gold": gold, "verdict": v.label, "confidence": v.confidence, "nuance": v.nuance,
                       "seconds": round(time.time() - t, 1), "reasoning": v.reasoning}
            except client.LLMError as exc:
                row = {"claim": claim, "gold": gold, "verdict": "error", "error": str(exc), "seconds": round(time.time() - t, 1)}
            results[model].append(row)
            print(f"{model:30} {gold:16} -> {row['verdict']:16} {row.get('confidence', 0):.2f} {row['seconds']:>5}s  {claim[:55]}", flush=True)
    print("\nAccuracy on claims with a known answer:")
    summary = {}
    for model, rows in results.items():
        scored = [r for r in rows if r["gold"] != Q]
        ok = sum(r["verdict"] == r["gold"] for r in scored)
        summary[model] = {"correct": ok, "scored": len(scored), "mean_seconds": round(sum(r["seconds"] for r in rows) / max(len(rows), 1), 1)}
        print(f"  {model:30} {ok}/{len(scored)}   mean {summary[model]['mean_seconds']}s")
    (ROOT / "docs" / "results" / "judge_bench.json").write_text(json.dumps({"summary": summary, "rows": results}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
