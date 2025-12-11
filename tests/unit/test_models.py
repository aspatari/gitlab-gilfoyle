"""Tests for data models."""

import pytest

from gilfoyle.models.events import (
    MergeRequestEvent,
    NoteEvent,
    parse_webhook_event,
)
from gilfoyle.models.review import (
    InlineComment,
    ReviewResult,
    Severity,
)


class TestInlineComment:
    """Tests for InlineComment model."""

    def test_create_comment(self):
        """Test creating an inline comment."""
        comment = InlineComment(
            file_path="src/main.py",
            line_number=10,
            comment="This needs improvement",
            severity=Severity.SUGGESTION,
        )
        assert comment.file_path == "src/main.py"
        assert comment.line_number == 10
        assert comment.line_type == "new"  # default
        assert comment.severity == Severity.SUGGESTION

    def test_format_for_gitlab(self):
        """Test GitLab formatting."""
        comment = InlineComment(
            file_path="test.py",
            line_number=5,
            comment="Security issue found",
            severity=Severity.ERROR,
        )
        formatted = comment.format_for_gitlab()
        assert "**[ERROR]**" in formatted
        assert "Security issue found" in formatted

    def test_line_number_validation(self):
        """Test that line number must be positive."""
        with pytest.raises(ValueError):
            InlineComment(
                file_path="test.py",
                line_number=0,
                comment="Invalid",
                severity=Severity.INFO,
            )


class TestReviewResult:
    """Tests for ReviewResult model."""

    def test_create_review(self):
        """Test creating a review result."""
        review = ReviewResult(
            summary="Code looks good overall",
            overall_assessment="approved",
            inline_comments=[],
            general_comments=["Nice work!"],
        )
        assert review.summary == "Code looks good overall"
        assert review.overall_assessment == "approved"
        assert len(review.general_comments) == 1

    def test_format_summary_comment(self):
        """Test summary formatting."""
        review = ReviewResult(
            summary="Found some issues",
            overall_assessment="needs_changes",
            inline_comments=[
                InlineComment(
                    file_path="test.py",
                    line_number=1,
                    comment="Fix this",
                    severity=Severity.ERROR,
                )
            ],
            general_comments=["Please address the issues"],
            referenced_standards=["docs/CODING_STANDARDS.md"],
        )
        formatted = review.format_summary_comment()
        assert "## Gilfoyle Code Review" in formatted
        assert "Needs Changes" in formatted
        assert "Found some issues" in formatted
        assert "Please address the issues" in formatted
        assert "CODING_STANDARDS.md" in formatted


class TestWebhookEvents:
    """Tests for webhook event parsing."""

    def test_parse_mr_event(self, sample_mr_event):
        """Test parsing a merge request event."""
        event = parse_webhook_event(sample_mr_event)
        assert isinstance(event, MergeRequestEvent)
        assert event.object_kind == "merge_request"
        assert event.project.id == 1

    def test_parse_note_event(self, sample_note_event):
        """Test parsing a note event."""
        event = parse_webhook_event(sample_note_event)
        assert isinstance(event, NoteEvent)
        assert event.object_kind == "note"
        assert event.mentions_user("gilfoyle")

    def test_parse_unsupported_event(self):
        """Test parsing an unsupported event."""
        event = parse_webhook_event({"object_kind": "pipeline"})
        assert event is None

    def test_mr_event_reviewer_check(self, sample_mr_event):
        """Test checking if reviewer was added."""
        event = MergeRequestEvent.model_validate(sample_mr_event)
        assert event.has_reviewer("gilfoyle")
        assert event.reviewer_was_added("gilfoyle")
        assert not event.has_reviewer("other_user")

    def test_note_event_mention_check(self, sample_note_event):
        """Test checking if user is mentioned."""
        event = NoteEvent.model_validate(sample_note_event)
        assert event.mentions_user("gilfoyle")
        assert not event.mentions_user("other_user")
        assert event.is_on_merge_request()
