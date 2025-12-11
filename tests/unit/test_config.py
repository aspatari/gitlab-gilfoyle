"""Tests for configuration module."""

import os
from unittest.mock import patch

import pytest


class TestSettings:
    """Tests for Settings configuration."""

    def test_settings_from_env(self):
        """Test loading settings from environment variables."""
        env = {
            "GITLAB_URL": "https://gitlab.example.com",
            "GITLAB_TOKEN": "test-token",
            "GITLAB_WEBHOOK_SECRET": "secret",
            "GILFOYLE_USER_ID": "123",
            "TEAMWORK_URL": "https://teamwork.example.com",
            "TEAMWORK_API_KEY": "tw-key",
            "ANTHROPIC_API_KEY": "ant-key",
        }
        with patch.dict(os.environ, env, clear=False):
            from gilfoyle.config import Settings

            settings = Settings()
            assert settings.gitlab_url == "https://gitlab.example.com"
            assert settings.gitlab_token.get_secret_value() == "test-token"
            assert settings.gilfoyle_user_id == 123

    def test_url_trailing_slash_removed(self):
        """Test that trailing slashes are removed from URLs."""
        env = {
            "GITLAB_URL": "https://gitlab.example.com/",
            "GITLAB_TOKEN": "test-token",
            "GITLAB_WEBHOOK_SECRET": "secret",
            "GILFOYLE_USER_ID": "123",
            "TEAMWORK_URL": "https://teamwork.example.com/",
            "TEAMWORK_API_KEY": "tw-key",
            "ANTHROPIC_API_KEY": "ant-key",
        }
        with patch.dict(os.environ, env, clear=False):
            from gilfoyle.config import Settings

            settings = Settings()
            assert not settings.gitlab_url.endswith("/")
            assert not settings.teamwork_url.endswith("/")

    def test_llm_model_string(self):
        """Test LLM model string property."""
        env = {
            "GITLAB_URL": "https://gitlab.example.com",
            "GITLAB_TOKEN": "test-token",
            "GITLAB_WEBHOOK_SECRET": "secret",
            "GILFOYLE_USER_ID": "123",
            "TEAMWORK_URL": "https://teamwork.example.com",
            "TEAMWORK_API_KEY": "tw-key",
            "ANTHROPIC_API_KEY": "ant-key",
            "LLM_PROVIDER": "anthropic",
            "LLM_MODEL": "claude-sonnet-4-20250514",
        }
        with patch.dict(os.environ, env, clear=False):
            from gilfoyle.config import Settings

            settings = Settings()
            assert settings.llm_model_string == "anthropic:claude-sonnet-4-20250514"

    def test_effective_api_key_anthropic(self):
        """Test effective API key for Anthropic."""
        env = {
            "GITLAB_URL": "https://gitlab.example.com",
            "GITLAB_TOKEN": "test-token",
            "GITLAB_WEBHOOK_SECRET": "secret",
            "GILFOYLE_USER_ID": "123",
            "TEAMWORK_URL": "https://teamwork.example.com",
            "TEAMWORK_API_KEY": "tw-key",
            "ANTHROPIC_API_KEY": "ant-key",
            "LLM_PROVIDER": "anthropic",
        }
        with patch.dict(os.environ, env, clear=False):
            from gilfoyle.config import Settings

            settings = Settings()
            assert settings.effective_api_key.get_secret_value() == "ant-key"

    def test_effective_api_key_missing(self):
        """Test error when API key is missing."""
        env = {
            "GITLAB_URL": "https://gitlab.example.com",
            "GITLAB_TOKEN": "test-token",
            "GITLAB_WEBHOOK_SECRET": "secret",
            "GILFOYLE_USER_ID": "123",
            "TEAMWORK_URL": "https://teamwork.example.com",
            "TEAMWORK_API_KEY": "tw-key",
            "LLM_PROVIDER": "anthropic",
            # Explicitly set ANTHROPIC_API_KEY to empty to simulate missing
            "ANTHROPIC_API_KEY": "",
        }
        with patch.dict(os.environ, env, clear=True):
            from gilfoyle.config import Settings

            settings = Settings()
            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY is required"):
                _ = settings.effective_api_key

    def test_defaults(self):
        """Test default values."""
        env = {
            "GITLAB_URL": "https://gitlab.example.com",
            "GITLAB_TOKEN": "test-token",
            "GITLAB_WEBHOOK_SECRET": "secret",
            "GILFOYLE_USER_ID": "123",
            "TEAMWORK_API_KEY": "tw-key",
            "ANTHROPIC_API_KEY": "ant-key",
        }
        with patch.dict(os.environ, env, clear=False):
            from gilfoyle.config import Settings

            settings = Settings()
            assert settings.app_name == "Gilfoyle"
            assert settings.debug is False
            assert settings.log_level == "INFO"
            assert settings.gilfoyle_username == "gilfoyle"
            assert settings.llm_provider == "anthropic"
