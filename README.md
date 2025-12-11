# Gilfoyle - AI Code Review Agent

An AI-powered code review agent for GitLab Merge Requests, built with [Pydantic AI](https://ai.pydantic.dev/).

## Overview

Gilfoyle is an automated code review assistant that integrates with self-hosted GitLab instances. It provides intelligent, context-aware feedback on merge requests by:

- Analyzing code changes and providing inline comments
- Enforcing coding standards from project documentation
- Referencing Architecture Decision Records (ADRs) when relevant
- Incorporating task context from Teamwork

## Technology Stack

| Package | Version |
|---------|---------|
| Python | 3.11+ |
| uv | 0.9.17+ |
| pydantic-ai | 1.30.1+ |
| pydantic | 2.12.5+ |
| fastapi | 0.124.2+ |

## Triggers

Gilfoyle can be triggered in two ways:

1. **Mention in Comments**: Comment `@gilfoyle` on any MR to request a review
2. **Assign as Reviewer**: Add `gilfoyle` as a reviewer on the MR

## Documentation

| Document | Description |
|----------|-------------|
| [ADR-001: Architecture](docs/adr/001-gilfoyle-ai-agent-for-mr-review.md) | Architecture Decision Record for Gilfoyle |
| [Setup & Testing Guide](docs/SETUP_AND_TESTING_GUIDE.md) | Complete setup, API keys, and testing instructions |
| [ADR Template](docs/adr/000-adr-template.md) | Template for future ADRs |

## Quick Start

```bash
# Clone the repository
git clone <repository-url>
cd gilfoyle

# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies with uv
uv sync

# Copy environment template
cp .env.example .env

# Edit .env with your configuration (see Setup Guide for details)
# Required variables:
# - GITLAB_URL, GITLAB_TOKEN, GITLAB_WEBHOOK_SECRET
# - ANTHROPIC_API_KEY
# - TEAMWORK_API_KEY, TEAMWORK_URL

# Run the service
uv run python -m gilfoyle.main
```

## Required API Keys

| Key | Where to Get | Permissions Needed |
|-----|--------------|-------------------|
| `ANTHROPIC_API_KEY` | [Anthropic Console](https://console.anthropic.com/) | Messages API access |
| `GITLAB_TOKEN` | GitLab → User Settings → Access Tokens | `api`, `read_repository`, `write_repository` |
| `TEAMWORK_API_KEY` | Teamwork → Settings → API | Read access to tasks |

See the [Setup & Testing Guide](docs/SETUP_AND_TESTING_GUIDE.md) for detailed instructions.

## Configuration

See `.env.example` for all available configuration options.

```bash
# Required
GITLAB_URL=https://gitlab.your-domain.com
GITLAB_TOKEN=glpat-xxxxxxxxxxxxxxxxxxxx
GITLAB_WEBHOOK_SECRET=your-webhook-secret
GILFOYLE_USER_ID=123
ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxx
TEAMWORK_URL=https://projects.ebs-integrator.com
TEAMWORK_API_KEY=tkn.xxxxxxxxxxxxxxxxxxxx

# Optional
LLM_MODEL=claude-sonnet-4-20250514
LOG_LEVEL=INFO
```

## Development

```bash
# Install dev dependencies
uv sync --dev

# Run tests
uv run pytest

# Run linting
uv run ruff check .

# Run type checking
uv run mypy src/
```

## CI/CD

The project includes a GitLab CI/CD pipeline (`.gitlab-ci.yml`) with:

- **Validate**: Linting and type checking
- **Build**: Docker image building
- **Test**: Unit and integration tests
- **Demo**: Live demonstration of Gilfoyle capabilities
- **Deploy**: Staging and production deployment

## License

[Add license information]
