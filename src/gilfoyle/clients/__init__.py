"""External API clients."""

from gilfoyle.clients.gitlab import GitLabClient
from gilfoyle.clients.teamwork import TeamworkClient

__all__ = ["GitLabClient", "TeamworkClient"]
