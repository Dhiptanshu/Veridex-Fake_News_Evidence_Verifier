"""Turn a claim into a few search queries and a country hint.

News search engines match words, not meaning, and fail on long or over-quoted strings. An LLM (when configured) writes
2-3 short, differently worded queries; without one, a rule-based fallback builds them from entities and keywords.
"""
import re
import time
from dataclasses import dataclass, field

from app.llm import client

MAX_QUERIES = 3
MAX_QUERY_WORDS = 8

_INDIA = re.compile(
    r"\b(india|indian|indians|bharat|hindustan|modi|narendra modi|rahul gandhi|amit shah|kejriwal|delhi|mumbai|bengaluru|bangalore|"
    r"kolkata|chennai|hyderabad|kerala|punjab|gujarat|maharashtra|uttar pradesh|bjp|congress party|aap|lok sabha|rajya sabha|"
    r"supreme court of india|rbi|sebi|isro|drdo|ipl|bcci|rupee|rupees|crore|lakh|aadhaar|upi|pib|niti aayog|bollywood|kohli|"
    r"dhoni|sachin|rohit sharma)\b",
    re.I,
)
_STOP = {"the", "a", "an", "of", "in", "on", "at", "to", "for", "and", "or", "is", "are", "was", "were", "be", "been", "has", "have",
         "had", "that", "this", "it", "its", "with", "by", "from", "as", "will", "would", "not", "no"}


@dataclass
class Plan:
    queries: list[str]
    country: str | None = None  # ISO-3166 alpha-2 for the news API, or None for worldwide
    used_llm: bool = False
    notes: list[str] = field(default_factory=list)


def india_related(text: str) -> bool:
    return bool(_INDIA.search(text))


def _words(text: str) -> list[str]:
    return re.findall(r"[\w'’.-]+", text)


def fallback_queries(claim: str, entities: list[str], keyword_query: str) -> list[str]:
    """Unquoted, short queries: entity names first, then the claim's own content words."""
    ents = []
    for e in entities:
        e = re.sub(r"^(?:the|a|an)\s+", "", e.strip(), flags=re.I)
        if len(e) > 2 and re.search(r"[A-Za-z]", e) and e.lower() not in {x.lower() for x in ents}:
            ents.append(e)
    content = [w for w in _words(claim) if w.lower() not in _STOP]
    out = []
    if ents:
        out.append(" ".join(ents[:3] + [w for w in content if w.lower() not in " ".join(ents).lower()][:3]))
    out.append(" ".join(content[:MAX_QUERY_WORDS]))
    kw = " ".join(keyword_query.split()[:5])
    if kw:
        out.append(kw)
    cleaned = []
    for q in out:
        q = " ".join(q.split()[:MAX_QUERY_WORDS]).strip()
        if q and q.lower() not in {c.lower() for c in cleaned}:
            cleaned.append(q)
    return cleaned[:MAX_QUERIES]


PLANNER_SYSTEM = (
    "You write web news search queries for fact-checking. Given a claim, return ONLY JSON: "
    '{"queries": [2 or 3 short queries], "country": "<two-letter ISO code or null>"}. '
    "Queries: 3 to 7 keywords each, no quotes, no operators, no punctuation; the first names the main people/organisations and the "
    "event; the others use different wording or the likely headline phrasing (including common English spellings of Indian names). "
    'Set country to "in" only if the claim is mainly about India, otherwise null. '
    "NEVER add a year, month or date that is not in the claim, and do not guess outcomes: describe what to look for."
)


def make_plan(claim: str, entities: list[str], keyword_query: str, *, use_llm: bool = True) -> Plan:
    base = fallback_queries(claim, entities, keyword_query)
    country = "in" if india_related(claim) else None
    if use_llm and client.configured():
        try:
            data = client.chat_json(
                [{"role": "system", "content": PLANNER_SYSTEM}, {"role": "user", "content": f"Today is {time.strftime('%Y-%m-%d')}. Claim: {claim[:600]}"}],
                max_tokens=150, timeout=15,
            )
            qs = [" ".join(_words(str(q))[:MAX_QUERY_WORDS]) for q in (data.get("queries") or []) if isinstance(q, str)]
            qs = [q for q in qs if len(q) > 2]
            if qs:
                merged = list(dict.fromkeys([*qs, *base]))[:MAX_QUERIES]
                c = data.get("country")
                if isinstance(c, str) and re.fullmatch(r"[A-Za-z]{2}", c):
                    country = c.lower()
                return Plan(queries=merged, country=country, used_llm=True)
        except (client.LLMError, AttributeError, TypeError) as exc:
            return Plan(queries=base or [claim[:80]], country=country, notes=[f"Query planning fell back to rules: {exc}"])
    return Plan(queries=base or [" ".join(_words(claim)[:MAX_QUERY_WORDS])], country=country)
