"""Tests for webhook handlers."""

from fastapi.testclient import TestClient


class TestWebhookEndpoints:
    """Tests for webhook endpoints."""

    def test_health_check(self, test_client: TestClient):
        """Test the health check endpoint."""
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data

    def test_readiness_check(self, test_client: TestClient):
        """Test the readiness endpoint."""
        response = test_client.get("/ready")
        assert response.status_code == 200
        assert response.json()["status"] == "ready"

    def test_webhook_no_token(self, test_client: TestClient):
        """Test webhook without authentication token."""
        response = test_client.post(
            "/webhook/gitlab",
            json={"object_kind": "note"},
        )
        assert response.status_code == 401

    def test_webhook_invalid_token(self, test_client: TestClient):
        """Test webhook with invalid token."""
        response = test_client.post(
            "/webhook/gitlab",
            json={"object_kind": "note"},
            headers={"X-Gitlab-Token": "wrong-token"},
        )
        assert response.status_code == 401

    def test_webhook_valid_token(self, test_client: TestClient):
        """Test webhook with valid token but unsupported event."""
        response = test_client.post(
            "/webhook/gitlab",
            json={"object_kind": "pipeline", "project": {}},
            headers={"X-Gitlab-Token": "test-secret"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ignored"

    def test_webhook_invalid_json(self, test_client: TestClient):
        """Test webhook with invalid JSON."""
        response = test_client.post(
            "/webhook/gitlab",
            content="not json",
            headers={
                "X-Gitlab-Token": "test-secret",
                "Content-Type": "application/json",
            },
        )
        assert response.status_code == 400

    def test_webhook_missing_fields(self, test_client: TestClient):
        """Test webhook with missing required fields."""
        response = test_client.post(
            "/webhook/gitlab",
            json={"object_kind": "note"},  # Missing project and object_attributes
            headers={"X-Gitlab-Token": "test-secret"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ignored"


class TestWebhookValidation:
    """Tests for webhook payload validation."""

    def test_validate_gitlab_signature(self, mock_settings):
        """Test GitLab signature validation."""
        from gilfoyle.webhooks.validators import validate_gitlab_signature

        assert validate_gitlab_signature(b"payload", "test-secret", mock_settings)
        assert not validate_gitlab_signature(b"payload", "wrong-secret", mock_settings)
        assert not validate_gitlab_signature(b"payload", None, mock_settings)

    def test_validate_webhook_payload_valid(self):
        """Test validation of valid payload."""
        from gilfoyle.webhooks.validators import validate_webhook_payload

        payload = {
            "object_kind": "merge_request",
            "project": {"id": 1},
            "object_attributes": {"iid": 1},
        }
        is_valid, error = validate_webhook_payload(payload)
        assert is_valid
        assert error == ""

    def test_validate_webhook_payload_missing_kind(self):
        """Test validation with missing object_kind."""
        from gilfoyle.webhooks.validators import validate_webhook_payload

        payload = {"project": {}}
        is_valid, error = validate_webhook_payload(payload)
        assert not is_valid
        assert "object_kind" in error

    def test_validate_webhook_payload_unsupported_kind(self):
        """Test validation with unsupported event type."""
        from gilfoyle.webhooks.validators import validate_webhook_payload

        payload = {
            "object_kind": "pipeline",
            "project": {},
            "object_attributes": {},
        }
        is_valid, error = validate_webhook_payload(payload)
        assert not is_valid
        assert "Unsupported" in error

    def test_validate_note_event_not_on_mr(self):
        """Test validation of note event not on MR."""
        from gilfoyle.webhooks.validators import validate_webhook_payload

        payload = {
            "object_kind": "note",
            "project": {"id": 1},
            "object_attributes": {
                "noteable_type": "Issue",
            },
        }
        is_valid, error = validate_webhook_payload(payload)
        assert not is_valid
        assert "not on a merge request" in error
