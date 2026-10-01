"""Check which optional services are configured in backend/.env and that each one really answers (1 small request each).

    python ml/check_live.py

Never prints a key; only whether it is set and what came back. Uses a few requests of your free-tier quota.
"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import settings  # noqa: E402
from app.qa import llm  # noqa: E402
from app.qa.schemas import AskRequest, Passage  # noqa: E402
from app.retrieval import live, news  # noqa: E402


def step(name: str, configured: bool, fn) -> None:
    if not configured:
        print(f"[skip] {name}: not set in backend/.env")
        return
    t = time.time()
    try:
        print(f"[ ok ] {name}: {fn()}  ({time.time() - t:.1f}s)")
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] {name}: {exc}")


def main() -> None:
    print("configured:", {
        "wikipedia_contact": bool(settings.wikipedia_contact.strip()), "gnews": bool(settings.gnews_api_key.strip()),
        "newsapi": bool(settings.newsapi_key.strip()), "aicredits": bool(settings.aicredits_api_key.strip()),
        "aicredits_model": settings.aicredits_model,
    })
    step("Wikipedia live search", bool(settings.wikipedia_contact.strip()), lambda: live.search_titles("Eiffel Tower completed 1889", 3))
    step("News search", news.provider() is not None, lambda: (
        lambda arts: f"{news.provider()} returned {len(arts)} articles; first: {arts[0].title[:70]!r}" if arts else f"{news.provider()} returned 0 articles"
    )(news.search("Eiffel Tower")))
    req = AskRequest(
        question="Where was Obama born?", claim="Barack Obama was born in Kenya.", label="refuted", confidence=0.78,
        probabilities={"supported": 0.02, "refuted": 0.78, "not_enough_info": 0.2}, rationale="The claim is refuted.",
        passages=[Passage(n=1, title="Barack Obama", text="Obama was born in Honolulu, Hawaii.")],
    )
    step("AICredits LLM answer", bool(settings.aicredits_api_key.strip()), lambda: repr(llm.ask(req)))


if __name__ == "__main__":
    main()
