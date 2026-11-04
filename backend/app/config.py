"""Application settings loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal
from pydantic import Field, field_validator, model_validator

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    portfolio_demo: bool = False

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
    environment: Literal["development", "production"] = "development"

    # LLM Provider: "openai", "deepseek", or "anthropic"
    llm_provider: Literal["openai", "deepseek", "anthropic"] = "deepseek"
    llm_model: str = ""  # auto-detected from provider if blank
    openai_api_key: str = ""
    deepseek_api_key: str = ""
    anthropic_api_key: str = ""
    anthropic_workspace_id: str = ""
    llm_timeout_seconds: float = Field(default=60, gt=0, le=300)
    llm_max_retries: int = Field(default=0, ge=0, le=2)
    llm_max_output_tokens: int = Field(default=4096, ge=256, le=16384)
    # Optional per-process verification limits; restart resets the counter.
    llm_request_limit: int = Field(default=0, ge=0)
    llm_max_input_bytes: int = Field(default=0, ge=0)

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
        """Return name, api_key, model, base_url for a given provider."""
        providers = {
            "deepseek": {
                "name": "deepseek",
                "api_key": self.deepseek_api_key,
                "model": "deepseek-flash",
                "base_url": "https://api.deepseek.com",
            },
            "openai": {
                "name": "openai",
                "api_key": self.openai_api_key,
                "model": "gpt-4.1-mini",
                "base_url": "https://api.openai.com/v1",
            },
            "anthropic": {
                "name": "anthropic",
                "api_key": self.anthropic_api_key,
                "model": "claude-sonnet-4-6",
                "base_url": "https://api.anthropic.com/v1/",
                "default_headers": ({"anthropic-workspace-id": self.anthropic_workspace_id}
                                    if self.anthropic_workspace_id else {}),
            },
        }
        if provider not in providers:
            raise ValueError("Unsupported LLM provider; use openai, deepseek or anthropic")
        return providers[provider]

    def get_fallback_chain(self) -> list[dict]:
        """Return ordered list of provider configs: [primary, fallback1, fallback2, ...]."""
        chain = [self._provider_config(self.llm_provider)]
        chain[0]["model"] = self.active_llm_model
        if self.llm_fallback_providers:
            for name in self.llm_fallback_providers.split(","):
                name = name.strip()
                if name and name != self.llm_provider:
                    cfg = self._provider_config(name)
                    if not cfg["api_key"]:
                        raise ValueError("An explicitly selected fallback is missing its API key")
                    if not any(item["name"] == name for item in chain):
                        chain.append(cfg)
        return chain

    # Storage (Supabase)
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_bucket: str = "resumes"

    # Email (Resend)
    resend_api_key: str = ""
    from_email: str = ""

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
    # Only the owned Next proxy may supply client identity. Uvicorn must use
    # --no-proxy-headers so request.client remains the actual transport peer.
    trusted_proxy_ips: list[str] = []
    proxy_auth_secret: str = ""

    @field_validator("environment", mode="before")
    @classmethod
    def environment_name(cls, value):
        return value.strip().lower() if isinstance(value, str) else value

    @model_validator(mode="after")
    def secure_configuration(self):
        for name in self.llm_fallback_providers.split(","):
            if name.strip():
                self._provider_config(name.strip())
        if self.portfolio_demo:
            if self.environment != "development":
                raise ValueError("Portfolio demo is forbidden in production")
            from app.demo.guard import require_demo
            require_demo()
        if self.environment == "production":
            if self.jwt_secret_key.strip().lower() in _INSECURE_DEFAULTS or len(self.jwt_secret_key.strip()) < 32:
                raise ValueError("JWT_SECRET_KEY must be a generated secret of at least 32 characters")
            if self.enable_test_emails:
                raise ValueError("Test emails are forbidden in production")
        if self.trusted_proxy_ips and len(self.proxy_auth_secret) < 32:
            raise ValueError("Trusted proxies require a generated PROXY_AUTH_SECRET of at least 32 characters")
        return self


    model_config = {
        "env_file": ".env",
        "hide_input_in_errors": True,
        "env_file_encoding": "utf-8",
        # Tolerate stale env vars (e.g. legacy JWT_EXPIRY_DAYS) instead of
        # crashing app startup. New settings are documented in .env.example.
        "extra": "ignore",
    }


_INSECURE_DEFAULTS = {
    "change-this-in-production",
    "hr-interviewer-dev-secret-key-2026",
    "replace-me-with-a-64-byte-hex-secret",
    "your-secret-key-change-in-production",
    "",
}

# Minimum acceptable JWT secret length (in characters) outside development
_MIN_JWT_SECRET_LENGTH = 32


@lru_cache
def get_settings() -> Settings:
    import os
    s = Settings(_env_file=None) if os.environ.get("PORTFOLIO_DEMO") == "1" else Settings()
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
