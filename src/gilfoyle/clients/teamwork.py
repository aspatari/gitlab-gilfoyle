"""Teamwork API client for fetching task details."""

import logging
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


class TeamworkClientError(Exception):
    """Base exception for Teamwork client errors."""


class TeamworkClient:
    """Client for interacting with the Teamwork API."""

    def __init__(self, base_url: str, api_key: str) -> None:
        """Initialize the Teamwork client.

        Args:
            base_url: The Teamwork instance URL (e.g., https://projects.ebs-integrator.com).
            api_key: The Teamwork API key.
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            auth=(api_key, ""),  # Teamwork uses API key as username with empty password
            timeout=30.0,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> "TeamworkClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.close()

    @retry(
        retry=retry_if_exception_type(httpx.HTTPError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def get_task(self, task_id: str) -> dict[str, Any]:
        """Fetch task details from Teamwork.

        Args:
            task_id: The Teamwork task ID.

        Returns:
            A dictionary with task details.

        Raises:
            TeamworkClientError: If the task cannot be retrieved.
        """
        try:
            response = await self._client.get(f"/tasks/{task_id}.json")
            response.raise_for_status()
            data = response.json()
            task = data.get("todo-item", {})

            return {
                "id": task.get("id"),
                "title": task.get("content", ""),
                "description": task.get("description", ""),
                "status": task.get("status", ""),
                "priority": task.get("priority", ""),
                "project_name": task.get("project-name", ""),
                "project_id": task.get("project-id"),
                "tasklist_name": task.get("todo-list-name", ""),
                "creator": task.get("creator-firstname", "") + " " + task.get("creator-lastname", ""),
                "responsible": self._get_responsible_party(task),
                "due_date": task.get("due-date", ""),
                "tags": [tag.get("name", "") for tag in task.get("tags", [])],
                "completed": task.get("completed", False),
            }
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Task {task_id} not found")
                raise TeamworkClientError(f"Task not found: {task_id}") from e
            logger.error(f"Error fetching task {task_id}: {e}")
            raise TeamworkClientError(f"Failed to fetch task: {e}") from e
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching task {task_id}: {e}")
            raise TeamworkClientError(f"HTTP error: {e}") from e

    def _get_responsible_party(self, task: dict[str, Any]) -> str:
        """Extract the responsible party name from a task."""
        responsible = task.get("responsible-party-names", "")
        if responsible:
            return responsible
        # Fallback to first assignee
        assignees = task.get("predecessors", [])
        if assignees:
            first = assignees[0]
            return f"{first.get('first-name', '')} {first.get('last-name', '')}"
        return "Unassigned"

    async def get_task_comments(self, task_id: str) -> list[dict[str, Any]]:
        """Fetch comments on a task.

        Args:
            task_id: The Teamwork task ID.

        Returns:
            A list of comment dictionaries.
        """
        try:
            response = await self._client.get(f"/tasks/{task_id}/comments.json")
            response.raise_for_status()
            data = response.json()
            comments = data.get("comments", [])

            return [
                {
                    "id": c.get("id"),
                    "body": c.get("body", ""),
                    "author": c.get("author-firstname", "") + " " + c.get("author-lastname", ""),
                    "date": c.get("datetime", ""),
                }
                for c in comments
            ]
        except httpx.HTTPError as e:
            logger.warning(f"Could not fetch comments for task {task_id}: {e}")
            return []

    async def verify_connection(self) -> bool:
        """Verify the API connection is working.

        Returns:
            True if the connection is successful, False otherwise.
        """
        try:
            response = await self._client.get("/me.json")
            response.raise_for_status()
            data = response.json()
            person = data.get("person", {})
            name = f"{person.get('first-name', '')} {person.get('last-name', '')}"
            logger.info(f"Connected to Teamwork as {name}")
            return True
        except httpx.HTTPError as e:
            logger.error(f"Failed to connect to Teamwork: {e}")
            return False

    def format_task_context(self, task: dict[str, Any]) -> str:
        """Format task details as context for the AI agent.

        Args:
            task: The task dictionary from get_task().

        Returns:
            A formatted string with task context.
        """
        lines = [
            f"## Teamwork Task: {task.get('title', 'Unknown')}",
            "",
            f"**Task ID:** {task.get('id')}",
            f"**Project:** {task.get('project_name', 'Unknown')}",
            f"**Status:** {task.get('status', 'Unknown')}",
            f"**Priority:** {task.get('priority', 'Normal')}",
            f"**Assigned to:** {task.get('responsible', 'Unassigned')}",
        ]

        if task.get("due_date"):
            lines.append(f"**Due Date:** {task.get('due_date')}")

        if task.get("tags"):
            lines.append(f"**Tags:** {', '.join(task.get('tags', []))}")

        if task.get("description"):
            lines.extend(["", "### Description", task.get("description", "")])

        return "\n".join(lines)
