"""GitLab webhook event models."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class GitLabUser(BaseModel):
    """GitLab user information."""

    id: int
    username: str
    name: str = ""
    email: str = ""


class GitLabProject(BaseModel):
    """GitLab project information."""

    id: int
    name: str
    path_with_namespace: str
    web_url: str = ""
    default_branch: str = "main"


class MergeRequestAttributes(BaseModel):
    """Merge Request attributes from webhook payload."""

    id: int
    iid: int
    title: str
    description: str | None = None
    state: Literal["opened", "closed", "merged", "locked"] = "opened"
    source_branch: str
    target_branch: str
    author_id: int
    assignee_id: int | None = None
    work_in_progress: bool = False
    draft: bool = False
    url: str = ""


class NoteAttributes(BaseModel):
    """Note (comment) attributes from webhook payload."""

    id: int
    note: str
    noteable_type: Literal["MergeRequest", "Issue", "Commit", "Snippet"]
    author_id: int
    noteable_id: int | None = None


class DiffRefs(BaseModel):
    """Diff references for positioning inline comments."""

    base_sha: str
    head_sha: str
    start_sha: str


class GitLabWebhookEvent(BaseModel):
    """Base model for GitLab webhook events."""

    object_kind: str
    event_type: str | None = None
    user: GitLabUser | None = None
    project: GitLabProject


class MergeRequestEvent(GitLabWebhookEvent):
    """Merge Request webhook event."""

    object_kind: Literal["merge_request"] = "merge_request"
    object_attributes: MergeRequestAttributes
    labels: list[dict[str, Any]] = Field(default_factory=list)
    changes: dict[str, Any] = Field(default_factory=dict)
    reviewers: list[GitLabUser] = Field(default_factory=list)
    assignees: list[GitLabUser] = Field(default_factory=list)

    def has_reviewer(self, username: str) -> bool:
        """Check if a specific user is a reviewer."""
        return any(r.username == username for r in self.reviewers)

    def reviewer_was_added(self, username: str) -> bool:
        """Check if reviewer was just added in this event."""
        reviewer_changes = self.changes.get("reviewers", {})
        previous = reviewer_changes.get("previous", [])
        current = reviewer_changes.get("current", [])

        # Check if username is in current but not in previous
        prev_usernames = {r.get("username") for r in previous if isinstance(r, dict)}
        curr_usernames = {r.get("username") for r in current if isinstance(r, dict)}

        return username in curr_usernames and username not in prev_usernames


class NoteEvent(GitLabWebhookEvent):
    """Note (comment) webhook event."""

    object_kind: Literal["note"] = "note"
    object_attributes: NoteAttributes
    merge_request: MergeRequestAttributes | None = None

    def mentions_user(self, username: str) -> bool:
        """Check if the note mentions a specific user."""
        note_text = self.object_attributes.note.lower()
        mention = f"@{username.lower()}"
        return mention in note_text

    def is_on_merge_request(self) -> bool:
        """Check if this note is on a merge request."""
        return (
            self.object_attributes.noteable_type == "MergeRequest"
            and self.merge_request is not None
        )


def parse_webhook_event(payload: dict[str, Any]) -> GitLabWebhookEvent | None:
    """Parse a webhook payload into the appropriate event model.

    Args:
        payload: The raw webhook payload dictionary.

    Returns:
        The parsed event model, or None if the event type is not supported.
    """
    object_kind = payload.get("object_kind")

    if object_kind == "merge_request":
        return MergeRequestEvent.model_validate(payload)
    elif object_kind == "note":
        return NoteEvent.model_validate(payload)

    return None
