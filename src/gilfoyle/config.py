"""Configuration management for Gilfoyle using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Gilfoyle AI Agent Configuration.

    All settings can be configured via environment variables.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Application Settings
    app_name: str = "Gilfoyle"
    app_version: str = "0.1.0"
    debug: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # Server Settings
    host: str = "0.0.0.0"
    port: int = 8000

    # GitLab Configuration
    gitlab_url: str
    gitlab_token: SecretStr
    gitlab_webhook_secret: SecretStr
    gilfoyle_user_id: int
    gilfoyle_username: str = "gilfoyle"

    # Teamwork Configuration
    teamwork_url: str = "https://projects.ebs-integrator.com"
    teamwork_api_key: SecretStr

    # LLM Configuration
    llm_provider: Literal["anthropic", "openai"] = "anthropic"
    anthropic_api_key: SecretStr | None = None
    openai_api_key: SecretStr | None = None
    llm_model: str = "claude-sonnet-4-20250514"
    llm_max_tokens: int = 4096
    llm_temperature: float = 0.3

    # Rate Limiting
    max_concurrent_reviews: int = 5
    review_timeout_seconds: int = 300

    @field_validator("gitlab_url", "teamwork_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Ensure URLs don't have trailing slashes."""
        return v.rstrip("/")

    @property
    def llm_model_string(self) -> str:
        """Return the full model string for Pydantic AI."""
        return f"{self.llm_provider}:{self.llm_model}"

    @property
    def effective_api_key(self) -> SecretStr:
        """Return the API key for the configured LLM provider."""
        if self.llm_provider == "anthropic":
            if not self.anthropic_api_key or not self.anthropic_api_key.get_secret_value():
                raise ValueError("ANTHROPIC_API_KEY is required when using Anthropic")
            return self.anthropic_api_key
        else:
            if not self.openai_api_key or not self.openai_api_key.get_secret_value():
                raise ValueError("OPENAI_API_KEY is required when using OpenAI")
            return self.openai_api_key


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Returns:
        Settings: The application settings.
    """
    return Settings()
