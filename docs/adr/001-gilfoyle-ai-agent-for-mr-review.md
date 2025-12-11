# ADR-001: Gilfoyle - AI Agent for GitLab Merge Request Review

## Status

**Proposed**

## Date

2024-12-11

## Context

Our development team requires an automated code review assistant to improve code quality, enforce coding standards, and reduce the time developers spend on routine code reviews. The agent should integrate seamlessly with our self-hosted GitLab instance and provide intelligent, context-aware feedback on merge requests.

### Current Challenges

1. Manual code reviews are time-consuming and sometimes inconsistent
2. Coding standards are documented but not always followed or checked
3. Context from Teamwork tasks is often missing during reviews
4. Reviewers need to manually cross-reference ADRs and coding guidelines

### Requirements

1. **Trigger Mechanism**: The agent must be invoked by:
   - Mentioning `@gilfoyle` in MR comments
   - Assigning `gilfoyle` as a reviewer on the MR

2. **Code Review Capabilities**:
   - Analyze diff/changes in the MR
   - Leave inline comments on specific code blocks
   - Provide general MR-level feedback
   - Suggest improvements based on best practices

3. **Context Awareness**:
   - Read and understand project documentation from `docs/` folder
   - Apply coding standards defined in the repository
   - Reference existing ADRs when relevant

4. **Teamwork Integration**:
   - Extract task references from MR description
   - Fetch task details from Teamwork API (`projects.ebs-integrator.com`)
   - Include task context in the review process

## Decision

We will build **Gilfoyle**, an AI-powered code review agent using **Pydantic AI** framework, deployed as a service that integrates with our self-hosted GitLab instance via webhooks.

### Technology Stack

| Component | Technology | Version | Rationale |
|-----------|------------|---------|-----------|
| AI Framework | [Pydantic AI](https://ai.pydantic.dev/) | 1.30.1+ | Type-safe, structured outputs, tool support, async-first |
| LLM Provider | Anthropic Claude | claude-sonnet-4-20250514 | High-quality code understanding and review capabilities |
| Data Validation | Pydantic | 2.12.5+ | Type-safe data validation and settings |
| Runtime | Python | 3.11+ | Pydantic AI requirement, modern async support |
| Package Manager | `uv` | 0.9.17+ | Fast, reliable Python package management |
| Web Framework | FastAPI | 0.124.2+ | Webhook handling, health checks, async support |
| GitLab Integration | `python-gitlab` | 5.6.0+ | Official GitLab API client |
| HTTP Client | `httpx` | 0.28.1+ | Async HTTP client for Teamwork API |
| Teamwork Integration | REST API | - | Custom client for Teamwork API |
| Deployment | Docker + Kubernetes / Docker Compose | - | Container-based deployment for scalability |
| Configuration | Pydantic Settings | 2.8.1+ | Type-safe configuration management |

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              GitLab (Self-Hosted)                            │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────────────────────┐ │
│  │   MR Created │     │  MR Comment  │     │   Reviewer Assigned          │ │
│  │   /Updated   │     │  @gilfoyle   │     │   (gilfoyle)                 │ │
│  └──────┬───────┘     └──────┬───────┘     └──────────────┬───────────────┘ │
│         │                    │                            │                  │
│         └────────────────────┼────────────────────────────┘                  │
│                              │                                               │
│                              ▼                                               │
│                     ┌────────────────┐                                       │
│                     │    Webhook     │                                       │
│                     └────────┬───────┘                                       │
└──────────────────────────────┼───────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                         Gilfoyle AI Agent Service                             │
│                                                                               │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                         FastAPI Application                             │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐ │  │
│  │  │ Webhook Handler │  │ Health Check    │  │ Metrics Endpoint        │ │  │
│  │  └────────┬────────┘  └─────────────────┘  └─────────────────────────┘ │  │
│  └───────────┼────────────────────────────────────────────────────────────┘  │
│              │                                                                │
│              ▼                                                                │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                      Event Processor                                    │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐   │  │
│  │  │ • Validate webhook payload                                       │   │  │
│  │  │ • Check trigger conditions (@gilfoyle mention / reviewer assign) │   │  │
│  │  │ • Extract MR metadata                                            │   │  │
│  │  └─────────────────────────────────────────────────────────────────┘   │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│              │                                                                │
│              ▼                                                                │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                    Pydantic AI Agent (Gilfoyle)                         │  │
│  │                                                                         │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐   │  │
│  │  │                      Agent Definition                            │   │  │
│  │  │  • System Prompt (Code Reviewer Persona)                         │   │  │
│  │  │  • Result Schema (Structured Review Output)                      │   │  │
│  │  │  • Dependencies (GitLab client, Teamwork client, etc.)           │   │  │
│  │  └─────────────────────────────────────────────────────────────────┘   │  │
│  │                                                                         │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐   │  │
│  │  │                         Tools                                    │   │  │
│  │  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │   │  │
│  │  │  │ get_mr_diff     │  │ get_file_content│  │ read_docs       │  │   │  │
│  │  │  └─────────────────┘  └─────────────────┘  └─────────────────┘  │   │  │
│  │  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │   │  │
│  │  │  │ get_coding_std  │  │ get_adr_list    │  │ get_teamwork_   │  │   │  │
│  │  │  │                 │  │                 │  │ task            │  │   │  │
│  │  │  └─────────────────┘  └─────────────────┘  └─────────────────┘  │   │  │
│  │  │  ┌─────────────────┐  ┌─────────────────┐                       │   │  │
│  │  │  │ post_inline_    │  │ post_mr_comment │                       │   │  │
│  │  │  │ comment         │  │                 │                       │   │  │
│  │  │  └─────────────────┘  └─────────────────┘                       │   │  │
│  │  └─────────────────────────────────────────────────────────────────┘   │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│              │                                                                │
│              ▼                                                                │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                      Response Handler                                   │  │
│  │  • Format review comments                                               │  │
│  │  • Post inline comments on specific lines                               │  │
│  │  • Post summary comment on MR                                           │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│   GitLab API     │ │   Teamwork API   │ │   LLM Provider   │
│  (python-gitlab) │ │  (REST Client)   │ │  (OpenAI/Claude) │
└──────────────────┘ └──────────────────┘ └──────────────────┘
```

### Pydantic AI Agent Design

#### Agent Definition

```python
from pydantic_ai import Agent
from pydantic import BaseModel
from typing import List, Optional

class InlineComment(BaseModel):
    """A comment on a specific line of code."""
    file_path: str
    line_number: int
    line_type: Literal["old", "new"]  # old = deletion, new = addition
    comment: str
    severity: Literal["info", "suggestion", "warning", "error"]

class ReviewResult(BaseModel):
    """Structured output for MR review."""
    summary: str
    overall_assessment: Literal["approved", "needs_changes", "needs_discussion"]
    inline_comments: List[InlineComment]
    general_comments: List[str]
    referenced_standards: List[str]  # Links to docs/ADRs referenced
    task_context_used: bool

class ReviewDependencies(BaseModel):
    """Dependencies injected into the agent."""
    gitlab_client: GitLabClient
    teamwork_client: TeamworkClient
    project_id: int
    mr_iid: int

gilfoyle_agent = Agent(
    "anthropic:claude-sonnet-4-20250514",  # Recommended for code review
    deps_type=ReviewDependencies,
    result_type=ReviewResult,
    system_prompt="""
    You are Gilfoyle, a senior software engineer and code reviewer.
    Your personality is direct, technically precise, and slightly sardonic.
    
    Your responsibilities:
    1. Review code changes for bugs, security issues, and best practices
    2. Check adherence to project coding standards (available via tools)
    3. Reference relevant ADRs when architectural decisions are involved
    4. Consider task context from Teamwork when available
    5. Provide actionable, specific feedback with code examples when helpful
    
    Be thorough but not pedantic. Focus on issues that matter.
    """,
)
```

#### Tool Definitions

```python
@gilfoyle_agent.tool
async def get_mr_diff(ctx: RunContext[ReviewDependencies]) -> str:
    """Get the diff/changes for the merge request."""
    return await ctx.deps.gitlab_client.get_mr_diff(
        ctx.deps.project_id, 
        ctx.deps.mr_iid
    )

@gilfoyle_agent.tool
async def get_file_content(
    ctx: RunContext[ReviewDependencies], 
    file_path: str,
    ref: str = "HEAD"
) -> str:
    """Get the full content of a file from the repository."""
    return await ctx.deps.gitlab_client.get_file_content(
        ctx.deps.project_id,
        file_path,
        ref
    )

@gilfoyle_agent.tool
async def read_docs(ctx: RunContext[ReviewDependencies], path: str = "docs/") -> str:
    """Read documentation files from the repository's docs folder."""
    return await ctx.deps.gitlab_client.get_directory_contents(
        ctx.deps.project_id,
        path
    )

@gilfoyle_agent.tool
async def get_coding_standards(ctx: RunContext[ReviewDependencies]) -> str:
    """Get the project's coding standards document."""
    try:
        return await ctx.deps.gitlab_client.get_file_content(
            ctx.deps.project_id,
            "docs/CODING_STANDARDS.md"
        )
    except FileNotFoundError:
        return "No coding standards document found."

@gilfoyle_agent.tool
async def list_adrs(ctx: RunContext[ReviewDependencies]) -> List[str]:
    """List all Architecture Decision Records in the project."""
    return await ctx.deps.gitlab_client.list_files(
        ctx.deps.project_id,
        "docs/adr/"
    )

@gilfoyle_agent.tool
async def get_adr_content(
    ctx: RunContext[ReviewDependencies], 
    adr_filename: str
) -> str:
    """Get the content of a specific ADR."""
    return await ctx.deps.gitlab_client.get_file_content(
        ctx.deps.project_id,
        f"docs/adr/{adr_filename}"
    )

@gilfoyle_agent.tool
async def get_teamwork_task(
    ctx: RunContext[ReviewDependencies], 
    task_id: str
) -> dict:
    """Fetch task details from Teamwork if a task ID is referenced."""
    return await ctx.deps.teamwork_client.get_task(task_id)
```

### GitLab Webhook Configuration

The agent will subscribe to the following GitLab webhook events:

| Event | Trigger Condition |
|-------|-------------------|
| `note` (Comment) | Check if comment body contains `@gilfoyle` |
| `merge_request` | Check if `reviewers` array contains `gilfoyle` user |

#### Webhook Payload Processing

```python
async def process_webhook(payload: dict) -> None:
    event_type = payload.get("object_kind")
    
    if event_type == "note":
        # Comment event
        if "@gilfoyle" in payload["object_attributes"]["note"]:
            await trigger_review(
                project_id=payload["project"]["id"],
                mr_iid=payload["merge_request"]["iid"]
            )
    
    elif event_type == "merge_request":
        # MR event - check if gilfoyle was added as reviewer
        reviewers = payload["object_attributes"].get("reviewers", [])
        if any(r["username"] == "gilfoyle" for r in reviewers):
            await trigger_review(
                project_id=payload["project"]["id"],
                mr_iid=payload["object_attributes"]["iid"]
            )
```

### Inline Comments Implementation

GitLab's Discussion API allows posting comments on specific lines:

```python
async def post_inline_comment(
    gitlab_client: GitLabClient,
    project_id: int,
    mr_iid: int,
    comment: InlineComment,
    diff_refs: dict
) -> None:
    """Post an inline comment on a specific line in the MR diff."""
    await gitlab_client.create_mr_discussion(
        project_id=project_id,
        mr_iid=mr_iid,
        body=f"**[{comment.severity.upper()}]** {comment.comment}",
        position={
            "base_sha": diff_refs["base_sha"],
            "start_sha": diff_refs["start_sha"],
            "head_sha": diff_refs["head_sha"],
            "position_type": "text",
            "new_path": comment.file_path,
            "new_line": comment.line_number if comment.line_type == "new" else None,
            "old_path": comment.file_path,
            "old_line": comment.line_number if comment.line_type == "old" else None,
        }
    )
```

### Teamwork Integration

#### Task Reference Detection

Parse MR description for Teamwork task references:

```python
import re

TEAMWORK_PATTERNS = [
    r"https://projects\.ebs-integrator\.com/[^\s]*tasks/(\d+)",
    r"#TW-(\d+)",
    r"TW-(\d+)",
    r"task[:\s]+(\d+)",
]

def extract_task_ids(description: str) -> List[str]:
    """Extract Teamwork task IDs from MR description."""
    task_ids = []
    for pattern in TEAMWORK_PATTERNS:
        matches = re.findall(pattern, description, re.IGNORECASE)
        task_ids.extend(matches)
    return list(set(task_ids))
```

#### Teamwork API Client

```python
class TeamworkClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url  # https://projects.ebs-integrator.com
        self.api_key = api_key
    
    async def get_task(self, task_id: str) -> dict:
        """Fetch task details from Teamwork API."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/tasks/{task_id}.json",
                auth=(self.api_key, ""),
            )
            response.raise_for_status()
            return response.json()["todo-item"]
```

### Project Structure

```
gilfoyle/
├── pyproject.toml
├── uv.lock
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── README.md
├── src/
│   └── gilfoyle/
│       ├── __init__.py
│       ├── main.py              # FastAPI application entry point
│       ├── config.py            # Pydantic Settings configuration
│       ├── agent/
│       │   ├── __init__.py
│       │   ├── gilfoyle.py      # Pydantic AI agent definition
│       │   ├── tools.py         # Agent tools
│       │   └── prompts.py       # System prompts and templates
│       ├── clients/
│       │   ├── __init__.py
│       │   ├── gitlab.py        # GitLab API client
│       │   └── teamwork.py      # Teamwork API client
│       ├── webhooks/
│       │   ├── __init__.py
│       │   ├── handlers.py      # Webhook event handlers
│       │   └── validators.py    # Payload validation
│       ├── models/
│       │   ├── __init__.py
│       │   ├── review.py        # Review result models
│       │   └── events.py        # Webhook event models
│       └── utils/
│           ├── __init__.py
│           └── parsing.py       # Task ID extraction, etc.
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_agent.py
│   ├── test_webhooks.py
│   └── test_clients.py
└── docs/
    ├── setup.md
    ├── configuration.md
    └── development.md
```

### Configuration

```python
# src/gilfoyle/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr

class Settings(BaseSettings):
    """Gilfoyle AI Agent Configuration."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    # Application
    app_name: str = "Gilfoyle"
    debug: bool = False
    
    # GitLab
    gitlab_url: str  # e.g., https://gitlab.company.com
    gitlab_token: SecretStr
    gitlab_webhook_secret: SecretStr
    gilfoyle_user_id: int  # GitLab user ID for gilfoyle
    
    # Teamwork
    teamwork_url: str = "https://projects.ebs-integrator.com"
    teamwork_api_key: SecretStr
    
    # LLM Configuration
    llm_provider: str = "anthropic"  # "anthropic" or "openai"
    anthropic_api_key: SecretStr | None = None
    openai_api_key: SecretStr | None = None
    llm_model: str = "claude-sonnet-4-20250514"  # or "gpt-4o" for OpenAI
    
    # Observability
    log_level: str = "INFO"
    
    @property
    def llm_model_string(self) -> str:
        """Return the full model string for Pydantic AI."""
        return f"{self.llm_provider}:{self.llm_model}"
```

### Deployment

#### Docker Compose (Development/Simple Deployment)

```yaml
version: "3.8"
services:
  gilfoyle:
    build: .
    ports:
      - "8000:8000"
    environment:
      - GITLAB_URL=${GITLAB_URL}
      - GITLAB_TOKEN=${GITLAB_TOKEN}
      - GITLAB_WEBHOOK_SECRET=${GITLAB_WEBHOOK_SECRET}
      - TEAMWORK_URL=${TEAMWORK_URL}
      - TEAMWORK_API_KEY=${TEAMWORK_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

#### GitLab Webhook Setup

1. Navigate to GitLab Project → Settings → Webhooks
2. Add webhook URL: `https://gilfoyle.internal.company.com/webhook`
3. Secret Token: Use `GITLAB_WEBHOOK_SECRET`
4. Triggers: ✓ Comments, ✓ Merge request events
5. SSL verification: Enable

## Consequences

### Positive

1. **Consistent Reviews**: All MRs reviewed by Gilfoyle will receive consistent feedback based on documented standards
2. **Time Savings**: Developers get immediate feedback without waiting for human reviewers
3. **Context-Aware**: Integration with Teamwork provides task context for better reviews
4. **Self-Documenting**: Agent references ADRs and coding standards, reinforcing their importance
5. **Type-Safe**: Pydantic AI provides structured, validated outputs
6. **Scalable**: Can handle multiple concurrent reviews
7. **Extensible**: Easy to add new tools and capabilities

### Negative

1. **LLM Costs**: Each review incurs LLM API costs (can be mitigated with model selection)
2. **Latency**: Reviews may take 30-60 seconds depending on MR size
3. **Maintenance**: Requires maintaining GitLab user account and webhook configuration
4. **False Positives**: AI may occasionally flag non-issues (can be improved with feedback)

### Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| LLM hallucinations | Structured output validation, human review for critical changes |
| Webhook downtime | Health checks, retry logic, alerting |
| API rate limits | Request queuing, exponential backoff |
| Secret exposure | Secret management (Vault/K8s secrets), never log secrets |
| Over-reliance on AI | Position as assistant, not replacement for human review |

## Alternatives Considered

### 1. GitHub Copilot for PRs
- **Rejected**: Not available for self-hosted GitLab

### 2. Custom LLM Integration (Direct API)
- **Rejected**: Pydantic AI provides better structure, tool support, and type safety

### 3. LangChain-based Agent
- **Rejected**: More complex, Pydantic AI is simpler and more aligned with our Pydantic usage

### 4. GitLab's Built-in AI Features
- **Rejected**: Requires GitLab Ultimate license and GitLab.com, not available for self-hosted

## Implementation Plan

### Phase 1: Core Agent (Week 1-2)
- [ ] Set up project structure with `uv`
- [ ] Implement basic Pydantic AI agent with review capability
- [ ] Create GitLab client with MR diff fetching
- [ ] Implement webhook handler for comment triggers

### Phase 2: GitLab Integration (Week 2-3)
- [ ] Implement inline comment posting
- [ ] Add reviewer assignment trigger
- [ ] Set up GitLab webhook configuration
- [ ] Create `gilfoyle` GitLab user account

### Phase 3: Documentation Integration (Week 3)
- [ ] Implement docs folder reading tool
- [ ] Add ADR listing and reading tools
- [ ] Implement coding standards tool

### Phase 4: Teamwork Integration (Week 3-4)
- [ ] Create Teamwork API client
- [ ] Implement task ID extraction from MR descriptions
- [ ] Add task context to review process

### Phase 5: Deployment & Testing (Week 4)
- [ ] Containerize application
- [ ] Set up deployment pipeline
- [ ] Integration testing with test GitLab project
- [ ] Documentation and team onboarding

## References

- [Pydantic AI Documentation](https://ai.pydantic.dev/)
- [GitLab Webhooks Documentation](https://docs.gitlab.com/ee/user/project/integrations/webhooks.html)
- [GitLab Discussions API](https://docs.gitlab.com/ee/api/discussions.html)
- [Teamwork API Documentation](https://developer.teamwork.com/)
- [python-gitlab Library](https://python-gitlab.readthedocs.io/)
- [Setup and Testing Guide](../SETUP_AND_TESTING_GUIDE.md) - Comprehensive setup, API key generation, and testing instructions

## Decision Makers

- [Add team members who should approve this ADR]

## Changelog

| Date | Author | Description |
|------|--------|-------------|
| 2024-12-11 | - | Initial proposal |
