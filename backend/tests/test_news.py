import pytest

from app.core.config import settings
from app.pipeline.orchestrator import run_pipeline
from app.retrieval import hybrid, live, news
from app.schemas.pipeline import VerifyRequest

GNEWS = {"articles": [
    {"title": "Marie Curie honoured with new stamp", "description": "A new stamp celebrates Marie Curie, who won two Nobel Prizes.",
     "content": "The post office said the stamp marks her work on radioactivity. She won the Nobel Prize in Physics in 1903... [1234 chars]",
     "url": "https://news.example/curie", "publishedAt": "2026-09-01T10:00:00Z", "source": {"name": "Example News"}},
    {"title": "Weather turns cold", "description": "Temperatures fall across the region this week.", "content": None,
     "url": "https://news.example/weather", "publishedAt": "2026-09-02T10:00:00Z", "source": {"name": "Example News"}},
]}


@pytest.fixture()
def keys(monkeypatch):
    monkeypatch.setattr(settings, "gnews_api_key", "test-key")
    monkeypatch.setattr(settings, "newsapi_key", "")
    monkeypatch.setattr(settings, "wikipedia_contact", "")
    seen = []

    def fake(url, *, params, headers=None):
        seen.append((url, params, headers))
        return GNEWS

    monkeypatch.setattr(news, "_get_json", fake)
    return seen


def test_provider_prefers_gnews_then_newsapi(monkeypatch):
    monkeypatch.setattr(settings, "gnews_api_key", "")
    monkeypatch.setattr(settings, "newsapi_key", "")
    assert news.provider() is None
    monkeypatch.setattr(settings, "newsapi_key", "k")
    assert news.provider() == "newsapi"
    monkeypatch.setattr(settings, "gnews_api_key", "k2")
    assert news.provider() == "gnews"


def test_search_refuses_without_a_key_and_names_where_to_get_one(monkeypatch):
    monkeypatch.setattr(settings, "gnews_api_key", "")
    monkeypatch.setattr(settings, "newsapi_key", "")
    with pytest.raises(RuntimeError, match="gnews.io/register"):
        news.search("anything")


def test_requests_use_each_providers_documented_shape(monkeypatch):
    calls = []
    monkeypatch.setattr(news, "_get_json", lambda url, *, params, headers=None: calls.append((url, params, headers)) or {"articles": []})
    news.search_gnews("marie curie", "KEY")
    news.search_newsapi("marie curie", "KEY2")
    (g_url, g_params, g_headers), (n_url, n_params, n_headers) = calls
    assert g_url == "https://gnews.io/api/v4/search" and g_params["apikey"] == "KEY" and g_params["lang"] == "en" and not g_headers
    assert n_url == "https://newsapi.org/v2/everything" and n_headers == {"X-Api-Key": "KEY2"} and "apikey" not in n_params


def test_http_errors_become_actionable_messages(monkeypatch):
    class R:
        def __init__(self, code): self.status_code = code
        def raise_for_status(self): pass
        def json(self): return {}

    for code, text in [(401, "rejected the key"), (429, "limit is used up")]:
        monkeypatch.setattr(news.httpx, "get", lambda *a, _c=code, **k: R(_c))
        with pytest.raises(RuntimeError, match=text):
            news._get_json("https://x", params={})


def test_article_items_strip_truncation_markers_and_duplicates():
    a = news.Article("Headline here today", "Headline here today", "Body sentence is long enough here... [1234 chars]", "https://n/a", "Src", "2026-09-01")
    texts = [it.text for it in news.article_items(a)]
    assert texts.count("Headline here today") == 1 and not any("chars]" in t for t in texts)
    assert news.article_items(news.Article("", "x y z w", "", "", "S", "")) == []


def test_news_search_ranks_the_relevant_article_first(tiny_resources, keys):
    out = news.news_search(hybrid.get_resources(), "Marie Curie won two Nobel Prizes", ["Marie Curie"], "Marie Curie Nobel", project=False)
    assert out.evidence[0].url == "https://news.example/curie"
    assert out.evidence[0].source == "Example News (2026-09-01)"
    assert keys[0][1]["apikey"] == "test-key"


async def test_pipeline_runs_end_to_end_in_news_mode(tiny_resources, keys):
    events = [e async for e in run_pipeline(VerifyRequest(claim="Marie Curie won two Nobel Prizes.", options={"retrieval": "live_news"}))]
    assert events[-1].type == "pipeline_end"
    assert next(e for e in events if e.type == "stage_end" and e.slot == "retrieval").payload["evidence"][0]["url"].startswith("https://news.example")


def test_candidate_queries_are_short_entity_phrases_then_a_few_keywords():
    q = news.candidate_queries("Eiffel Tower 1889 complete tower built", ["the Eiffel Tower", "1889", "Paris"])
    assert q == ['"Eiffel Tower" "Paris"', "Eiffel Tower 1889 complete"]
    assert news.candidate_queries("", []) == []
    assert news.candidate_queries("alpha beta", ["12 May 2020"]) == ["alpha beta"]  # dates are not entities worth searching


def test_news_items_falls_back_to_the_next_query_only_when_the_first_finds_nothing(monkeypatch):
    calls = []

    def fake(query):
        calls.append(query)
        return [] if len(calls) == 1 else [news.Article("Headline of the story", "A description of the story here.", "", "https://n/1", "Src", "2026-09-01")]

    monkeypatch.setattr(news, "search", fake)
    assert news.news_items(["first", "second"]) and calls == ["first", "second"]
    calls.clear()
    monkeypatch.setattr(news, "search", lambda q: calls.append(q) or [news.Article("Another headline here", "Some description of it.", "", "https://n/2", "S", "")])
    news.news_items(["first", "second"])
    assert calls == ["first"]  # no wasted request


def test_no_matching_articles_gives_an_actionable_error(tiny_resources, keys, monkeypatch):
    monkeypatch.setattr(news, "search", lambda q: [])
    with pytest.raises(RuntimeError, match="Try Live Wikipedia"):
        news.news_search(hybrid.get_resources(), "Some claim here", ["Entity"], "keywords here")


def test_combined_search_uses_only_what_is_configured(tiny_resources, keys, monkeypatch):
    called = []
    monkeypatch.setattr(live, "wikipedia_items", lambda c, e: called.append("wiki") or [])
    news.combined_search(hybrid.get_resources(), "Marie Curie won two Nobel Prizes", ["Marie Curie"], "Marie Curie", project=False)
    assert called == []  # no Wikipedia contact configured, so Wikipedia is skipped
    monkeypatch.setattr(settings, "gnews_api_key", "")
    with pytest.raises(RuntimeError, match="Nothing is configured"):
        news.combined_search(hybrid.get_resources(), "x y z", [], "x")


def test_identical_sentences_from_syndicated_copies_are_ranked_once(tiny_resources):
    items = [live.Item(doc_id=f"d{i}", title=f"Copy {i}", url=f"https://n/{i}", source="S", text="Marie Curie won two Nobel Prizes.") for i in range(3)]
    items.append(live.Item(doc_id="x", title="Other", url="https://n/x", source="S", text="Paris is the capital of France."))
    out = live.rank_items(hybrid.get_resources(), "Marie Curie won two Nobel Prizes", ["Marie Curie"], items, project=False)
    texts = [s.text for e in out.evidence for s in e.sentences]
    assert texts.count("Marie Curie won two Nobel Prizes.") == 1 and len(texts) == 2
