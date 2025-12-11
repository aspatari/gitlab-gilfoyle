"""Tools for the Gilfoyle AI Agent."""

import logging
from dataclasses import dataclass

from pydantic_ai import RunContext

from gilfoyle.clients.gitlab import GitLabClient, GitLabClientError
from gilfoyle.clients.teamwork import TeamworkClient, TeamworkClientError
from gilfoyle.utils.parsing import truncate_diff

logger = logging.getLogger(__name__)


@dataclass
class ReviewDependencies:
    """Dependencies injected into the Gilfoyle agent."""

    gitlab_client: GitLabClient
    teamwork_client: TeamworkClient
    project_id: int
    mr_iid: int
    source_branch: str
    target_branch: str


async def get_mr_diff(ctx: RunContext[ReviewDependencies]) -> str:
    """Get the diff/changes for the merge request.

    Returns the unified diff showing all changes in this MR.
    """
    try:
        diff = ctx.deps.gitlab_client.get_mr_diff(
            ctx.deps.project_id,
            ctx.deps.mr_iid,
        )
        # Truncate very large diffs
        return truncate_diff(diff, max_lines=1000)
    except Exception as e:
        logger.error(f"Error getting MR diff: {e}")
        return f"Error retrieving diff: {e}"


async def get_file_content(
    ctx: RunContext[ReviewDependencies],
    file_path: str,
    use_source_branch: bool = True,
) -> str:
    """Get the full content of a file from the repository.

    Args:
        file_path: Path to the file in the repository.
        use_source_branch: If True, get from source branch; otherwise from target.

    Returns:
        The file content as a string.
    """
    try:
        ref = ctx.deps.source_branch if use_source_branch else ctx.deps.target_branch
        content = ctx.deps.gitlab_client.get_file_content(
            ctx.deps.project_id,
            file_path,
            ref=ref,
        )
        return content
    except GitLabClientError as e:
        return f"File not found or inaccessible: {file_path} ({e})"
    except Exception as e:
        logger.error(f"Error getting file content: {e}")
        return f"Error retrieving file: {e}"


async def read_documentation(
    ctx: RunContext[ReviewDependencies],
    path: str = "docs",
) -> str:
    """Read documentation from the repository's docs folder.

    Args:
        path: Path to the docs directory or specific file.

    Returns:
        Documentation content or directory listing.
    """
    try:
        # Check if it's a file or directory
        if path.endswith(".md") or path.endswith(".txt") or path.endswith(".rst"):
            # It's a file, read it directly
            content = ctx.deps.gitlab_client.get_file_content(
                ctx.deps.project_id,
                path,
                ref=ctx.deps.target_branch,
            )
            return content

        # It's a directory, list contents
        items = ctx.deps.gitlab_client.list_directory(
            ctx.deps.project_id,
            path=path,
            ref=ctx.deps.target_branch,
            recursive=True,
        )

        if not items:
            return f"No documentation found in {path}/"

        # Format as a listing
        lines = [f"## Documentation in {path}/", ""]
        for item in items:
            if item["type"] == "blob":  # File
                lines.append(f"- {item['path']}")

        return "\n".join(lines)

    except GitLabClientError:
        return f"Documentation path not found: {path}"
    except Exception as e:
        logger.error(f"Error reading documentation: {e}")
        return f"Error reading documentation: {e}"


async def get_coding_standards(ctx: RunContext[ReviewDependencies]) -> str:
    """Get the project's coding standards document.

    Looks for common coding standards file names in the docs folder.
    """
    standard_files = [
        "docs/CODING_STANDARDS.md",
        "docs/coding-standards.md",
        "docs/STYLE_GUIDE.md",
        "docs/style-guide.md",
        "CONTRIBUTING.md",
        ".github/CONTRIBUTING.md",
        "docs/CONTRIBUTING.md",
    ]

    for file_path in standard_files:
        try:
            content = ctx.deps.gitlab_client.get_file_content(
                ctx.deps.project_id,
                file_path,
                ref=ctx.deps.target_branch,
            )
            return f"# Coding Standards from {file_path}\n\n{content}"
        except GitLabClientError:
            continue

    return "No coding standards document found in the repository."


async def list_adrs(ctx: RunContext[ReviewDependencies]) -> str:
    """List all Architecture Decision Records (ADRs) in the project.

    Returns a list of ADR files found in the docs/adr directory.
    """
    adr_paths = ["docs/adr", "docs/ADR", "adr", "ADR", "docs/decisions"]

    for path in adr_paths:
        try:
            items = ctx.deps.gitlab_client.list_directory(
                ctx.deps.project_id,
                path=path,
                ref=ctx.deps.target_branch,
            )
            if items:
                adr_files = [item for item in items if item["type"] == "blob" and item["name"].endswith(".md")]
                if adr_files:
                    lines = [f"## ADRs found in {path}/", ""]
                    for adr in adr_files:
                        lines.append(f"- {adr['name']}")
                    lines.append("")
                    lines.append("Use get_adr_content(filename) to read a specific ADR.")
                    return "\n".join(lines)
        except GitLabClientError:
            continue

    return "No ADR directory found in the repository."


async def get_adr_content(
    ctx: RunContext[ReviewDependencies],
    adr_filename: str,
) -> str:
    """Get the content of a specific ADR.

    Args:
        adr_filename: The filename of the ADR (e.g., "001-use-pydantic.md").

    Returns:
        The ADR content.
    """
    adr_paths = ["docs/adr", "docs/ADR", "adr", "ADR", "docs/decisions"]

    for base_path in adr_paths:
        try:
            full_path = f"{base_path}/{adr_filename}"
            content = ctx.deps.gitlab_client.get_file_content(
                ctx.deps.project_id,
                full_path,
                ref=ctx.deps.target_branch,
            )
            return content
        except GitLabClientError:
            continue

    return f"ADR not found: {adr_filename}"


async def get_teamwork_task(
    ctx: RunContext[ReviewDependencies],
    task_id: str,
) -> str:
    """Fetch task details from Teamwork.

    Args:
        task_id: The Teamwork task ID.

    Returns:
        Formatted task details.
    """
    try:
        task = await ctx.deps.teamwork_client.get_task(task_id)
        return ctx.deps.teamwork_client.format_task_context(task)
    except TeamworkClientError as e:
        return f"Could not fetch task {task_id}: {e}"
    except Exception as e:
        logger.error(f"Error fetching Teamwork task: {e}")
        return f"Error fetching task: {e}"
