# API keys and optional services

The app works offline without any key (a Wikipedia-trained model on a fixed corpus), but it is built to work on **live news**.
Add the keys below to get the full experience: news + fact-check evidence, an LLM judge, and a chat assistant that can search.

## Where to put keys

1. Open **`backend/.env`** (it exists, with blank values; `backend/.env.example` is the template). It is gitignored, so keys never reach git.
2. Fill in the lines you want.
3. Restart the API (`uvicorn app.main:app` from the `backend` folder). Settings are read once at startup.

```bash
FNEV_GNEWS_API_KEY=your-gnews-key
FNEV_NEWSAPI_KEY=your-newsapi-key              # optional second news source
FNEV_GOOGLE_FACTCHECK_KEY=your-google-key      # fact-check sites (Alt News, BOOM, PIB Fact Check, AFP...)
FNEV_AICREDITS_API_KEY=sk-your-aicredits-key   # LLM judge, query planning and the assistant
FNEV_WIKIPEDIA_CONTACT=you@example.com         # Wikipedia background; an email or URL of yours
# FNEV_AICREDITS_JUDGE_MODEL=anthropic/claude-sonnet-4.6   # default; openai/gpt-4o-mini is cheaper
# FNEV_AICREDITS_MODEL=openai/gpt-4o-mini                  # planner + assistant
```

Never paste a key into a chat, an issue or a commit. If one leaks, delete it in the provider's dashboard and make a new one.
The **Pipeline** tab shows which services are configured (never the key values) and how to fix what is missing.

## What each one does

| Setting | Used for | Where to get it |
|---|---|---|
| `FNEV_GNEWS_API_KEY` | Main news search (supports `country=in` for India) | https://gnews.io/register (key on your dashboard, no card). Docs: https://docs.gnews.io/ |
| `FNEV_NEWSAPI_KEY` | Second news source, used when GNews finds few articles | https://newsapi.org/register ; plans: https://newsapi.org/pricing |
| `FNEV_GOOGLE_FACTCHECK_KEY` | Published fact-checks as the strongest evidence tier | Google Cloud console: create a project, enable **Fact Check Tools API**, create an API key. https://developers.google.com/fact-check/tools/api |
| `FNEV_AICREDITS_API_KEY` | LLM judge (verdicts), query planning, assistant chat with web search | https://aicredits.in ; API: https://aicredits.in/docs/api-reference |
| `FNEV_AICREDITS_JUDGE_MODEL` | Model that writes the verdict (default `anthropic/claude-sonnet-4.6`) | model ids are listed in the API reference |
| `FNEV_WIKIPEDIA_CONTACT` | Wikipedia background and the assistant's Wikipedia lookups | no key; Wikimedia requires contact details in the User-Agent: https://www.mediawiki.org/wiki/API:Etiquette |

Everything is optional and degrades gracefully: without news keys the offline Wikipedia subset is used; without an LLM key the
Wikipedia-trained BERT gives the verdict (with a visible warning that it is weak on news) and the chat falls back to a small local
question-answering box.

## How a live check uses them (and what it costs)

One verification run makes about: **1-2 GNews requests** (a second one only if the first finds fewer than 5 articles), **0-1 NewsAPI**
request, **1-2 Google Fact Check** requests, **2-4 Wikipedia** requests, **up to 3 article downloads**, and **2 LLM calls**
(query planning with the small model, the verdict with the judge model). The assistant adds one LLM call per message plus up to
four tool searches. Identical searches within an hour are served from a cache, and a "daily limit reached" reply is remembered so
no further requests are wasted that day.

## Free-tier limits (checked while writing; confirm on the sign-up page)

* **GNews free:** 100 requests/day, 10 articles per request, 12-hour delay, last 30 days, truncated article text, non-commercial use only.
* **NewsAPI Developer:** 100 requests/day, 24-hour delay, 1 month back, ~200-character content, development and testing only.
* **Google Fact Check Tools API:** free with a Google Cloud API key (generous quota).
* **AICredits:** pay-as-you-go from a wallet in INR; an empty wallet shows "insufficient credits" in the UI. The judge model is the main cost.
* **Wikipedia API:** no key; keep requests modest.

## What gets sent where (privacy)

* **News and fact-check search:** short search queries derived from your claim go to GNews / NewsAPI / Google.
* **Wikipedia:** the claim and entity names go to en.wikipedia.org.
* **Article download:** the app fetches the public article pages found by search (private and local addresses are refused).
* **LLM (AICredits, and on to the model provider):** your claim, the retrieved passages, and your chat messages.
* **Offline mode** (no keys) sends nothing anywhere.

## Caveats

* LLM verdicts can be wrong and their confidence is the model's own, not calibrated; always read the cited sources.
* Evidence only covers what the search APIs return (recent news, fact-checks that exist). "Not enough info" is a normal outcome.
* Source credibility tiers come from a small curated list (`backend/app/evidence/credibility.py`) and are editorial, not ground truth.
