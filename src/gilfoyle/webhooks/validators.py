"""Webhook payload validators."""

import hmac
import logging
from typing import Any

from gilfoyle.config import Settings

logger = logging.getLogger(__name__)


def validate_gitlab_signature(
    payload: bytes,  # noqa: ARG001 - kept for API consistency
    signature: str | None,
    settings: Settings,
) -> bool:
    """Validate the GitLab webhook signature.

    GitLab uses a simple token comparison, not HMAC.
    The X-Gitlab-Token header should match our secret.

    Args:
        payload: The raw request body (not used for GitLab, but kept for consistency).
        signature: The X-Gitlab-Token header value.
        settings: Application settings containing the webhook secret.

    Returns:
        True if the signature is valid, False otherwise.
    """
    if not signature:
        logger.warning("No X-Gitlab-Token header provided")
        return False

    expected = settings.gitlab_webhook_secret.get_secret_value()

    # Use constant-time comparison to prevent timing attacks
    return hmac.compare_digest(signature, expected)


def validate_webhook_payload(payload: dict[str, Any]) -> tuple[bool, str]:
    """Validate the structure of a webhook payload.

    Args:
        payload: The parsed webhook payload.

    Returns:
        A tuple of (is_valid, error_message).
    """
    if not isinstance(payload, dict):
        return False, "Payload must be a JSON object"

    object_kind = payload.get("object_kind")
    if not object_kind:
        return False, "Missing 'object_kind' field"

    if object_kind not in ("merge_request", "note"):
        return False, f"Unsupported event type: {object_kind}"

    if "project" not in payload:
        return False, "Missing 'project' field"

    if "object_attributes" not in payload:
        return False, "Missing 'object_attributes' field"

    # For note events, we need merge_request info
    if object_kind == "note":
        noteable_type = payload.get("object_attributes", {}).get("noteable_type")
        if noteable_type != "MergeRequest":
            return False, "Note event is not on a merge request"
        if "merge_request" not in payload:
            return False, "Missing 'merge_request' field for note event"

    return True, ""
