# Gilfoyle - AI Code Review Agent

An AI-powered code review agent for GitLab Merge Requests, built with [Pydantic AI](https://ai.pydantic.dev/).

## Overview

Gilfoyle is an automated code review assistant that integrates with self-hosted GitLab instances. It provides intelligent, context-aware feedback on merge requests by:

- Analyzing code changes and providing inline comments
- Enforcing coding standards from project documentation
- Referencing Architecture Decision Records (ADRs) when relevant
- Incorporating task context from Teamwork

## Triggers

Gilfoyle can be triggered in two ways:

1. **Mention in Comments**: Comment `@gilfoyle` on any MR to request a review
2. **Assign as Reviewer**: Add `gilfoyle` as a reviewer on the MR

## Documentation

- [ADR-001: Gilfoyle AI Agent Architecture](docs/adr/001-gilfoyle-ai-agent-for-mr-review.md)

## Quick Start

```bash
# Clone the repository
git clone <repository-url>
cd gilfoyle

# Install dependencies with uv
uv sync

# Copy environment template
cp .env.example .env

# Edit .env with your configuration
# - GITLAB_URL
# - GITLAB_TOKEN
# - TEAMWORK_API_KEY
# - OPENAI_API_KEY (or ANTHROPIC_API_KEY)

# Run the service
uv run python -m gilfoyle.main
```

## Configuration

See `.env.example` for all available configuration options.

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

## License

[Add license information]
