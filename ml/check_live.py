"""Check which optional services are configured in backend/.env and that each one really answers (one small request each).

    python ml/check_live.py

Never prints a key; only whether it is set and what came back. Uses a few requests of your free-tier quota.
"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import settings  # noqa: E402
from app.evidence import providers  # noqa: E402
from app.llm import client  # noqa: E402
from app.retrieval import live  # noqa: E402


def step(name: str, configured: bool, fn, missing: str) -> None:
    if not configured:
        print(f"[skip] {name}: not set ({missing})")
        return
    t = time.time()
    try:
        print(f"[ ok ] {name}: {fn()}  ({time.time() - t:.1f}s)")
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] {name}: {exc}")


def first_title(arts) -> str:
    return f"{len(arts)} articles; first: {arts[0].title[:70]!r} ({arts[0].source}, {arts[0].published})" if arts else "0 articles"


def llm_json() -> str:
    data = client.chat_json([{"role": "user", "content": 'Reply with JSON {"ok": true, "word": "ping"}.'}], max_tokens=40)
    return f"JSON reply {data}"


def llm_tools() -> str:
    from app.assistant import tools

    calls = []
    for chunk in client.chat_stream(
        [{"role": "user", "content": "Use the search_news tool to look up 'India cabinet decision'."}], tools=tools.TOOLS, max_tokens=60,
    ):
        calls += chunk.get("tool_calls", [])
    return f"streaming + tool calling work (called {[c['function']['name'] for c in calls]})" if calls else "streaming works but the model did not call a tool"


def main() -> None:
    print("model for verdicts:", settings.aicredits_judge_model or settings.aicredits_model, "| planner/assistant:", settings.aicredits_model)
    step("GNews (India)", bool(settings.gnews_api_key.strip()), lambda: first_title(providers.gnews("Modi cabinet decision", "in", limit=3)), "FNEV_GNEWS_API_KEY")
    step("NewsAPI", bool(settings.newsapi_key.strip()), lambda: first_title(providers.newsapi("Modi cabinet decision", limit=3)), "FNEV_NEWSAPI_KEY")
    step("Google Fact Check", bool(settings.google_factcheck_key.strip()),
         lambda: (lambda r: f"{len(r)} reviews; first: {r[0].publisher} rated {r[0].rating!r}" if r else "0 reviews (key works)")(providers.factchecks("hot water cures cancer", limit=3)),
         "FNEV_GOOGLE_FACTCHECK_KEY")
    step("Wikipedia", bool(settings.wikipedia_contact.strip()), lambda: live.search_titles("Eiffel Tower", 3), "FNEV_WIKIPEDIA_CONTACT")
    step("AICredits JSON", client.configured(), llm_json, "FNEV_AICREDITS_API_KEY")
    step("AICredits streaming + tools", client.configured(), llm_tools, "FNEV_AICREDITS_API_KEY")


if __name__ == "__main__":
    main()
