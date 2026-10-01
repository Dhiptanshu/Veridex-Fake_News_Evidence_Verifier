"""Live evidence from Wikipedia's public API (no key needed), for claims outside the FEVER subset.

Search -> fetch the introduction of the top pages -> split into sentences -> rank the sentences against the claim with
the same BGE embeddings as the offline retriever. The output has the same shape as the offline retrieval, so the
verifier and the explainer work unchanged.

Privacy: the claim text and entity names are sent to en.wikipedia.org as search queries.
"""
import re
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


def live_search(
    res: hybrid.Resources, claim: str, entity_texts: list[str], *, store_name: str = "bge_small", k_sentences: int = 5,
    project: bool = True,
) -> RetrievalOut:
    queries = [claim, *dict.fromkeys(e for e in entity_texts if len(e) > 2)][:4]
    titles: list[str] = []
    for q in queries:
        for t in search_titles(q, limit=4 if q == claim else 3):
            if t not in titles:
                titles.append(t)
    intros = fetch_intros(titles[:MAX_PAGES])
    if not intros:
        raise RuntimeError("Wikipedia returned no pages for this claim.")

    items: list[tuple[str, str]] = [(t, s) for t, body in intros.items() for s in intro_sentences(body)]
    store = hybrid.get_store(res, store_name)
    embed_docs = store.encode_docs or store.encode
    q = store.encode([claim])[0]
    docs = embed_docs([f"{t}. {s}" for t, s in items])
    scores = docs @ q
    lowered = claim.lower() + " " + " ".join(entity_texts).lower()
    scores = scores + np.array([TITLE_BONUS if re.sub(r"\s*\([^)]*\)$", "", t).lower() in lowered else 0.0 for t, _ in items])
    order = np.argsort(-scores)[:k_sentences]

    by_title: dict[str, list[tuple[str, float]]] = {}
    for i in order:
        by_title.setdefault(items[i][0], []).append((items[i][1], float(scores[i])))
    evidence = [
        Evidence(
            id=t.replace(" ", "_"), title=t, source="wikipedia (live)", url="https://en.wikipedia.org/wiki/" + quote(t.replace(" ", "_")),
            score=round(max(0.0, min(1.0, max(sc for _, sc in ss))), 4),
            sentences=[EvidenceSentence(text=x, score=round(max(0.0, min(1.0, sc)), 4)) for x, sc in ss],
        )
        for t, ss in by_title.items()
    ]
    evidence.sort(key=lambda e: -e.sentences[0].score)

    projection = None
    if project:
        try:
            from app.retrieval import projection as projection_mod

            top = [items[i] for i in order]
            projection = projection_mod.get_projector(store_name).project(
                q, claim[:70], docs[order], [(f"{t}: {s[:70]}", float(scores[i])) for (t, s), i in zip(top, order)],
            )
        except FileNotFoundError:
            projection = None
    top10 = np.sort(scores)[::-1][:10]
    z = np.exp((top10 - top10.max()) / 0.05)
    entropy = entropy_bits((z / z.sum()).tolist())
    return RetrievalOut(evidence=evidence, query=claim, score_entropy=round(entropy, 3), projection=projection)
