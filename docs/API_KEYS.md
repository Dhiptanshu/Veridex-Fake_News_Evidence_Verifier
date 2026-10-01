# API keys and optional services

Everything below is **optional**. The core app (offline retrieval, verification, explanation) needs no key and no internet
once the data and models are built. Each key only switches on one extra feature.

## Where to put keys

1. Copy `backend/.env.example` to `backend/.env` (the `.env` file is gitignored, so keys never reach git).
2. Fill in only the lines you want.
3. Restart the API (`uvicorn app.main:app` from the `backend` folder). Settings are read once at startup.

```bash
FNEV_WIKIPEDIA_CONTACT=you@example.com        # or a URL; see below
FNEV_GNEWS_API_KEY=your-gnews-key
FNEV_NEWSAPI_KEY=your-newsapi-key              # only if you do not use GNews
FNEV_ANTHROPIC_API_KEY=your-anthropic-key
```

Never paste a key into a chat, an issue or a commit. If one leaks, delete it in the provider's dashboard and make a new one.
With Docker, put the same variables in a `.env` file next to `docker-compose.yml`; compose passes all four through.
(Docker support is untested; see the README.)

## What each one enables

| Setting | Feature in the UI | Needs a key? | Where to get it |
|---|---|---|---|
| `FNEV_WIKIPEDIA_CONTACT` | Retrieval option **Live Wikipedia search** | No key, but Wikimedia requires contact details in the User-Agent | Use your own email or a URL. Policy: https://www.mediawiki.org/wiki/API:Etiquette |
| `FNEV_GNEWS_API_KEY` | Retrieval options **Live news search** and **Live Wikipedia + news** | Yes | Register at https://gnews.io/register, confirm your email, and the key is on your dashboard. No credit card. |
| `FNEV_NEWSAPI_KEY` | Same as above (used if no GNews key) | Yes | https://newsapi.org/register ; plans: https://newsapi.org/pricing |
| `FNEV_ANTHROPIC_API_KEY` | **Ask about this result** answers written by Claude instead of the local model | Yes, and usage is billed | Console: https://platform.claude.com ; create a key at https://platform.claude.com/settings/keys ; docs: https://platform.claude.com/docs/en/api/overview |
| `FNEV_ANTHROPIC_MODEL` | Which Claude model answers (default `claude-haiku-4-5-20251001`) | n/a | Model list: https://platform.claude.com/docs/en/about-claude/models |

Without a key the feature stays off and the UI shows a message saying exactly which setting is missing.

## Free-tier limits (checked while writing this; confirm on the sign-up page)

* **GNews free:** 100 requests/day, up to 10 articles per request, 12-hour delay, last 30 days only, truncated article text,
  non-commercial use only. Docs: https://docs.gnews.io/
* **NewsAPI Developer:** 100 requests/day, 24-hour delay, up to 1 month back, article text cut to about 200 characters,
  "for development and testing" only. Docs: https://newsapi.org/docs/endpoints/everything
* **Claude API:** billed by usage; check your Billing page for credits and set a spend limit in the Console.
* **Wikipedia API:** no key and no hard daily cap for polite use; keep requests modest.

Each verification run in a live mode uses 1 news request, so 100 requests/day is plenty for a demo but not for batch tests.

## What gets sent where (privacy)

* **Live Wikipedia:** the claim and its entity names go to en.wikipedia.org as search queries.
* **News:** the claim's keywords go to GNews or NewsAPI.
* **Claude mode:** your question, the claim, the verdict and the evidence passages shown on screen go to the Anthropic API.
  The default **Local model** answerer sends nothing anywhere; choose it in the "Ask" panel if the claim is sensitive.

## Quality caveats for live modes

The verifier was trained on Wikipedia claims and evidence. News headlines and snippets are short and written differently, so
verdicts based on news evidence are **less reliable** than offline ones. Treat them as a demonstration.
