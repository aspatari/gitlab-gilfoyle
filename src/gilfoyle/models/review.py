"""Review result models for Gilfoyle AI Agent."""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class Severity(str, Enum):
    """Severity level for review comments."""

    INFO = "info"
    SUGGESTION = "suggestion"
    WARNING = "warning"
    ERROR = "error"


class InlineComment(BaseModel):
    """A comment on a specific line of code in the MR diff."""

    file_path: str = Field(
        ...,
        description="The path to the file being commented on",
    )
    line_number: int = Field(
        ...,
        gt=0,
        description="The line number in the diff (1-indexed)",
    )
    line_type: Literal["old", "new"] = Field(
        default="new",
        description="Whether this is on the old (deleted) or new (added) line",
    )
    comment: str = Field(
        ...,
        min_length=1,
        description="The review comment content",
    )
    severity: Severity = Field(
        default=Severity.SUGGESTION,
        description="The severity level of this comment",
    )

    def format_for_gitlab(self) -> str:
        """Format the comment for GitLab with severity prefix."""
        severity_prefixes = {
            Severity.INFO: "**[INFO]**",
            Severity.SUGGESTION: "**[SUGGESTION]**",
            Severity.WARNING: "**[WARNING]** :warning:",
            Severity.ERROR: "**[ERROR]** :x:",
        }
        prefix = severity_prefixes.get(self.severity, "")
        return f"{prefix} {self.comment}"


class ReviewResult(BaseModel):
    """Structured output for a complete MR review."""

    summary: str = Field(
        ...,
        min_length=10,
        description="A brief summary of the overall review findings",
    )
    overall_assessment: Literal["approved", "needs_changes", "needs_discussion"] = Field(
        ...,
        description="The overall verdict for the MR",
    )
    inline_comments: list[InlineComment] = Field(
        default_factory=list,
        description="List of inline comments on specific code lines",
    )
    general_comments: list[str] = Field(
        default_factory=list,
        description="General comments not tied to specific lines",
    )
    referenced_standards: list[str] = Field(
        default_factory=list,
        description="Coding standards or ADRs referenced in the review",
    )
    task_context_used: bool = Field(
        default=False,
        description="Whether Teamwork task context was incorporated",
    )

    def format_summary_comment(self) -> str:
        """Format the review as a summary comment for GitLab."""
        verdict_emoji = {
            "approved": ":white_check_mark:",
            "needs_changes": ":x:",
            "needs_discussion": ":speech_balloon:",
        }
        emoji = verdict_emoji.get(self.overall_assessment, "")

        lines = [
            f"## Gilfoyle Code Review {emoji}",
            "",
            f"**Verdict:** {self.overall_assessment.replace('_', ' ').title()}",
            "",
            "### Summary",
            self.summary,
        ]

        if self.general_comments:
            lines.extend(["", "### General Comments"])
            for comment in self.general_comments:
                lines.append(f"- {comment}")

        if self.referenced_standards:
            lines.extend(["", "### Referenced Standards"])
            for standard in self.referenced_standards:
                lines.append(f"- {standard}")

        if self.inline_comments:
            lines.extend(
                [
                    "",
                    f"### Inline Comments ({len(self.inline_comments)})",
                    "_See inline comments in the diff for details._",
                ]
            )

        if self.task_context_used:
            lines.extend(["", "_Task context from Teamwork was considered in this review._"])

        lines.extend(["", "---", "_Review by Gilfoyle AI Agent_"])

        return "\n".join(lines)


class ReviewContext(BaseModel):
    """Context information for a review."""

    project_id: int = Field(..., description="GitLab project ID")
    mr_iid: int = Field(..., description="Merge Request internal ID")
    mr_title: str = Field(default="", description="MR title")
    mr_description: str = Field(default="", description="MR description")
    source_branch: str = Field(default="", description="Source branch name")
    target_branch: str = Field(default="", description="Target branch name")
    author_username: str = Field(default="", description="MR author's username")
    task_ids: list[str] = Field(default_factory=list, description="Extracted Teamwork task IDs")
