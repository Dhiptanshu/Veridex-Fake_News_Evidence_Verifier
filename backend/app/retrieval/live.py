"""Live evidence: Wikipedia's public API and/or news APIs, ranked with the same BGE embeddings as the offline retriever.

Each source turns a claim into candidate sentences ("items"); one shared step ranks them and builds the pipeline's
RetrievalOut, so the verifier and explainer work unchanged whichever source the evidence came from.

Privacy: the claim text and entity names are sent to the chosen service(s) as search queries.
"""
import hashlib
import re
from dataclasses import dataclass
from urllib.parse import quote

import httpx
import numpy as np
from nltk import sent_tokenize

from app.core.config import settings
from app.retrieval import hybrid
from app.retrieval.search import entropy_bits
from app.schemas.stages import Evidence, EvidenceSentence, RetrievalOut

API = "https://en.wikipedia.org/w/api.php"
TIMEOUT_S = 8.0
MAX_PAGES = 8
MAX_SENTENCES_PER_PAGE = 12
TITLE_BONUS = 0.02  # same bonus as the offline default (tuned on FEVER val)


@dataclass
class Item:
    """One candidate evidence sentence together with the document it came from."""

    doc_id: str
    title: str
    url: str
    source: str
    text: str
    boost_name: str = ""  # a name that, if mentioned in the claim, earns the title bonus (Wikipedia page titles)


# ------------------------------------------------------------------------------------------------ Wikipedia


def _headers() -> dict[str, str]:
    contact = settings.wikipedia_contact.strip()
    if not contact:
        raise RuntimeError(
            "Live Wikipedia search is not configured: Wikimedia's API policy requires contact details in the User-Agent. "
            "Set FNEV_WIKIPEDIA_CONTACT to your email address or a URL (for example in backend/.env), then restart."
        )
    return {"User-Agent": f"FakeNewsEvidenceVerifier/0.1 (university NLP lab project; {contact})"}


def _get(params: dict) -> dict:
    headers = _headers()
    try:
        r = httpx.get(API, params={**params, "format": "json", "formatversion": 2}, headers=headers, timeout=TIMEOUT_S)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Could not reach Wikipedia: {exc}") from exc


def search_titles(query: str, limit: int = 5) -> list[str]:
    data = _get({"action": "query", "list": "search", "srsearch": query, "srlimit": limit, "srnamespace": 0})
    return [hit["title"] for hit in data.get("query", {}).get("search", [])]


def fetch_intros(titles: list[str]) -> dict[str, str]:
    """title -> plain-text introduction. Redirects are followed, so the returned title may differ from the query."""
    if not titles:
        return {}
    data = _get({
        "action": "query", "prop": "extracts", "exintro": 1, "explaintext": 1, "redirects": 1,
        "exlimit": "max", "titles": "|".join(titles),
    })
    return {p["title"]: p.get("extract", "") for p in data.get("query", {}).get("pages", []) if p.get("extract")}


def intro_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    return [s for s in sent_tokenize(text) if len(s.split()) >= 4][:MAX_SENTENCES_PER_PAGE]


def wikipedia_items(claim: str, entity_texts: list[str]) -> list[Item]:
    queries = [claim, *dict.fromkeys(e for e in entity_texts if len(e) > 2)][:4]
    titles: list[str] = []
    for q in queries:
        for t in search_titles(q, limit=4 if q == claim else 3):
            if t not in titles:
                titles.append(t)
    intros = fetch_intros(titles[:MAX_PAGES])
    if not intros:
        raise RuntimeError("Wikipedia returned no pages for this claim.")
    return [
        Item(
            doc_id=t.replace(" ", "_"), title=t, url="https://en.wikipedia.org/wiki/" + quote(t.replace(" ", "_")),
            source="wikipedia (live)", text=s, boost_name=re.sub(r"\s*\([^)]*\)$", "", t).lower(),
        )
        for t, body in intros.items() for s in intro_sentences(body)
    ]


# ------------------------------------------------------------------------------------------------ shared ranking


def _clean_snippet(text: str) -> str:
    """Drop the truncation marker news APIs append, e.g. '... [+1234 chars]' or '... [1234 chars]'."""
    return re.sub(r"\s*(?:…|\.\.\.)?\s*\[\+?\d+ chars\]\s*$", "", text or "").strip()


def rank_items(
    res: hybrid.Resources, claim: str, entity_texts: list[str], items: list[Item], *, store_name: str = "bge_small",
    k_sentences: int = 5, project: bool = True,
) -> RetrievalOut:
    if not items:
        raise RuntimeError("No evidence was found for this claim.")
    store = hybrid.get_store(res, store_name)
    embed_docs = store.encode_docs or store.encode
    q = store.encode([claim])[0]
    docs = embed_docs([f"{it.title}. {it.text}" for it in items])
    scores = docs @ q
    lowered = claim.lower() + " " + " ".join(entity_texts).lower()
    scores = scores + np.array([TITLE_BONUS if it.boost_name and it.boost_name in lowered else 0.0 for it in items])
    order = np.argsort(-scores)[:k_sentences]

    by_doc: dict[str, list[tuple[str, float]]] = {}
    meta: dict[str, Item] = {}
    for i in order:
        by_doc.setdefault(items[i].doc_id, []).append((items[i].text, float(scores[i])))
        meta.setdefault(items[i].doc_id, items[i])
    evidence = [
        Evidence(
            id=doc_id, title=meta[doc_id].title, source=meta[doc_id].source, url=meta[doc_id].url,
            score=round(max(0.0, min(1.0, max(sc for _, sc in ss))), 4),
            sentences=[EvidenceSentence(text=x, score=round(max(0.0, min(1.0, sc)), 4)) for x, sc in ss],
        )
        for doc_id, ss in by_doc.items()
    ]
    evidence.sort(key=lambda e: -e.sentences[0].score)

    projection = None
    if project:
        try:
            from app.retrieval import projection as projection_mod

            projection = projection_mod.get_projector(store_name).project(
                q, claim[:70], docs[order], [(f"{items[i].title}: {items[i].text[:70]}", float(scores[i])) for i in order],
            )
        except FileNotFoundError:
            projection = None
    top10 = np.sort(scores)[::-1][:10]
    z = np.exp((top10 - top10.max()) / 0.05)
    return RetrievalOut(
        evidence=evidence, query=claim, score_entropy=round(entropy_bits((z / z.sum()).tolist()), 3), projection=projection,
    )


def live_search(res: hybrid.Resources, claim: str, entity_texts: list[str], **kw) -> RetrievalOut:
    """Wikipedia only."""
    return rank_items(res, claim, entity_texts, wikipedia_items(claim, entity_texts), **kw)


def doc_id_for(url: str) -> str:
    return "news-" + hashlib.sha1(url.encode()).hexdigest()[:10]
