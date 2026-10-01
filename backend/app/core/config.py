from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FNEV_", env_file=".env", extra="ignore")

    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    # Artificial per-stage latency for placeholder stages, so the UI streaming is visible.
    placeholder_delay_s: float = 0.45
    # Wikimedia's API policy requires contact details in the User-Agent. Live Wikipedia search stays off until you set
    # FNEV_WIKIPEDIA_CONTACT to an email address or a URL of yours.
    wikipedia_contact: str = ""
    # News evidence (optional). Keys come from the provider's dashboard; see .env.example. Empty = feature off.
    gnews_api_key: str = ""
    newsapi_key: str = ""
    # Follow-up answers from Claude (optional). Without a key the local extractive answerer is used.
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-haiku-4-5-20251001"


settings = Settings()
