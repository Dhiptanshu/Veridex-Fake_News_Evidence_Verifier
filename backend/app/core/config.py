from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="FNEV_", env_file=(str(BACKEND_DIR / ".env"), ".env"), extra="ignore"  # backend/.env wherever the API starts
    )

    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    # Artificial per-stage latency for placeholder stages, so the UI streaming is visible.
    placeholder_delay_s: float = 0.45
    # Wikimedia's API policy requires contact details in the User-Agent. Live Wikipedia search stays off until you set
    # FNEV_WIKIPEDIA_CONTACT to an email address or a URL of yours.
    wikipedia_contact: str = ""
    google_factcheck_key: str = ""  # Google Fact Check Tools API (optional): https://developers.google.com/fact-check/tools/api
    # News evidence (optional). Keys come from the provider's dashboard; see .env.example. Empty = feature off.
    gnews_api_key: str = ""
    newsapi_key: str = ""
    # Follow-up answers from an LLM through AICredits (optional, OpenAI-compatible API). Without a key the local
    # extractive answerer is used. Model ids look like "openai/gpt-4o-mini" or "anthropic/claude-sonnet-4.6".
    aicredits_api_key: str = ""
    aicredits_base_url: str = "https://api.aicredits.in/v1"
    aicredits_model: str = "openai/gpt-4o-mini"
    aicredits_judge_model: str = ""  # model for verdicts; empty = same as aicredits_model. A stronger one judges better.


settings = Settings()
