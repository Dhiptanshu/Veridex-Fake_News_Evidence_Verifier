"""Source credibility tiers, from a small curated table. Unknown domains are "unrated": shown as such, never trusted by default.

This is editorial judgement, not ground truth. Tiers are shown to the user and given to the judge as context.
"""
from urllib.parse import urlparse

TIER_FACTCHECK = "fact-checker"
TIER_WIRE = "wire / major"
TIER_NATIONAL = "established"
TIER_UNRATED = "unrated"

_FACTCHECK = {
    "factcheck.pib.gov.in", "altnews.in", "boomlive.in", "factly.in", "thequint.com/webqoof", "vishvasnews.com", "newschecker.in",
    "factchecker.in", "afp.com", "factcheck.afp.com", "snopes.com", "politifact.com", "factcheck.org", "fullfact.org",
    "reuters.com/fact-check", "apnews.com/hub/ap-fact-check", "logically.ai", "newsmeter.in", "dfrac.org", "thehindu.com/fact-check",
}
_WIRE = {
    "reuters.com", "apnews.com", "bbc.com", "bbc.co.uk", "ptinews.com", "aninews.in", "bloomberg.com", "afp.com", "pib.gov.in",
    "nytimes.com", "theguardian.com", "washingtonpost.com", "aljazeera.com", "npr.org", "france24.com", "dw.com",
}
_ESTABLISHED = {
    "thehindu.com", "indianexpress.com", "timesofindia.indiatimes.com", "hindustantimes.com", "ndtv.com", "theprint.in",
    "economictimes.indiatimes.com", "livemint.com", "business-standard.com", "financialexpress.com", "scroll.in", "thewire.in",
    "deccanherald.com", "telegraphindia.com", "news18.com", "indiatoday.in", "firstpost.com", "thenewsminute.com", "mid-day.com",
    "tribuneindia.com", "outlookindia.com", "frontline.thehindu.com", "wionews.com", "cnbctv18.com", "moneycontrol.com",
    "espncricinfo.com", "thehindubusinessline.com", "hurriyetdailynews.com", "dnaindia.com", "oneindia.com", "newindianexpress.com", "freepressjournal.in", "devdiscourse.com", "ians.in", "theweek.in", "indiatvnews.com", "abplive.com", "zeenews.india.com", "navbharattimes.indiatimes.com", "jagran.com", "bhaskar.com", "amarujala.com", "cricbuzz.com", "cnn.com", "cnbc.com", "forbes.com", "time.com", "economist.com", "ft.com", "wsj.com",
    "abcnews.go.com", "cbsnews.com", "nbcnews.com", "sky.com", "independent.co.uk", "telegraph.co.uk", "theatlantic.com",
}


def host_of(url: str) -> str:
    try:
        host = (urlparse(url).hostname or "").lower()
    except ValueError:
        return ""
    return host[4:] if host.startswith("www.") else host


def _matches(host: str, path: str, table: set[str]) -> bool:
    for entry in table:
        d, _, p = entry.partition("/")
        if (host == d or host.endswith("." + d)) and (not p or path.startswith("/" + p)):
            return True
    return False


def tier_for(url: str) -> str:
    host, path = host_of(url), (urlparse(url).path or "").lower() if url else ""
    if not host:
        return TIER_UNRATED
    if _matches(host, path, _FACTCHECK):
        return TIER_FACTCHECK
    if _matches(host, path, _WIRE):
        return TIER_WIRE
    if _matches(host, path, _ESTABLISHED):
        return TIER_NATIONAL
    return TIER_UNRATED


# additive ranking prior: small, so relevance still dominates
PRIOR = {TIER_FACTCHECK: 0.06, TIER_WIRE: 0.04, TIER_NATIONAL: 0.02, TIER_UNRATED: 0.0}
