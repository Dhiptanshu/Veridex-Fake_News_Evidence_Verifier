"""News evidence from GNews or NewsAPI (whichever key is configured; GNews first).

Free plans return headlines, descriptions and a short truncated body, so each article contributes only a few short
sentences. News is also a different domain from the Wikipedia text the verifier was trained on, so treat verdicts based on
news evidence as less reliable than offline ones.

Docs: GNews https://docs.gnews.io/  NewsAPI https://newsapi.org/docs/endpoints/everything
"""
import re
from dataclasses import dataclass

import httpx

from app.core.config import settings
from app.retrieval import hybrid, live
from app.schemas.stages import RetrievalOut

GNEWS_URL = "https://gnews.io/api/v4/search"
NEWSAPI_URL = "https://newsapi.org/v2/everything"
TIMEOUT_S = 10.0
MAX_ARTICLES = 10
MAX_QUERY_CHARS = 120


@dataclass
class Article:
    title: str
    description: str
    content: str
    url: str
    source: str
    published: str


def provider() -> str | None:
    if settings.gnews_api_key.strip():
        return "gnews"
    if settings.newsapi_key.strip():
        return "newsapi"
    return None


def _get_json(url: str, *, params: dict, headers: dict | None = None) -> dict:
    try:
        r = httpx.get(url, params=params, headers=headers or {}, timeout=TIMEOUT_S)
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Could not reach the news service: {exc}") from exc
    if r.status_code in (401, 403):
        raise RuntimeError("The news API rejected the key (check FNEV_GNEWS_API_KEY / FNEV_NEWSAPI_KEY in backend/.env).")
    if r.status_code == 429:
        raise RuntimeError("The news API's request limit is used up (free plans allow about 100 requests per day).")
    try:
        r.raise_for_status()
    except httpx.HTTPError as exc:
        raise RuntimeError(f"The news API returned an error: {exc}") from exc
    return r.json()


def _query(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()[:MAX_QUERY_CHARS]


def search_gnews(query: str, key: str, limit: int = MAX_ARTICLES) -> list[Article]:
    data = _get_json(GNEWS_URL, params={"q": _query(query), "lang": "en", "max": limit, "apikey": key})
    return [
        Article(a.get("title", ""), a.get("description") or "", a.get("content") or "", a.get("url", ""),
                (a.get("source") or {}).get("name", "news"), (a.get("publishedAt") or "")[:10])
        for a in data.get("articles", [])
    ]


def search_newsapi(query: str, key: str, limit: int = MAX_ARTICLES) -> list[Article]:
    data = _get_json(
        NEWSAPI_URL, params={"q": _query(query), "language": "en", "pageSize": limit, "sortBy": "relevancy"},
        headers={"X-Api-Key": key},
    )
    return [
        Article(a.get("title") or "", a.get("description") or "", a.get("content") or "", a.get("url") or "",
                (a.get("source") or {}).get("name", "news"), (a.get("publishedAt") or "")[:10])
        for a in data.get("articles", [])
    ]


def search(query: str) -> list[Article]:
    which = provider()
    if which is None:
        raise RuntimeError(
            "News search is not configured. Add FNEV_GNEWS_API_KEY (https://gnews.io/register) or FNEV_NEWSAPI_KEY "
            "(https://newsapi.org/register) to backend/.env and restart."
        )
    return search_gnews(query, settings.gnews_api_key.strip()) if which == "gnews" else search_newsapi(query, settings.newsapi_key.strip())


def article_items(a: Article) -> list[live.Item]:
    """Headline, description and the (truncated) body as separate short sentences, without duplicates."""
    if not a.url or not a.title:
        return []
    sentences = [a.title.strip()]
    for body in (a.description, live._clean_snippet(a.content)):
        sentences += live.intro_sentences(body)
    seen: set[str] = set()
    unique = [s for s in sentences if not (s.lower() in seen or seen.add(s.lower()))]
    label = f"{a.source} ({a.published})" if a.published else a.source
    doc = live.doc_id_for(a.url)
    return [live.Item(doc_id=doc, title=a.title.strip(), url=a.url, source=label, text=s) for s in unique]


def news_items(query: str) -> list[live.Item]:
    return [it for a in search(query) for it in article_items(a)]


def news_search(res: hybrid.Resources, claim: str, entity_texts: list[str], query: str, **kw) -> RetrievalOut:
    return live.rank_items(res, claim, entity_texts, news_items(query or claim), **kw)


def combined_search(res: hybrid.Resources, claim: str, entity_texts: list[str], query: str, **kw) -> RetrievalOut:
    """Wikipedia (if a contact is configured) plus news (if a key is configured), ranked together."""
    items: list[live.Item] = []
    if settings.wikipedia_contact.strip():
        items += live.wikipedia_items(claim, entity_texts)
    if provider():
        items += news_items(query or claim)
    if not items:
        raise RuntimeError("Nothing is configured: set FNEV_WIKIPEDIA_CONTACT and/or a news API key in backend/.env.")
    return live.rank_items(res, claim, entity_texts, items, **kw)
