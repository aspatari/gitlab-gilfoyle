"""Integration tests for Teamwork client.

These tests require a real Teamwork instance and valid credentials.
They are skipped by default unless INTEGRATION_TESTS=1 is set.
"""

import os

import pytest

# Skip all tests in this module unless integration testing is enabled
pytestmark = pytest.mark.skipif(
    os.environ.get("INTEGRATION_TESTS") != "1",
    reason="Integration tests disabled. Set INTEGRATION_TESTS=1 to enable.",
)


class TestTeamworkClientIntegration:
    """Integration tests for Teamwork client."""

    @pytest.fixture
    async def teamwork_client(self):
        """Create a real Teamwork client."""
        from gilfoyle.clients.teamwork import TeamworkClient
        from gilfoyle.config import get_settings

        settings = get_settings()
        client = TeamworkClient(
            base_url=settings.teamwork_url,
            api_key=settings.teamwork_api_key.get_secret_value(),
        )
        yield client
        await client.close()

    @pytest.mark.asyncio
    async def test_verify_connection(self, teamwork_client):
        """Test verifying Teamwork connection."""
        result = await teamwork_client.verify_connection()
        assert result is True

    @pytest.mark.asyncio
    async def test_get_task(self, teamwork_client):
        """Test fetching a task."""
        # This test requires a real task ID to work
        # Placeholder for real integration test
        pass
