"""GitLab API client for Gilfoyle."""

import logging
from typing import Any

import gitlab
from gitlab.v4.objects import Project, ProjectMergeRequest
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from gilfoyle.models.review import InlineComment

logger = logging.getLogger(__name__)


class GitLabClientError(Exception):
    """Base exception for GitLab client errors."""


class GitLabClient:
    """Async-friendly wrapper around python-gitlab for Gilfoyle operations."""

    def __init__(self, url: str, token: str) -> None:
        """Initialize the GitLab client.

        Args:
            url: The GitLab instance URL.
            token: Personal access token for authentication.
        """
        self.url = url
        self._gl = gitlab.Gitlab(url, private_token=token)
        self._gl.auth()
        logger.info(f"Authenticated with GitLab as {self._gl.user.username}")  # type: ignore

    def _get_project(self, project_id: int) -> Project:
        """Get a project by ID."""
        return self._gl.projects.get(project_id)

    def _get_mr(self, project_id: int, mr_iid: int) -> ProjectMergeRequest:
        """Get a merge request by project ID and MR IID."""
        project = self._get_project(project_id)
        return project.mergerequests.get(mr_iid)

    @retry(
        retry=retry_if_exception_type(gitlab.exceptions.GitlabError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def get_mr_details(self, project_id: int, mr_iid: int) -> dict[str, Any]:
        """Get merge request details.

        Args:
            project_id: The GitLab project ID.
            mr_iid: The merge request internal ID.

        Returns:
            A dictionary with MR details.
        """
        mr = self._get_mr(project_id, mr_iid)
        return {
            "id": mr.id,
            "iid": mr.iid,
            "title": mr.title,
            "description": mr.description or "",
            "state": mr.state,
            "source_branch": mr.source_branch,
            "target_branch": mr.target_branch,
            "author": mr.author.get("username", "") if mr.author else "",
            "web_url": mr.web_url,
            "diff_refs": mr.diff_refs,
        }

    @retry(
        retry=retry_if_exception_type(gitlab.exceptions.GitlabError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def get_mr_diff(self, project_id: int, mr_iid: int) -> str:
        """Get the diff for a merge request.

        Args:
            project_id: The GitLab project ID.
            mr_iid: The merge request internal ID.

        Returns:
            The unified diff as a string.
        """
        mr = self._get_mr(project_id, mr_iid)
        changes = mr.changes()

        diff_parts = []
        for change in changes.get("changes", []):
            old_path = change.get("old_path", "")
            new_path = change.get("new_path", "")
            diff = change.get("diff", "")

            header = f"diff --git a/{old_path} b/{new_path}"
            diff_parts.append(f"{header}\n{diff}")

        return "\n".join(diff_parts)

    @retry(
        retry=retry_if_exception_type(gitlab.exceptions.GitlabError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def get_file_content(
        self,
        project_id: int,
        file_path: str,
        ref: str = "HEAD",
    ) -> str:
        """Get the content of a file from the repository.

        Args:
            project_id: The GitLab project ID.
            file_path: Path to the file in the repository.
            ref: Git ref (branch, tag, or commit SHA).

        Returns:
            The file content as a string.

        Raises:
            GitLabClientError: If the file cannot be retrieved.
        """
        try:
            project = self._get_project(project_id)
            file = project.files.get(file_path=file_path, ref=ref)
            return file.decode().decode("utf-8")
        except gitlab.exceptions.GitlabGetError as e:
            logger.warning(f"Could not get file {file_path}: {e}")
            raise GitLabClientError(f"File not found: {file_path}") from e

    @retry(
        retry=retry_if_exception_type(gitlab.exceptions.GitlabError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def list_directory(
        self,
        project_id: int,
        path: str = "",
        ref: str = "HEAD",
        recursive: bool = False,
    ) -> list[dict[str, str]]:
        """List files in a directory.

        Args:
            project_id: The GitLab project ID.
            path: Directory path in the repository.
            ref: Git ref (branch, tag, or commit SHA).
            recursive: Whether to list recursively.

        Returns:
            A list of file/directory entries.
        """
        try:
            project = self._get_project(project_id)
            items = project.repository_tree(path=path, ref=ref, recursive=recursive, get_all=True)
            return [{"name": item["name"], "path": item["path"], "type": item["type"]} for item in items]
        except gitlab.exceptions.GitlabGetError:
            logger.warning(f"Could not list directory {path}")
            return []

    @retry(
        retry=retry_if_exception_type(gitlab.exceptions.GitlabError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def post_mr_comment(
        self,
        project_id: int,
        mr_iid: int,
        body: str,
    ) -> None:
        """Post a general comment on a merge request.

        Args:
            project_id: The GitLab project ID.
            mr_iid: The merge request internal ID.
            body: The comment body (Markdown supported).
        """
        mr = self._get_mr(project_id, mr_iid)
        mr.notes.create({"body": body})
        logger.info(f"Posted comment on MR !{mr_iid}")

    @retry(
        retry=retry_if_exception_type(gitlab.exceptions.GitlabError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def post_inline_comment(
        self,
        project_id: int,
        mr_iid: int,
        comment: InlineComment,
        diff_refs: dict[str, str],
    ) -> None:
        """Post an inline comment on a specific line in the MR diff.

        Args:
            project_id: The GitLab project ID.
            mr_iid: The merge request internal ID.
            comment: The inline comment to post.
            diff_refs: The diff refs (base_sha, head_sha, start_sha).
        """
        mr = self._get_mr(project_id, mr_iid)

        position = {
            "base_sha": diff_refs["base_sha"],
            "start_sha": diff_refs["start_sha"],
            "head_sha": diff_refs["head_sha"],
            "position_type": "text",
            "old_path": comment.file_path,
            "new_path": comment.file_path,
        }

        if comment.line_type == "new":
            position["new_line"] = comment.line_number
        else:
            position["old_line"] = comment.line_number

        try:
            mr.discussions.create(
                {
                    "body": comment.format_for_gitlab(),
                    "position": position,
                }
            )
            logger.info(
                f"Posted inline comment on {comment.file_path}:{comment.line_number}"
            )
        except gitlab.exceptions.GitlabCreateError as e:
            # Log but don't fail - inline comments can fail for various reasons
            logger.warning(
                f"Could not post inline comment on {comment.file_path}:{comment.line_number}: {e}"
            )

    def get_diff_refs(self, project_id: int, mr_iid: int) -> dict[str, str]:
        """Get the diff refs for a merge request.

        Args:
            project_id: The GitLab project ID.
            mr_iid: The merge request internal ID.

        Returns:
            A dictionary with base_sha, head_sha, and start_sha.
        """
        mr = self._get_mr(project_id, mr_iid)
        refs = mr.diff_refs
        return {
            "base_sha": refs.get("base_sha", ""),
            "head_sha": refs.get("head_sha", ""),
            "start_sha": refs.get("start_sha", ""),
        }

    def check_user_exists(self, username: str) -> bool:
        """Check if a user exists in GitLab.

        Args:
            username: The username to check.

        Returns:
            True if the user exists, False otherwise.
        """
        users = self._gl.users.list(username=username)
        return len(list(users)) > 0
