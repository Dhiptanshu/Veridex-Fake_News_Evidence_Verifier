import httpx
import pytest

from app.core.config import settings
from app.evidence import credibility, engine, fetch, planner, providers
from app.llm import client
from app.pipeline.orchestrator import run_pipeline
from app.retrieval import hybrid
from app.schemas.pipeline import VerifyRequest


# ---- credibility ----------------------------------------------------------------------------------------------
@pytest.mark.parametrize("url,tier", [
    ("https://www.thehindu.com/news/national/x/article1.ece", credibility.TIER_NATIONAL),
    ("https://www.reuters.com/world/india/x", credibility.TIER_WIRE),
    ("https://www.reuters.com/fact-check/some-claim", credibility.TIER_FACTCHECK),
    ("https://www.altnews.in/some-claim/", credibility.TIER_FACTCHECK),
    ("https://random-blog.example.com/post", credibility.TIER_UNRATED),
    ("https://evil-thehindu.com.example.org/x", credibility.TIER_UNRATED),  # suffix tricks do not inherit trust
    ("not a url", credibility.TIER_UNRATED),
])
def test_source_tiers(url, tier):
    assert credibility.tier_for(url) == tier


# ---- planner --------------------------------------------------------------------------------------------------
def test_india_hint_and_short_unquoted_fallback_queries():
    q = planner.fallback_queries("PM Modi announced a new GST rate for Indian railways on Tuesday.", ["Modi", "GST"], "modi gst rate railways")
    assert 1 <= len(q) <= 3 and all(len(x.split()) <= planner.MAX_QUERY_WORDS and '"' not in x for x in q)
    assert q[0].startswith("Modi GST")
    assert planner.india_related("Virat Kohli scored a century in the IPL")
    assert not planner.india_related("Paris is the capital of France")


def test_llm_plan_is_merged_with_rules_and_sets_country(monkeypatch):
    monkeypatch.setattr(settings, "aicredits_api_key", "sk-test")
    monkeypatch.setattr(client, "chat_json", lambda *a, **k: {"queries": ["Modi GST railways", "GST rate cut railway tickets"], "country": "in"})
    p = planner.make_plan("PM Modi cut GST on railway tickets.", ["Modi"], "modi gst")
    assert p.used_llm and p.country == "in" and p.queries[0] == "Modi GST railways" and len(p.queries) <= planner.MAX_QUERIES


def test_planner_failure_falls_back_to_rules_with_a_note(monkeypatch):
    monkeypatch.setattr(settings, "aicredits_api_key", "sk-test")

    def boom(*a, **k):
        raise client.LLMError("AICredits rate limit hit")

    monkeypatch.setattr(client, "chat_json", boom)
    p = planner.make_plan("Marie Curie won two Nobel Prizes.", ["Marie Curie"], "marie curie nobel")
    assert not p.used_llm and p.queries and "fell back to rules" in p.notes[0]


# ---- providers ------------------------------------------------------------------------------------------------
def test_gnews_request_shape_country_and_cache(monkeypatch):
    monkeypatch.setattr(settings, "gnews_api_key", "KEY")
    calls = []

    def fake(name, url, params, headers=None):
        calls.append(params)
        return {"articles": [{"title": "T", "description": "D", "content": "C... [1200 chars]", "url": "https://a/b",
                              "publishedAt": "2026-09-30T10:00:00Z", "source": {"name": "ThePrint"}}]}

    monkeypatch.setattr(providers, "_get", fake)
    a = providers.gnews("modi gst", "in")
    providers.gnews("modi gst", "in")  # identical query: served from cache, no second request
    assert len(calls) == 1 and calls[0]["country"] == "in" and calls[0]["apikey"] == "KEY"
    assert a[0].content == "C" and a[0].published == "2026-09-30" and a[0].source == "ThePrint"


def test_factcheck_parsing(monkeypatch):
    monkeypatch.setattr(settings, "google_factcheck_key", "KEY")
    monkeypatch.setattr(providers, "_get", lambda *a, **k: {"claims": [{
        "text": "Water cures cancer", "claimant": "viral post", "claimDate": "2026-08-01",
        "claimReview": [{"publisher": {"name": "BOOM"}, "url": "https://boomlive.in/x", "title": "No, water does not cure cancer",
                         "textualRating": "False", "reviewDate": "2026-08-03T00:00:00Z"}]}]})
    fc = providers.factchecks("water cancer")[0]
    assert (fc.publisher, fc.rating, fc.published) == ("BOOM", "False", "2026-08-03")


def test_missing_keys_and_http_errors_raise_readable_provider_errors(monkeypatch):
    with pytest.raises(providers.ProviderError, match="no key"):
        providers.gnews("x")

    class R:
        def __init__(self, code):
            self.status_code = code

        def json(self):
            return {}

    for code, text in [(403, "key was rejected"), (429, "daily request limit"), (500, "HTTP 500")]:
        providers.clear_cache()  # a 429 is remembered for the day, so reset between cases
        monkeypatch.setattr(providers.httpx, "get", lambda *a, _c=code, **k: R(_c))
        with pytest.raises(providers.ProviderError, match=text):
            providers._get("GNews", "https://x", {})

    def conn(*a, **k):
        raise httpx.ConnectError("x")

    monkeypatch.setattr(providers.httpx, "get", conn)
    with pytest.raises(providers.ProviderError, match="could not connect"):
        providers._get("GNews", "https://x", {})


# ---- fetch ----------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("url", ["http://localhost/x", "http://127.0.0.1:8000/", "http://192.168.1.5/a", "ftp://example.com/f", "file:///etc/passwd", "http://[::1]/"])
def test_private_and_non_http_urls_are_refused(url):
    assert fetch.is_public_url(url) is False
    assert fetch.fetch_article(url) == ""


def test_extract_text_returns_main_content():
    html = "<html><body><nav>menu menu</nav><article><h1>Title</h1>" + "<p>The minister announced a new policy on Tuesday in Delhi. </p>" * 8 + "</article></body></html>"
    assert "announced a new policy" in fetch.extract_text(html)


# ---- engine ---------------------------------------------------------------------------------------------------
def art(title, url, src="ThePrint", desc=""):
    return providers.Article(title, desc, "", url, src, "2026-09-30")


@pytest.fixture()
def live_setup(monkeypatch, tiny_resources):
    monkeypatch.setattr(settings, "gnews_api_key", "KEY")
    monkeypatch.setattr(settings, "google_factcheck_key", "KEY")
    monkeypatch.setattr(fetch, "fetch_article", lambda url, max_chars=6000: "")
    monkeypatch.setattr(planner, "make_plan", lambda *a, **k: planner.Plan(queries=["marie curie nobel"], country=None))
    return monkeypatch


def test_gather_combines_news_and_factchecks_and_ranks_by_relevance(live_setup):
    live_setup.setattr(providers, "gnews", lambda q, country=None, limit=10: [
        art("Marie Curie won two Nobel Prizes, historians recall", "https://www.thehindu.com/a", "The Hindu", "Curie won in Physics and Chemistry."),
        art("Weather turns cold in the region", "https://news.example/weather", "Example", "Temperatures fall this week."),
    ])
    live_setup.setattr(providers, "factchecks", lambda q, limit=8: [providers.FactCheck(
        "Marie Curie won two Nobel Prizes", "viral", "BOOM", "Yes, Curie won two Nobels", "https://boomlive.in/curie", "True", "2026-09-01")])
    out = engine.gather(hybrid.get_resources(), "Marie Curie won two Nobel Prizes", ["Marie Curie"], "marie curie nobel", project=False)
    assert {"news", "fact-check"} <= {e.kind for e in out.evidence}
    fc = next(e for e in out.evidence if e.kind == "fact-check")
    assert fc.rating == "True" and fc.tier == credibility.TIER_FACTCHECK and fc.url == "https://boomlive.in/curie"
    assert out.queries == ["marie curie nobel"]
    assert "weather" not in out.evidence[0].title.lower()


def test_one_failing_provider_does_not_kill_the_run(live_setup):
    live_setup.setattr(providers, "gnews", lambda q, country=None, limit=10: [art("Marie Curie Nobel Prize story today", "https://www.thehindu.com/a", "The Hindu", "Curie won two Nobel Prizes.")])

    def fail(q, limit=8):
        raise providers.ProviderError("Google Fact Check: daily request limit reached")

    live_setup.setattr(providers, "factchecks", fail)
    out = engine.gather(hybrid.get_resources(), "Marie Curie won two Nobel Prizes", ["Marie Curie"], "marie curie", project=False)
    assert out.evidence and any("daily request limit" in n for n in out.notes)


def test_article_bodies_are_fetched_for_top_results_and_failures_are_noted(live_setup):
    live_setup.setattr(settings, "google_factcheck_key", "")
    live_setup.setattr(providers, "gnews", lambda q, country=None, limit=10: [
        art("Marie Curie Nobel honours", "https://www.thehindu.com/a", "The Hindu", "A short note."),
        art("Curie biography feature", "https://www.indianexpress.com/b", "Indian Express", "Another note."),
    ])
    live_setup.setattr(fetch, "fetch_article", lambda url, max_chars=6000: (
        "Marie Curie won the Nobel Prize in Physics in 1903. She won a second Nobel Prize in Chemistry in 1911." if "thehindu" in url else ""))
    out = engine.gather(hybrid.get_resources(), "Marie Curie won two Nobel Prizes", ["Marie Curie"], "marie curie", project=False)
    texts = " ".join(s.text for e in out.evidence for s in e.sentences)
    assert "second Nobel Prize in Chemistry in 1911" in texts
    assert any("Full text could not be read for 1 of the top 2" in n for n in out.notes)


def test_newsapi_is_only_used_when_gnews_comes_up_short(live_setup):
    live_setup.setattr(settings, "newsapi_key", "K2")
    live_setup.setattr(settings, "google_factcheck_key", "")
    called = []
    many = [art(f"Distinct headline number {i} about Curie", f"https://n/{i}") for i in range(4)]
    live_setup.setattr(providers, "gnews", lambda q, country=None, limit=10: many)
    live_setup.setattr(providers, "newsapi", lambda q, limit=10: called.append(q) or [])
    engine.gather(hybrid.get_resources(), "Curie Nobel", ["Curie"], "curie", project=False)
    assert called == []
    live_setup.setattr(providers, "gnews", lambda q, country=None, limit=10: many[:1])
    engine.gather(hybrid.get_resources(), "Curie Nobel", ["Curie"], "curie", project=False)
    assert called == ["marie curie nobel"]


def test_second_gnews_query_is_only_sent_when_the_first_found_few_articles(live_setup):
    live_setup.setattr(settings, "google_factcheck_key", "")
    live_setup.setattr(planner, "make_plan", lambda *a, **k: planner.Plan(queries=["q one", "q two", "q three"], country="in"))
    sent = []
    many = [art(f"Distinct headline number {i} about Curie", f"https://n/{i}") for i in range(6)]
    live_setup.setattr(providers, "gnews", lambda q, country=None, limit=10: sent.append((q, country)) or many)
    engine.gather(hybrid.get_resources(), "Curie Nobel", ["Curie"], "curie", project=False)
    assert sent == [("q one", "in")]  # enough articles: quota saved
    sent.clear()
    live_setup.setattr(providers, "gnews", lambda q, country=None, limit=10: sent.append((q, country)) or many[:1])
    engine.gather(hybrid.get_resources(), "Curie Nobel", ["Curie"], "curie", project=False)
    assert [q for q, _ in sent] == ["q one", "q two"]  # never more than two requests per run


def test_daily_limit_is_remembered_so_no_more_requests_are_wasted(monkeypatch):
    monkeypatch.setattr(settings, "gnews_api_key", "KEY")
    n = []

    class R:
        status_code = 429

        def json(self):
            return {}

    monkeypatch.setattr(providers.httpx, "get", lambda *a, **k: n.append(1) or R())
    for _ in range(3):
        with pytest.raises(providers.ProviderError, match="daily request limit"):
            providers._get("GNews", "https://x", {})
    assert len(n) == 1


def test_wikipedia_background_is_capped_and_timings_are_reported(live_setup):
    from app.retrieval import live as live_mod

    live_setup.setattr(settings, "wikipedia_contact", "me@example.org")
    live_setup.setattr(settings, "google_factcheck_key", "")
    live_setup.setattr(providers, "gnews", lambda q, country=None, limit=10: [art("Curie headline about Nobel", "https://www.thehindu.com/a", "The Hindu", "Curie won prizes.")])
    wiki = [live_mod.Item(doc_id="Marie_Curie", title="Marie Curie", url="https://en.wikipedia.org/wiki/Marie_Curie", source="wikipedia (live)",
                          text=f"Marie Curie won Nobel Prize number {i} in physics and chemistry.", kind="background") for i in range(6)]
    live_setup.setattr(live_mod, "wikipedia_items", lambda c, e: wiki)
    out = engine.gather(hybrid.get_resources(), "Marie Curie won Nobel Prize", ["Marie Curie"], "curie", project=False)
    n_bg = sum(len(e.sentences) for e in out.evidence if e.kind == "background")
    assert 0 < n_bg <= engine.MAX_BACKGROUND_PASSAGES
    assert set(out.timings_ms) == {"plan", "search", "fetch", "rank"}


def test_no_evidence_raises_an_actionable_error(live_setup):
    live_setup.setattr(providers, "gnews", lambda q, country=None, limit=10: [])
    live_setup.setattr(providers, "factchecks", lambda q, limit=8: [])
    with pytest.raises(RuntimeError, match="No evidence found"):
        engine.gather(hybrid.get_resources(), "Obscure claim", [], "obscure", project=False)


async def test_default_retrieval_falls_back_to_offline_wikipedia_without_keys(tiny_resources):
    events = [e async for e in run_pipeline(VerifyRequest(claim="Marie Curie won two Nobel Prizes."))]
    assert events[-1].type == "pipeline_end"
    ret = next(e for e in events if e.type == "stage_end" and e.slot == "retrieval")
    assert ret.impl == "news_first" and any("offline Wikipedia subset" in n for n in ret.payload["notes"])
    assert ret.payload["evidence"][0]["kind"] == "wikipedia"
