"""Utility functions for parsing and extracting information."""

import re

# Patterns for extracting Teamwork task IDs
TEAMWORK_PATTERNS = [
    # Full URL: https://projects.ebs-integrator.com/app/tasks/12345
    r"https?://projects\.ebs-integrator\.com/[^\s]*tasks/(\d+)",
    # URL with #tasks: https://projects.ebs-integrator.com/#/tasks/12345
    r"https?://projects\.ebs-integrator\.com/[^\s]*#/tasks/(\d+)",
    # Shorthand: #TW-12345 or TW-12345
    r"#?TW-(\d+)",
    # Task reference: task: 12345 or task #12345
    r"task[:\s#]+(\d+)",
    # Teamwork URL with different subdomains
    r"https?://[a-zA-Z0-9-]+\.teamwork\.com/[^\s]*tasks/(\d+)",
]


def extract_task_ids(text: str | None) -> list[str]:
    """Extract Teamwork task IDs from text.

    Supports various formats:
    - Full URLs: https://projects.ebs-integrator.com/app/tasks/12345
    - Hash URLs: https://projects.ebs-integrator.com/#/tasks/12345
    - Shorthand: #TW-12345 or TW-12345
    - References: task: 12345 or task #12345

    Args:
        text: The text to search for task IDs.

    Returns:
        A deduplicated list of task IDs found.
    """
    if not text:
        return []

    task_ids: set[str] = set()

    for pattern in TEAMWORK_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        task_ids.update(matches)

    return sorted(task_ids)


def sanitize_comment(comment: str) -> str:
    """Sanitize a comment for safe posting to GitLab.

    Args:
        comment: The comment text to sanitize.

    Returns:
        The sanitized comment.
    """
    # Remove any potential script injections
    comment = re.sub(r"<script[^>]*>.*?</script>", "", comment, flags=re.IGNORECASE | re.DOTALL)

    # Escape HTML entities that could cause issues
    comment = comment.replace("<", "&lt;").replace(">", "&gt;")

    # But allow markdown formatting by unescaping common patterns
    comment = re.sub(r"&lt;(/?)(?:strong|em|code|pre|a|br)&gt;", r"<\1>", comment)

    return comment.strip()


def truncate_diff(diff: str, max_lines: int = 500) -> str:
    """Truncate a diff to a maximum number of lines.

    Args:
        diff: The diff content.
        max_lines: Maximum number of lines to keep.

    Returns:
        The truncated diff with an indicator if truncation occurred.
    """
    lines = diff.split("\n")

    if len(lines) <= max_lines:
        return diff

    truncated = lines[:max_lines]
    truncated.append(f"\n... (truncated, {len(lines) - max_lines} more lines)")

    return "\n".join(truncated)


def extract_file_paths_from_diff(diff: str) -> list[str]:
    """Extract file paths from a unified diff.

    Args:
        diff: The unified diff content.

    Returns:
        A list of file paths mentioned in the diff.
    """
    # Match lines like: diff --git a/path/to/file b/path/to/file
    pattern = r"diff --git a/(.+?) b/(.+?)$"
    matches = re.findall(pattern, diff, re.MULTILINE)

    # Return unique paths (using the 'b' path as it's the new version)
    paths = [match[1] for match in matches]
    return list(dict.fromkeys(paths))  # Preserve order, remove duplicates
