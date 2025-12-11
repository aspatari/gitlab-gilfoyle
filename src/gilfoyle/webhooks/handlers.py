"""Webhook event handlers for Gilfoyle."""

import asyncio
import logging
from typing import Any

from gilfoyle.agent.gilfoyle import GilfoyleAgent
from gilfoyle.config import Settings
from gilfoyle.models.events import (
    MergeRequestEvent,
    NoteEvent,
    parse_webhook_event,
)

logger = logging.getLogger(__name__)


class WebhookHandler:
    """Handler for GitLab webhook events."""

    def __init__(self, settings: Settings, agent: GilfoyleAgent) -> None:
        """Initialize the webhook handler.

        Args:
            settings: Application settings.
            agent: The Gilfoyle agent instance.
        """
        self.settings = settings
        self.agent = agent
        self._active_reviews: set[str] = set()
        self._lock = asyncio.Lock()

    def _get_review_key(self, project_id: int, mr_iid: int) -> str:
        """Get a unique key for tracking active reviews."""
        return f"{project_id}:{mr_iid}"

    async def _is_review_in_progress(self, project_id: int, mr_iid: int) -> bool:
        """Check if a review is already in progress for this MR."""
        async with self._lock:
            key = self._get_review_key(project_id, mr_iid)
            return key in self._active_reviews

    async def _start_review(self, project_id: int, mr_iid: int) -> bool:
        """Mark a review as started. Returns False if already in progress."""
        async with self._lock:
            key = self._get_review_key(project_id, mr_iid)
            if key in self._active_reviews:
                return False
            if len(self._active_reviews) >= self.settings.max_concurrent_reviews:
                logger.warning("Max concurrent reviews reached, queuing...")
            self._active_reviews.add(key)
            return True

    async def _end_review(self, project_id: int, mr_iid: int) -> None:
        """Mark a review as completed."""
        async with self._lock:
            key = self._get_review_key(project_id, mr_iid)
            self._active_reviews.discard(key)

    async def handle_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Handle an incoming webhook event.

        Args:
            payload: The webhook payload.

        Returns:
            A response dictionary with status information.
        """
        event = parse_webhook_event(payload)

        if event is None:
            return {
                "status": "ignored",
                "reason": f"Unsupported event type: {payload.get('object_kind')}",
            }

        if isinstance(event, NoteEvent):
            return await self._handle_note_event(event)
        elif isinstance(event, MergeRequestEvent):
            return await self._handle_mr_event(event)

        return {"status": "ignored", "reason": "Unknown event type"}

    async def _handle_note_event(self, event: NoteEvent) -> dict[str, Any]:
        """Handle a note (comment) event.

        Triggers a review if Gilfoyle is mentioned.
        """
        if not event.is_on_merge_request():
            return {"status": "ignored", "reason": "Note is not on a merge request"}

        if not event.mentions_user(self.settings.gilfoyle_username):
            return {"status": "ignored", "reason": "Gilfoyle not mentioned"}

        # Get project and MR info
        project_id = event.project.id
        mr_iid = event.merge_request.iid  # type: ignore

        logger.info(
            f"Gilfoyle mentioned in MR !{mr_iid} comment, triggering review"
        )

        return await self._trigger_review(project_id, mr_iid, trigger="mention")

    async def _handle_mr_event(self, event: MergeRequestEvent) -> dict[str, Any]:
        """Handle a merge request event.

        Triggers a review if Gilfoyle is added as a reviewer.
        """
        # Check if gilfoyle was added as a reviewer
        if not event.reviewer_was_added(self.settings.gilfoyle_username):
            return {
                "status": "ignored",
                "reason": "Gilfoyle not added as reviewer in this event",
            }

        project_id = event.project.id
        mr_iid = event.object_attributes.iid

        logger.info(
            f"Gilfoyle assigned as reviewer on MR !{mr_iid}, triggering review"
        )

        return await self._trigger_review(project_id, mr_iid, trigger="reviewer_assigned")

    async def _trigger_review(
        self,
        project_id: int,
        mr_iid: int,
        trigger: str,
    ) -> dict[str, Any]:
        """Trigger a code review for a merge request.

        Args:
            project_id: The GitLab project ID.
            mr_iid: The merge request internal ID.
            trigger: What triggered the review (for logging).

        Returns:
            A response dictionary with status information.
        """
        # Check if review is already in progress
        if await self._is_review_in_progress(project_id, mr_iid):
            return {
                "status": "skipped",
                "reason": "Review already in progress for this MR",
            }

        # Start the review
        if not await self._start_review(project_id, mr_iid):
            return {
                "status": "skipped",
                "reason": "Could not start review (already in progress)",
            }

        try:
            # Run the review asynchronously
            task = asyncio.create_task(
                self._run_review(project_id, mr_iid, trigger)
            )
            # Store task reference to prevent garbage collection
            self._background_tasks = getattr(self, "_background_tasks", set())
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

            return {
                "status": "accepted",
                "message": f"Review triggered for MR !{mr_iid}",
                "trigger": trigger,
            }

        except Exception as e:
            await self._end_review(project_id, mr_iid)
            logger.error(f"Error triggering review: {e}")
            return {
                "status": "error",
                "message": str(e),
            }

    async def _run_review(
        self,
        project_id: int,
        mr_iid: int,
        trigger: str,
    ) -> None:
        """Run the actual review process.

        This runs as a background task.
        """
        try:
            logger.info(f"Starting review for MR !{mr_iid} (trigger: {trigger})")

            # Perform the review
            review_result = await asyncio.wait_for(
                self.agent.review_merge_request(project_id, mr_iid),
                timeout=self.settings.review_timeout_seconds,
            )

            # Post the results
            await self.agent.post_review(project_id, mr_iid, review_result)

            logger.info(
                f"Review completed for MR !{mr_iid}: {review_result.overall_assessment}"
            )

        except TimeoutError:
            logger.error(f"Review timed out for MR !{mr_iid}")

        except Exception as e:
            logger.exception(f"Error during review of MR !{mr_iid}: {e}")

        finally:
            await self._end_review(project_id, mr_iid)
