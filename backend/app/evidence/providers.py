"""Live evidence providers: GNews, NewsAPI and the Google Fact Check Tools API. Each returns plain dataclasses and raises
ProviderError with a readable message; the engine isolates failures so one broken provider never kills a run.

Docs: GNews https://docs.gnews.io/ | NewsAPI https://newsapi.org/docs/endpoints/everything |
Fact Check https://developers.google.com/fact-check/tools/api/reference/rest/v1alpha1/claims/search
"""
import re
import threading
import time
from dataclasses import dataclass

import httpx

from app.core.config import settings

GNEWS_URL = "https://gnews.io/api/v4/search"
NEWSAPI_URL = "https://newsapi.org/v2/everything"
FACTCHECK_URL = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
TIMEOUT_S = 10.0
CACHE_TTL_S = 3600  # identical queries within an hour reuse the answer: free plans allow about 100 requests a day


class ProviderError(RuntimeError):
    pass


@dataclass
class Article:
    title: str
    description: str
    content: str
    url: str
    source: str
    published: str  # YYYY-MM-DD


@dataclass
class FactCheck:
    claim: str
    claimant: str
    publisher: str
    title: str
    url: str
    rating: str
    published: str


_cache: dict[tuple, tuple[float, object]] = {}
_lock = threading.Lock()
_exhausted: dict[str, str] = {}  # provider -> date its daily limit was hit; further calls that day are skipped


def cached(key: tuple, fn):
    now = time.time()
    with _lock:
        hit = _cache.get(key)
        if hit and now - hit[0] < CACHE_TTL_S:
            return hit[1]
    value = fn()
    with _lock:
        _cache[key] = (now, value)
    return value


def clear_cache() -> None:
    with _lock:
        _cache.clear()
        _exhausted.clear()


def _get(name: str, url: str, params: dict, headers: dict | None = None) -> dict:
    today = time.strftime("%Y-%m-%d", time.gmtime())
    if _exhausted.get(name) == today:
        raise ProviderError(f"{name}: daily request limit reached (resets at midnight UTC)")
    try:
        r = httpx.get(url, params=params, headers=headers or {}, timeout=TIMEOUT_S)
    except httpx.HTTPError as exc:
        raise ProviderError(f"{name}: could not connect ({type(exc).__name__})") from exc
    if r.status_code in (401, 403):
        raise ProviderError(f"{name}: the key was rejected or lacks access (check backend/.env)")
    if r.status_code == 429:
        _exhausted[name] = today
        raise ProviderError(f"{name}: daily request limit reached (resets at midnight UTC)")
    if r.status_code >= 400:
        raise ProviderError(f"{name}: HTTP {r.status_code}")
    try:
        return r.json()
    except ValueError as exc:
        raise ProviderError(f"{name}: malformed response") from exc


def clean_snippet(text: str) -> str:
    """Drop the truncation marker free news plans append, e.g. '... [+1234 chars]'."""
    return re.sub(r"\s*(?:…|\.\.\.)?\s*\[\+?\d+ chars\]\s*$", "", text or "").strip()


def gnews(query: str, country: str | None = None, limit: int = 10) -> list[Article]:
    key = settings.gnews_api_key.strip()
    if not key:
        raise ProviderError("GNews: no key configured")

    def go() -> list[Article]:
        params = {"q": query[:200], "lang": "en", "max": limit, "sortby": "relevance", "apikey": key}
        if country:
            params["country"] = country
        data = _get("GNews", GNEWS_URL, params)
        return [
            Article(a.get("title") or "", a.get("description") or "", clean_snippet(a.get("content") or ""), a.get("url") or "",
                    (a.get("source") or {}).get("name") or "news", (a.get("publishedAt") or "")[:10])
            for a in data.get("articles", [])
        ]

    return cached(("gnews", query, country, limit), go)  # type: ignore[return-value]


def newsapi(query: str, limit: int = 10) -> list[Article]:
    key = settings.newsapi_key.strip()
    if not key:
        raise ProviderError("NewsAPI: no key configured")

    def go() -> list[Article]:
        data = _get("NewsAPI", NEWSAPI_URL, {"q": query[:200], "language": "en", "pageSize": limit, "sortBy": "relevancy"},
                    {"X-Api-Key": key})
        return [
            Article(a.get("title") or "", a.get("description") or "", clean_snippet(a.get("content") or ""), a.get("url") or "",
                    (a.get("source") or {}).get("name") or "news", (a.get("publishedAt") or "")[:10])
            for a in data.get("articles", [])
        ]

    return cached(("newsapi", query, limit), go)  # type: ignore[return-value]


def factchecks(query: str, limit: int = 8) -> list[FactCheck]:
    key = settings.google_factcheck_key.strip()
    if not key:
        raise ProviderError("Google Fact Check: no key configured")

    def go() -> list[FactCheck]:
        data = _get("Google Fact Check", FACTCHECK_URL, {"query": query[:200], "languageCode": "en", "pageSize": limit, "key": key})
        out = []
        for c in data.get("claims", []):
            for rv in c.get("claimReview", [])[:2]:
                out.append(FactCheck(
                    claim=c.get("text") or "", claimant=c.get("claimant") or "", publisher=(rv.get("publisher") or {}).get("name") or "",
                    title=rv.get("title") or "", url=rv.get("url") or "", rating=rv.get("textualRating") or "",
                    published=(rv.get("reviewDate") or c.get("claimDate") or "")[:10],
                ))
        return out

    return cached(("factcheck", query, limit), go)  # type: ignore[return-value]


def configured() -> dict[str, bool]:
    return {"gnews": bool(settings.gnews_api_key.strip()), "newsapi": bool(settings.newsapi_key.strip()),
            "factcheck": bool(settings.google_factcheck_key.strip()), "wikipedia": bool(settings.wikipedia_contact.strip())}
