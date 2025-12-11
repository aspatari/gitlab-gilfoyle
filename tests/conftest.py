"""Pytest configuration and fixtures."""

import os
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Set test environment variables before importing app
os.environ.setdefault("GITLAB_URL", "https://gitlab.test.com")
os.environ.setdefault("GITLAB_TOKEN", "test-token")
os.environ.setdefault("GITLAB_WEBHOOK_SECRET", "test-secret")
os.environ.setdefault("GILFOYLE_USER_ID", "123")
os.environ.setdefault("TEAMWORK_URL", "https://teamwork.test.com")
os.environ.setdefault("TEAMWORK_API_KEY", "test-teamwork-key")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    from gilfoyle.config import Settings

    return Settings(
        gitlab_url="https://gitlab.test.com",
        gitlab_token="test-token",  # type: ignore
        gitlab_webhook_secret="test-secret",  # type: ignore
        gilfoyle_user_id=123,
        teamwork_url="https://teamwork.test.com",
        teamwork_api_key="test-teamwork-key",  # type: ignore
        anthropic_api_key="test-anthropic-key",  # type: ignore
        debug=True,
    )


@pytest.fixture
def mock_gitlab_client():
    """Create a mock GitLab client."""
    client = MagicMock()
    client.get_mr_details.return_value = {
        "id": 1,
        "iid": 1,
        "title": "Test MR",
        "description": "Test description",
        "state": "opened",
        "source_branch": "feature/test",
        "target_branch": "main",
        "author": "testuser",
        "web_url": "https://gitlab.test.com/test/repo/-/merge_requests/1",
        "diff_refs": {
            "base_sha": "abc123",
            "head_sha": "def456",
            "start_sha": "abc123",
        },
    }
    client.get_mr_diff.return_value = """
diff --git a/test.py b/test.py
--- a/test.py
+++ b/test.py
@@ -1,3 +1,5 @@
 def hello():
-    print("Hello")
+    print("Hello, World!")
+
+API_KEY = "secret123"
"""
    client.get_diff_refs.return_value = {
        "base_sha": "abc123",
        "head_sha": "def456",
        "start_sha": "abc123",
    }
    return client


@pytest.fixture
def mock_teamwork_client():
    """Create a mock Teamwork client."""
    client = MagicMock()
    client.get_task.return_value = {
        "id": "12345",
        "title": "Implement feature",
        "description": "Description of the task",
        "status": "in progress",
        "priority": "high",
        "project_name": "Test Project",
        "responsible": "Test User",
    }
    client.format_task_context.return_value = "## Task: Implement feature\n\nDescription"
    return client


@pytest.fixture
def test_client(mock_settings) -> Generator[TestClient, None, None]:
    """Create a test client with mocked dependencies."""
    with (
        patch("gilfoyle.main.get_settings", return_value=mock_settings),
        patch("gilfoyle.agent.gilfoyle.GitLabClient"),
        patch("gilfoyle.agent.gilfoyle.TeamworkClient"),
    ):
        from gilfoyle.main import create_app

        app = create_app(mock_settings)
        with TestClient(app) as client:
            yield client


@pytest.fixture
def sample_mr_event() -> dict:
    """Sample merge request webhook event."""
    return {
        "object_kind": "merge_request",
        "event_type": "merge_request",
        "user": {
            "id": 1,
            "username": "testuser",
            "name": "Test User",
            "email": "test@example.com",
        },
        "project": {
            "id": 1,
            "name": "test-project",
            "path_with_namespace": "group/test-project",
            "web_url": "https://gitlab.test.com/group/test-project",
            "default_branch": "main",
        },
        "object_attributes": {
            "id": 1,
            "iid": 1,
            "title": "Test MR",
            "description": "Test description with TW-12345",
            "state": "opened",
            "source_branch": "feature/test",
            "target_branch": "main",
            "author_id": 1,
            "url": "https://gitlab.test.com/group/test-project/-/merge_requests/1",
        },
        "labels": [],
        "changes": {
            "reviewers": {
                "previous": [],
                "current": [{"username": "gilfoyle", "id": 123}],
            }
        },
        "reviewers": [{"id": 123, "username": "gilfoyle", "name": "Gilfoyle"}],
    }


@pytest.fixture
def sample_note_event() -> dict:
    """Sample note (comment) webhook event."""
    return {
        "object_kind": "note",
        "event_type": "note",
        "user": {
            "id": 1,
            "username": "testuser",
            "name": "Test User",
            "email": "test@example.com",
        },
        "project": {
            "id": 1,
            "name": "test-project",
            "path_with_namespace": "group/test-project",
            "web_url": "https://gitlab.test.com/group/test-project",
            "default_branch": "main",
        },
        "object_attributes": {
            "id": 1,
            "note": "@gilfoyle please review this MR",
            "noteable_type": "MergeRequest",
            "author_id": 1,
            "noteable_id": 1,
        },
        "merge_request": {
            "id": 1,
            "iid": 1,
            "title": "Test MR",
            "description": "Test description",
            "state": "opened",
            "source_branch": "feature/test",
            "target_branch": "main",
            "author_id": 1,
            "url": "https://gitlab.test.com/group/test-project/-/merge_requests/1",
        },
    }
