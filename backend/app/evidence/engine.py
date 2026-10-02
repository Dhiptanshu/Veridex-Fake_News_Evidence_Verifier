"""News-first evidence gathering: plan queries -> search news / fact-checks (/ Wikipedia as background) in parallel ->
fetch the full text of the most relevant articles -> rank passages with BGE plus credibility priors.

Failures are isolated: a provider that errors or hits its quota adds a note, and the run continues with what is left.
"""
import time
from concurrent.futures import ThreadPoolExecutor, wait

from nltk import sent_tokenize

from app.evidence import credibility, fetch, planner, providers
from app.retrieval import hybrid, live
from app.schemas.stages import RetrievalOut

FETCH_TOP = 4  # article bodies to download (the most relevant ones by headline/snippet)
FETCH_DEADLINE_S = 6.0  # slow sites are abandoned: their headline and snippet are used instead
MAX_BODY_SENTENCES = 14
BACKGROUND_PRIOR = -0.02  # Wikipedia may add context but should not outrank news and fact-checks
MAX_BACKGROUND_PASSAGES = 2
MAX_BACKGROUND_WHEN_NEWS_OFF_TOPIC = 5
NEWS_RELEVANT_MIN = 0.72  # in the 14-claim benchmark, on-topic news scored >= 0.76 and off-topic news <= 0.68
FACTCHECK_PRIOR = 0.08
ENOUGH_ARTICLES = 5  # a first query that returns this many distinct articles makes a second request unnecessary


def _norm_title(t: str) -> str:
    return " ".join("".join(c.lower() if c.isalnum() else " " for c in t).split())


def article_items(a: providers.Article) -> list[live.Item]:
    """Headline, description and snippet as short passages (the article body is added later for the top results)."""
    if not a.url or not a.title:
        return []
    tier = credibility.tier_for(a.url)
    label = f"{a.source} ({a.published})" if a.published else a.source
    texts = [a.title.strip()]
    for body in (a.description, a.content):
        texts += live.intro_sentences(body)
    return [
        live.Item(doc_id=live.doc_id_for(a.url), title=a.title.strip(), url=a.url, source=label, text=t, kind="news",
                  published=a.published, tier=tier, prior=credibility.PRIOR[tier])
        for t in texts
    ]


def factcheck_items(fc: providers.FactCheck) -> list[live.Item]:
    if not fc.url or not (fc.rating or fc.title):
        return []
    claim = f' the claim "{fc.claim.strip()}"' if fc.claim else " a related claim"
    verdict = f"rated{claim} as: {fc.rating}." if fc.rating else f"reviewed{claim}."
    texts = [f"{fc.publisher or 'A fact-checker'} {verdict}"]
    if fc.title:
        texts.append(fc.title.strip())
    return [
        live.Item(doc_id=live.doc_id_for(fc.url), title=fc.title or f"{fc.publisher} fact-check", url=fc.url,
                  source=f"{fc.publisher or 'fact-check'} ({fc.published})" if fc.published else (fc.publisher or "fact-check"),
                  text=t, kind="fact-check", published=fc.published, tier=credibility.TIER_FACTCHECK, rating=fc.rating,
                  prior=FACTCHECK_PRIOR)
        for t in texts
    ]


def body_items(base: live.Item, text: str) -> list[live.Item]:
    sents = [s for s in sent_tokenize(" ".join(text.split())) if len(s.split()) >= 5][:MAX_BODY_SENTENCES]
    return [
        live.Item(doc_id=base.doc_id, title=base.title, url=base.url, source=base.source, text=s, kind=base.kind,
                  published=base.published, tier=base.tier, prior=base.prior)
        for s in sents
    ]


def _unique(articles: list[providers.Article]) -> list[providers.Article]:
    out, seen = [], set()
    for a in articles:
        k = _norm_title(a.title)
        if a.url and k and k not in seen:
            seen.add(k)
            out.append(a)
    return out


def _search_news(plan: planner.Plan, notes: list[str]) -> list[providers.Article]:
    """GNews first: the main query, and a second differently-worded one only if the first found few articles (each request
    costs quota). NewsAPI only when GNews is absent or still short."""
    conf = providers.configured()
    articles: list[providers.Article] = []
    if conf["gnews"]:
        for q in plan.queries[:2]:
            try:
                articles += providers.gnews(q, plan.country)
            except providers.ProviderError as exc:
                notes.append(str(exc))
                break
            if len(_unique(articles)) >= ENOUGH_ARTICLES:
                break
    if conf["newsapi"] and len(_unique(articles)) < 3:
        try:
            articles += providers.newsapi(plan.queries[0])
        except providers.ProviderError as exc:
            notes.append(str(exc))
    return _unique(articles)


def gather(
    res: hybrid.Resources, claim: str, entities: list[str], keyword_query: str, *, k: int = 8, project: bool = True,
    use_llm: bool = True,
) -> RetrievalOut:
    conf = providers.configured()
    notes: list[str] = []
    timings: dict[str, float] = {}

    t0 = time.perf_counter()
    plan = planner.make_plan(claim, entities, keyword_query, use_llm=use_llm)
    notes += plan.notes
    timings["plan"] = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=3) as pool:
        news_f = pool.submit(_search_news, plan, notes) if (conf["gnews"] or conf["newsapi"]) else None
        fc_f = (pool.submit(lambda: [fc for q in dict.fromkeys([claim[:200], plan.queries[0]]) for fc in providers.factchecks(q)])
                if conf["factcheck"] else None)
        wiki_f = pool.submit(live.wikipedia_items, claim, entities) if conf["wikipedia"] else None
        articles = news_f.result() if news_f else []
        checks: list[providers.FactCheck] = []
        if fc_f:
            try:
                checks = fc_f.result()
            except providers.ProviderError as exc:
                notes.append(str(exc))
        wiki: list[live.Item] = []
        if wiki_f:
            try:
                wiki = wiki_f.result()
            except RuntimeError as exc:
                notes.append(str(exc))
    timings["search"] = (time.perf_counter() - t0) * 1000

    items: list[live.Item] = [it for a in articles for it in article_items(a)]
    items += [it for fc in checks for it in factcheck_items(fc)]
    for it in wiki:
        it.prior = BACKGROUND_PRIOR
    items = live.dedupe_items(items + wiki)
    if not items:
        raise RuntimeError(
            "No evidence found. " + (" ".join(dict.fromkeys(notes)) + " " if notes else "") +
            "Try rephrasing the claim, or check the keys in backend/.env (see the Pipeline tab)."
        )

    # Download the full text of the most relevant articles: snippets rarely contain the facts.
    t0 = time.perf_counter()
    cache: dict = {}  # passage embeddings are computed once and reused by the final ranking
    scores, _, _ = live.score_items(res, claim, entities, items, cache=cache)
    news_items = [it for it in items if it.kind == "news"]
    best_live = max((float(sc) for it, sc in zip(items, scores) if it.kind in ("news", "fact-check")), default=0.0)
    if news_items and FETCH_TOP > 0:
        best: dict[str, float] = {}
        for it, sc in zip(items, scores):
            if it.kind == "news":
                best[it.doc_id] = max(best.get(it.doc_id, -9.0), float(sc))
        top_docs = sorted(best, key=lambda d: -best[d])[:FETCH_TOP]
        base_of = {it.doc_id: it for it in news_items}
        pool = ThreadPoolExecutor(max_workers=FETCH_TOP)
        futs = [pool.submit(fetch.fetch_article, base_of[d].url) for d in top_docs]
        wait(futs, timeout=FETCH_DEADLINE_S)
        texts = [f.result() if f.done() and not f.exception() else "" for f in futs]
        pool.shutdown(wait=False, cancel_futures=True)
        fetched = 0
        for d, text in zip(top_docs, texts):
            if text:
                fetched += 1
                items += body_items(base_of[d], text)
        if fetched < len(top_docs):
            notes.append(f"Full text could not be read for {len(top_docs) - fetched} of the top {len(top_docs)} articles "
                         "(paywall or blocked); their headline and snippet were used.")
    timings["fetch"] = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    background_cap = MAX_BACKGROUND_PASSAGES if best_live >= NEWS_RELEVANT_MIN else MAX_BACKGROUND_WHEN_NEWS_OFF_TOPIC
    out = live.rank_items(res, claim, entities, items, k_sentences=k, project=project,
                          max_per_kind={"background": background_cap}, cache=cache)
    timings["rank"] = (time.perf_counter() - t0) * 1000

    if not articles and not checks and not conf["gnews"] and not conf["newsapi"]:
        notes.append("No news provider is configured, so only Wikipedia background was used.")
    elif not articles and (conf["gnews"] or conf["newsapi"]):
        notes.append("No recent news articles matched this claim; the evidence below is fact-checks or background only.")
    out.queries, out.notes = plan.queries, list(dict.fromkeys(notes))
    out.timings_ms = {k_: round(v, 1) for k_, v in timings.items()}
    return out


def available() -> bool:
    """True when at least one live evidence source is configured."""
    c = providers.configured()
    return c["gnews"] or c["newsapi"] or c["factcheck"]
