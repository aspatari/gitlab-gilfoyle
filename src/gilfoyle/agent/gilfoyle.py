"""Gilfoyle AI Agent definition using Pydantic AI."""

import logging

from pydantic_ai import Agent

from gilfoyle.agent.prompts import GILFOYLE_SYSTEM_PROMPT, REVIEW_USER_PROMPT_TEMPLATE
from gilfoyle.agent.tools import (
    ReviewDependencies,
    get_adr_content,
    get_coding_standards,
    get_file_content,
    get_mr_diff,
    get_teamwork_task,
    list_adrs,
    read_documentation,
)
from gilfoyle.clients.gitlab import GitLabClient
from gilfoyle.clients.teamwork import TeamworkClient
from gilfoyle.config import Settings
from gilfoyle.models.review import ReviewContext, ReviewResult
from gilfoyle.utils.parsing import extract_task_ids

logger = logging.getLogger(__name__)


class GilfoyleAgent:
    """The Gilfoyle AI code review agent."""

    def __init__(self, settings: Settings) -> None:
        """Initialize the Gilfoyle agent.

        Args:
            settings: Application settings.
        """
        self.settings = settings
        self._agent = self._create_agent()
        self._gitlab_client: GitLabClient | None = None
        self._teamwork_client: TeamworkClient | None = None

    def _create_agent(self) -> Agent[ReviewDependencies, ReviewResult]:
        """Create the Pydantic AI agent with tools."""
        agent: Agent[ReviewDependencies, ReviewResult] = Agent(
            self.settings.llm_model_string,
            deps_type=ReviewDependencies,
            output_type=ReviewResult,
            system_prompt=GILFOYLE_SYSTEM_PROMPT,
        )

        # Register tools
        agent.tool(get_mr_diff)
        agent.tool(get_file_content)
        agent.tool(read_documentation)
        agent.tool(get_coding_standards)
        agent.tool(list_adrs)
        agent.tool(get_adr_content)
        agent.tool(get_teamwork_task)

        return agent

    def _get_gitlab_client(self) -> GitLabClient:
        """Get or create the GitLab client."""
        if self._gitlab_client is None:
            self._gitlab_client = GitLabClient(
                url=self.settings.gitlab_url,
                token=self.settings.gitlab_token.get_secret_value(),
            )
        return self._gitlab_client

    def _get_teamwork_client(self) -> TeamworkClient:
        """Get or create the Teamwork client."""
        if self._teamwork_client is None:
            self._teamwork_client = TeamworkClient(
                base_url=self.settings.teamwork_url,
                api_key=self.settings.teamwork_api_key.get_secret_value(),
            )
        return self._teamwork_client

    async def review_merge_request(
        self,
        project_id: int,
        mr_iid: int,
    ) -> ReviewResult:
        """Perform a code review on a merge request.

        Args:
            project_id: The GitLab project ID.
            mr_iid: The merge request internal ID.

        Returns:
            The structured review result.
        """
        gitlab_client = self._get_gitlab_client()
        teamwork_client = self._get_teamwork_client()

        # Get MR details
        mr_details = gitlab_client.get_mr_details(project_id, mr_iid)

        # Extract task IDs from MR description
        task_ids = extract_task_ids(mr_details.get("description", ""))

        # Build review context
        context = ReviewContext(
            project_id=project_id,
            mr_iid=mr_iid,
            mr_title=mr_details.get("title", ""),
            mr_description=mr_details.get("description", ""),
            source_branch=mr_details.get("source_branch", ""),
            target_branch=mr_details.get("target_branch", ""),
            author_username=mr_details.get("author", ""),
            task_ids=task_ids,
        )

        # Prepare task context string
        task_context = ""
        if task_ids:
            task_context = f"\n## Referenced Tasks\nTask IDs found in description: {', '.join(task_ids)}\nUse get_teamwork_task(task_id) to fetch details."

        # Build the user prompt
        user_prompt = REVIEW_USER_PROMPT_TEMPLATE.format(
            title=context.mr_title,
            author=context.author_username,
            source_branch=context.source_branch,
            target_branch=context.target_branch,
            description=context.mr_description or "_No description provided_",
            task_context=task_context,
        )

        # Create dependencies
        deps = ReviewDependencies(
            gitlab_client=gitlab_client,
            teamwork_client=teamwork_client,
            project_id=project_id,
            mr_iid=mr_iid,
            source_branch=context.source_branch,
            target_branch=context.target_branch,
        )

        logger.info(f"Starting review of MR !{mr_iid} in project {project_id}")

        # Run the agent
        result = await self._agent.run(user_prompt, deps=deps)

        logger.info(
            f"Review completed for MR !{mr_iid}: {result.data.overall_assessment}"
        )

        return result.data

    async def post_review(
        self,
        project_id: int,
        mr_iid: int,
        review: ReviewResult,
    ) -> None:
        """Post the review results to the merge request.

        Args:
            project_id: The GitLab project ID.
            mr_iid: The merge request internal ID.
            review: The review result to post.
        """
        gitlab_client = self._get_gitlab_client()

        # Get diff refs for inline comments
        diff_refs = gitlab_client.get_diff_refs(project_id, mr_iid)

        # Post inline comments first
        for comment in review.inline_comments:
            gitlab_client.post_inline_comment(
                project_id=project_id,
                mr_iid=mr_iid,
                comment=comment,
                diff_refs=diff_refs,
            )

        # Post the summary comment
        summary = review.format_summary_comment()
        gitlab_client.post_mr_comment(
            project_id=project_id,
            mr_iid=mr_iid,
            body=summary,
        )

        logger.info(f"Posted review to MR !{mr_iid}")

    async def close(self) -> None:
        """Clean up resources."""
        if self._teamwork_client is not None:
            await self._teamwork_client.close()


def create_agent(settings: Settings) -> GilfoyleAgent:
    """Factory function to create a Gilfoyle agent.

    Args:
        settings: Application settings.

    Returns:
        A configured GilfoyleAgent instance.
    """
    return GilfoyleAgent(settings)
