"""Integration tests for GitLab client.

These tests require a real GitLab instance and valid credentials.
They are skipped by default unless INTEGRATION_TESTS=1 is set.
"""

import os

import pytest

# Skip all tests in this module unless integration testing is enabled
pytestmark = pytest.mark.skipif(
    os.environ.get("INTEGRATION_TESTS") != "1",
    reason="Integration tests disabled. Set INTEGRATION_TESTS=1 to enable.",
)


class TestGitLabClientIntegration:
    """Integration tests for GitLab client."""

    @pytest.fixture
    def gitlab_client(self):
        """Create a real GitLab client."""
        from gilfoyle.clients.gitlab import GitLabClient
        from gilfoyle.config import get_settings

        settings = get_settings()
        return GitLabClient(
            url=settings.gitlab_url,
            token=settings.gitlab_token.get_secret_value(),
        )

    def test_check_user_exists(self, gitlab_client):
        """Test checking if gilfoyle user exists."""
        from gilfoyle.config import get_settings

        settings = get_settings()
        assert gitlab_client.check_user_exists(settings.gilfoyle_username)

    def test_list_directory(self, gitlab_client):
        """Test listing repository directory."""
        # This test requires a real project ID to work
        # Placeholder for real integration test
        pass
