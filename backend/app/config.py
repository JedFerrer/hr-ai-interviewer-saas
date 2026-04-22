"""Application settings loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite+aiosqlite:///./hr_interviewer.db"

    # Auth
    jwt_secret_key: str = "change-this-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 60  # short-lived access tokens; rotate via re-login
    # Account lockout
    max_failed_login_attempts: int = 5
    account_lockout_minutes: int = 15

    # Feature flags (default OFF — never enable in production)
    enable_test_emails: bool = False
    test_emails: str = ""  # comma-separated allowlist when enable_test_emails=True

    # Environment: "development" | "production"
    environment: str = "development"

    # LLM Provider: "openai", "deepseek", or "anthropic"
    llm_provider: str = "deepseek"
    llm_model: str = ""  # auto-detected from provider if blank
    openai_api_key: str = ""
    deepseek_api_key: str = ""
    anthropic_api_key: str = ""

    # Fallback order: comma-separated provider names tried after primary fails
    # e.g. "anthropic,openai" means: try primary → anthropic → openai
    llm_fallback_providers: str = ""

    @property
    def active_llm_api_key(self) -> str:
        return self._provider_config(self.llm_provider)["api_key"]

    @property
    def active_llm_model(self) -> str:
        if self.llm_model:
            return self.llm_model
        return self._provider_config(self.llm_provider)["model"]

    @property
    def active_llm_base_url(self) -> str | None:
        return self._provider_config(self.llm_provider).get("base_url")

    def _provider_config(self, provider: str) -> dict:
        """Return api_key, model, base_url for a given provider name."""
        providers = {
            "deepseek": {
                "api_key": self.deepseek_api_key,
                "model": "deepseek-chat",
                "base_url": "https://api.deepseek.com",
            },
            "openai": {
                "api_key": self.openai_api_key,
                "model": "gpt-4.1-mini",
                "base_url": None,
            },
            "anthropic": {
                "api_key": self.anthropic_api_key,
                "model": "claude-sonnet-4-20250514",
                "base_url": "https://api.anthropic.com/v1/",
            },
        }
        return providers.get(provider, providers["deepseek"])

    def get_fallback_chain(self) -> list[dict]:
        """Return ordered list of provider configs: [primary, fallback1, fallback2, ...]."""
        chain = [self._provider_config(self.llm_provider)]
        if self.llm_fallback_providers:
            for name in self.llm_fallback_providers.split(","):
                name = name.strip()
                if name and name != self.llm_provider:
                    cfg = self._provider_config(name)
                    if cfg["api_key"]:
                        chain.append(cfg)
        return chain

    # Storage (Supabase)
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_bucket: str = "resumes"

    # Email (Resend)
    resend_api_key: str = ""
    from_email: str = "onboarding@resend.dev"

    # App
    app_url: str = "http://localhost:3000"
    api_url: str = "http://localhost:8000"
    # Share-report token lifetime (days). Configurable per deployment.
    share_link_ttl_days: int = 7
    allowed_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]

    # Rate limiting
    # Empty = use in-memory storage (single process only).
    # Set to e.g. "redis://localhost:6379/0" to share limits across workers.
    redis_url: str = ""
    rate_limit_enabled: bool = True

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        # Tolerate stale env vars (e.g. legacy JWT_EXPIRY_DAYS) instead of
        # crashing app startup. New settings are documented in .env.example.
        "extra": "ignore",
    }


_INSECURE_DEFAULTS = {
    "change-this-in-production",
    "hr-interviewer-dev-secret-key-2026",
    "",
}

# Minimum acceptable JWT secret length (in characters) outside development
_MIN_JWT_SECRET_LENGTH = 32


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    is_prod = s.environment.lower() == "production"

    if s.jwt_secret_key in _INSECURE_DEFAULTS or len(s.jwt_secret_key) < _MIN_JWT_SECRET_LENGTH:
        msg = (
            "JWT_SECRET_KEY is missing, default, or too short (<32 chars). "
            "Generate a strong key: "
            'python -c "import secrets; print(secrets.token_hex(64))"'
        )
        if is_prod:
            raise RuntimeError(msg)
        import warnings
        warnings.warn(msg, stacklevel=2)

    if is_prod and s.enable_test_emails:
        raise RuntimeError(
            "ENABLE_TEST_EMAILS must not be true in production."
        )
    return s
