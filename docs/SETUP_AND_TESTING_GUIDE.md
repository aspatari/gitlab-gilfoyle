# Gilfoyle AI Agent - Complete Setup and Testing Guide

This guide provides step-by-step instructions for setting up, configuring, and testing the Gilfoyle AI Agent on a self-hosted GitLab instance.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Package Versions](#package-versions)
3. [API Keys and Permissions](#api-keys-and-permissions)
4. [GitLab Setup](#gitlab-setup)
5. [Project Setup](#project-setup)
6. [CI/CD Demo Workflow](#cicd-demo-workflow)
7. [Testing Plan](#testing-plan)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

- Self-hosted GitLab instance (version 15.0+)
- Docker and Docker Compose installed
- Python 3.11+ installed
- `uv` package manager installed
- Access to create GitLab users and configure webhooks
- Anthropic API account (or OpenAI)
- Teamwork account with API access

### Install uv (Latest Version)

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with pip
pip install uv

# Verify installation
uv --version  # Should show 0.9.17 or later
```

---

## Package Versions

The project uses the following package versions (as of December 2024):

| Package | Version | Purpose |
|---------|---------|---------|
| `uv` | 0.9.17+ | Package manager and virtual environment |
| `pydantic` | 2.12.5+ | Data validation and settings |
| `pydantic-ai` | 1.30.1+ | AI agent framework |
| `fastapi` | 0.124.2+ | Web framework for webhooks |
| `python-gitlab` | 5.6.0+ | GitLab API client |
| `httpx` | 0.28.1+ | Async HTTP client |
| `uvicorn` | 0.34.0+ | ASGI server |

---

## API Keys and Permissions

### 1. Anthropic API Key

#### Where to Generate
1. Go to [Anthropic Console](https://console.anthropic.com/)
2. Sign in or create an account
3. Navigate to **API Keys** section
4. Click **Create Key**

#### Required Permissions
- **Usage**: Messages API access
- **Models**: `claude-sonnet-4-20250514`, `claude-3-5-haiku-20241022` (recommended for code review)
- **Rate Limits**: Ensure your plan supports sufficient requests/minute

#### Key Format
```
sk-ant-api03-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

#### Where to Store
```bash
# In .env file
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here

# Or as GitLab CI/CD variable (recommended for production)
# Settings → CI/CD → Variables → Add Variable
# Key: ANTHROPIC_API_KEY
# Value: sk-ant-api03-your-key-here
# Type: Variable
# Flags: ✓ Mask variable, ✓ Protect variable
```

---

### 2. GitLab Access Token (for Gilfoyle Bot)

#### Step 1: Create Gilfoyle User Account

1. Log in to GitLab as **Administrator**
2. Navigate to **Admin Area** → **Users** → **New User**
3. Fill in details:
   - **Name**: Gilfoyle
   - **Username**: `gilfoyle`
   - **Email**: `gilfoyle@your-domain.com` (can be a service email)
   - **Access Level**: Regular
4. Click **Create User**
5. Set a password for the account

#### Step 2: Generate Personal Access Token

1. Log in as the `gilfoyle` user
2. Navigate to **User Settings** → **Access Tokens**
3. Create a new token:
   - **Token name**: `gilfoyle-agent-token`
   - **Expiration date**: Set appropriate expiration (recommend 1 year, with rotation plan)
   - **Scopes** (required permissions):

| Scope | Permission | Why Needed |
|-------|------------|------------|
| `api` | Full API access | Read MRs, post comments, read files |
| `read_repository` | Read repository | Access file contents and diffs |
| `write_repository` | Write repository | Post inline comments on diffs |
| `read_user` | Read user info | Identify mentioned users |

4. Click **Create personal access token**
5. **Copy the token immediately** (it won't be shown again)

#### Token Format
```
glpat-xxxxxxxxxxxxxxxxxxxx
```

#### Where to Store
```bash
# In .env file (development)
GITLAB_TOKEN=glpat-your-token-here

# As GitLab CI/CD variable (production)
# Key: GITLAB_TOKEN
# Value: glpat-your-token-here
# Type: Variable
# Flags: ✓ Mask variable, ✓ Protect variable
```

---

### 3. GitLab Webhook Secret

#### Generate a Secure Secret

```bash
# Generate a random 32-character secret
openssl rand -hex 32
# Example output: a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6

# Or use Python
python3 -c "import secrets; print(secrets.token_hex(32))"
```

#### Where to Store
```bash
# In .env file
GITLAB_WEBHOOK_SECRET=your-generated-secret-here

# As GitLab CI/CD variable
# Key: GITLAB_WEBHOOK_SECRET
# Value: your-generated-secret
# Flags: ✓ Mask variable, ✓ Protect variable
```

---

### 4. Teamwork API Key

#### Where to Generate

1. Log in to [Teamwork](https://projects.ebs-integrator.com/)
2. Click your profile icon → **Settings**
3. Navigate to **API & Integrations** → **API**
4. Click **Create API Token** or **Show API Token**

#### Required Permissions
- **Read access** to:
  - Tasks
  - Projects
  - Task lists
  - Comments (optional, for context)

#### Key Format
Teamwork uses API tokens that can be used as the username in Basic Auth (with empty password):
```
tkn.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

#### Where to Store
```bash
# In .env file
TEAMWORK_API_KEY=tkn.your-teamwork-api-key
TEAMWORK_URL=https://projects.ebs-integrator.com

# As GitLab CI/CD variable
# Key: TEAMWORK_API_KEY
# Value: tkn.your-teamwork-api-key
# Flags: ✓ Mask variable, ✓ Protect variable
```

---

## GitLab Setup

### Step 1: Create Test Repository

1. Log in to your self-hosted GitLab
2. Click **New Project** → **Create blank project**
3. Fill in:
   - **Project name**: `gilfoyle-test-repo`
   - **Visibility**: Private (recommended for testing)
   - **Initialize with README**: ✓
4. Click **Create project**

### Step 2: Add Gilfoyle as Project Member

1. Navigate to your project
2. Go to **Settings** → **Members**
3. Click **Invite members**
4. Search for `gilfoyle`
5. Select role: **Developer** (minimum required)
6. Click **Invite**

### Step 3: Configure Webhook

1. Navigate to **Settings** → **Webhooks**
2. Click **Add new webhook**
3. Configure:

| Field | Value |
|-------|-------|
| **URL** | `https://gilfoyle.your-domain.com/webhook/gitlab` |
| **Secret token** | Your `GITLAB_WEBHOOK_SECRET` value |
| **Trigger** | ✓ Comments |
| | ✓ Merge request events |
| **SSL verification** | ✓ Enable (if using HTTPS) |

4. Click **Add webhook**

### Step 4: Configure CI/CD Variables

1. Navigate to **Settings** → **CI/CD**
2. Expand **Variables**
3. Add the following variables:

| Key | Value | Protected | Masked |
|-----|-------|-----------|--------|
| `ANTHROPIC_API_KEY` | `sk-ant-api03-...` | ✓ | ✓ |
| `GITLAB_TOKEN` | `glpat-...` | ✓ | ✓ |
| `GITLAB_WEBHOOK_SECRET` | `your-secret` | ✓ | ✓ |
| `TEAMWORK_API_KEY` | `tkn....` | ✓ | ✓ |
| `GITLAB_URL` | `https://gitlab.your-domain.com` | ✓ | ✗ |
| `TEAMWORK_URL` | `https://projects.ebs-integrator.com` | ✓ | ✗ |
| `GILFOYLE_USER_ID` | `123` (gilfoyle's GitLab user ID) | ✓ | ✗ |

#### Finding Gilfoyle's User ID

```bash
# Using GitLab API
curl --header "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  "https://gitlab.your-domain.com/api/v4/users?username=gilfoyle" \
  | jq '.[0].id'
```

---

## Project Setup

### Step 1: Initialize Project

```bash
# Create project directory
mkdir gilfoyle && cd gilfoyle

# Initialize with uv
uv init

# Create project structure
mkdir -p src/gilfoyle/{agent,clients,webhooks,models,utils}
mkdir -p tests docs
touch src/gilfoyle/__init__.py
touch src/gilfoyle/{agent,clients,webhooks,models,utils}/__init__.py
```

### Step 2: Configure pyproject.toml

```toml
[project]
name = "gilfoyle"
version = "0.1.0"
description = "AI-powered GitLab MR review agent"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.12.5",
    "pydantic-ai>=1.30.1",
    "pydantic-settings>=2.8.1",
    "fastapi>=0.124.2",
    "uvicorn[standard]>=0.34.0",
    "python-gitlab>=5.6.0",
    "httpx>=0.28.1",
    "anthropic>=0.52.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.5",
    "pytest-asyncio>=0.25.0",
    "pytest-cov>=6.1.0",
    "ruff>=0.11.12",
    "mypy>=1.16.0",
    "respx>=0.22.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP", "B", "C4", "SIM"]

[tool.mypy]
python_version = "3.11"
strict = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

### Step 3: Install Dependencies

```bash
# Install all dependencies
uv sync

# Install with dev dependencies
uv sync --dev

# Verify installation
uv run python -c "import pydantic_ai; print(f'pydantic-ai version: {pydantic_ai.__version__}')"
```

### Step 4: Create Environment File

```bash
# Create .env.example
cat > .env.example << 'EOF'
# ===========================================
# Gilfoyle AI Agent Configuration
# ===========================================

# Application Settings
APP_NAME=Gilfoyle
DEBUG=false
LOG_LEVEL=INFO

# GitLab Configuration
GITLAB_URL=https://gitlab.your-domain.com
GITLAB_TOKEN=glpat-xxxxxxxxxxxxxxxxxxxx
GITLAB_WEBHOOK_SECRET=your-webhook-secret-here
GILFOYLE_USER_ID=123

# Teamwork Configuration
TEAMWORK_URL=https://projects.ebs-integrator.com
TEAMWORK_API_KEY=tkn.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# LLM Configuration
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxxxxxxxxxx
LLM_MODEL=claude-sonnet-4-20250514

# Optional: OpenAI (if using OpenAI instead)
# LLM_PROVIDER=openai
# OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
# LLM_MODEL=gpt-4o
EOF

# Copy to .env for local development
cp .env.example .env
# Edit .env with your actual values
```

---

## CI/CD Demo Workflow

Create a `.gitlab-ci.yml` file that demonstrates the Gilfoyle agent functionality:

### `.gitlab-ci.yml`

```yaml
# ===========================================
# Gilfoyle AI Agent - CI/CD Demo Workflow
# ===========================================

stages:
  - validate
  - build
  - test
  - demo
  - deploy

variables:
  PYTHON_VERSION: "3.11"
  UV_VERSION: "0.9.17"
  # These are set in GitLab CI/CD Variables (masked)
  # ANTHROPIC_API_KEY: $ANTHROPIC_API_KEY
  # GITLAB_TOKEN: $GITLAB_TOKEN
  # TEAMWORK_API_KEY: $TEAMWORK_API_KEY

# ===========================================
# Templates
# ===========================================

.uv-setup: &uv-setup
  before_script:
    - pip install uv==$UV_VERSION
    - uv sync --dev
    - source .venv/bin/activate

# ===========================================
# Stage: Validate
# ===========================================

validate:lint:
  stage: validate
  image: python:${PYTHON_VERSION}
  <<: *uv-setup
  script:
    - echo "Running Ruff linter..."
    - uv run ruff check src/ tests/
    - uv run ruff format --check src/ tests/
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH

validate:typecheck:
  stage: validate
  image: python:${PYTHON_VERSION}
  <<: *uv-setup
  script:
    - echo "Running MyPy type checker..."
    - uv run mypy src/
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH

# ===========================================
# Stage: Build
# ===========================================

build:docker:
  stage: build
  image: docker:24
  services:
    - docker:24-dind
  variables:
    DOCKER_TLS_CERTDIR: "/certs"
  script:
    - docker build -t gilfoyle:${CI_COMMIT_SHA} .
    - docker tag gilfoyle:${CI_COMMIT_SHA} gilfoyle:latest
    # Push to registry if configured
    - |
      if [ -n "$CI_REGISTRY" ]; then
        docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
        docker tag gilfoyle:${CI_COMMIT_SHA} $CI_REGISTRY_IMAGE:${CI_COMMIT_SHA}
        docker push $CI_REGISTRY_IMAGE:${CI_COMMIT_SHA}
      fi
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"

# ===========================================
# Stage: Test
# ===========================================

test:unit:
  stage: test
  image: python:${PYTHON_VERSION}
  <<: *uv-setup
  script:
    - echo "Running unit tests..."
    - uv run pytest tests/unit/ -v --cov=src/gilfoyle --cov-report=xml
  coverage: '/TOTAL.*\s+(\d+%)/'
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH

test:integration:
  stage: test
  image: python:${PYTHON_VERSION}
  <<: *uv-setup
  script:
    - echo "Running integration tests..."
    - uv run pytest tests/integration/ -v
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
  needs:
    - test:unit

# ===========================================
# Stage: Demo - Gilfoyle Agent Demonstration
# ===========================================

demo:agent-health-check:
  stage: demo
  image: python:${PYTHON_VERSION}
  <<: *uv-setup
  script:
    - echo "=== Gilfoyle Agent Health Check ==="
    - |
      uv run python << 'PYTHON_SCRIPT'
      import asyncio
      from pydantic_ai import Agent

      async def test_agent():
          """Test that the agent can be initialized and run."""
          agent = Agent(
              "anthropic:claude-sonnet-4-20250514",
              system_prompt="You are a helpful assistant. Respond with 'OK' if you can hear me."
          )
          result = await agent.run("Hello, are you working?")
          print(f"Agent Response: {result.data}")
          assert "OK" in result.data.upper() or len(result.data) > 0
          print("✓ Agent health check passed!")

      asyncio.run(test_agent())
      PYTHON_SCRIPT
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
  allow_failure: true  # Don't block pipeline if API is down

demo:review-simulation:
  stage: demo
  image: python:${PYTHON_VERSION}
  <<: *uv-setup
  script:
    - echo "=== Simulating MR Review with Gilfoyle ==="
    - |
      uv run python << 'PYTHON_SCRIPT'
      import asyncio
      import os
      from pydantic import BaseModel
      from pydantic_ai import Agent
      from typing import Literal

      class ReviewComment(BaseModel):
          file: str
          line: int
          severity: Literal["info", "suggestion", "warning", "error"]
          comment: str

      class ReviewResult(BaseModel):
          summary: str
          verdict: Literal["approved", "needs_changes", "needs_discussion"]
          comments: list[ReviewComment]

      # Sample diff for demonstration
      SAMPLE_DIFF = '''
      diff --git a/src/utils.py b/src/utils.py
      --- a/src/utils.py
      +++ b/src/utils.py
      @@ -1,5 +1,10 @@
      +import os
      +
       def get_user_data(user_id):
      -    query = f"SELECT * FROM users WHERE id = {user_id}"
      +    # Fixed SQL injection vulnerability
      +    query = "SELECT * FROM users WHERE id = ?"
           return execute_query(query, [user_id])
      +
      +def get_api_key():
      +    return os.environ.get("API_KEY", "default-key-123")
      '''

      async def demo_review():
          agent = Agent(
              "anthropic:claude-sonnet-4-20250514",
              result_type=ReviewResult,
              system_prompt="""You are Gilfoyle, a senior code reviewer.
              Review the provided diff and identify:
              1. Security issues
              2. Best practice violations
              3. Potential bugs
              Be direct and specific. Provide actionable feedback."""
          )

          result = await agent.run(f"Review this code change:\n\n{SAMPLE_DIFF}")
          review = result.data

          print("=" * 60)
          print("GILFOYLE CODE REVIEW RESULTS")
          print("=" * 60)
          print(f"\n📋 Summary: {review.summary}")
          print(f"🎯 Verdict: {review.verdict.upper()}")
          print(f"\n💬 Comments ({len(review.comments)}):")
          for i, comment in enumerate(review.comments, 1):
              severity_emoji = {
                  "info": "ℹ️",
                  "suggestion": "💡",
                  "warning": "⚠️",
                  "error": "❌"
              }
              print(f"\n  {i}. [{severity_emoji[comment.severity]} {comment.severity.upper()}]")
              print(f"     File: {comment.file}, Line: {comment.line}")
              print(f"     {comment.comment}")
          print("\n" + "=" * 60)
          print("✓ Demo review completed successfully!")

      asyncio.run(demo_review())
      PYTHON_SCRIPT
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
  needs:
    - demo:agent-health-check
  allow_failure: true

demo:gitlab-api-test:
  stage: demo
  image: python:${PYTHON_VERSION}
  <<: *uv-setup
  script:
    - echo "=== Testing GitLab API Connection ==="
    - |
      uv run python << 'PYTHON_SCRIPT'
      import os
      import gitlab

      GITLAB_URL = os.environ.get("GITLAB_URL", "https://gitlab.com")
      GITLAB_TOKEN = os.environ.get("GITLAB_TOKEN")

      if not GITLAB_TOKEN:
          print("⚠️ GITLAB_TOKEN not set, skipping GitLab API test")
          exit(0)

      try:
          gl = gitlab.Gitlab(GITLAB_URL, private_token=GITLAB_TOKEN)
          gl.auth()
          user = gl.user
          print(f"✓ Connected to GitLab as: {user.username}")
          print(f"✓ GitLab URL: {GITLAB_URL}")

          # Test listing projects (limited)
          projects = gl.projects.list(membership=True, per_page=5)
          print(f"✓ Can access {len(projects)} projects")

          print("\n✓ GitLab API test passed!")
      except Exception as e:
          print(f"❌ GitLab API test failed: {e}")
          exit(1)
      PYTHON_SCRIPT
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
  allow_failure: true

demo:teamwork-api-test:
  stage: demo
  image: python:${PYTHON_VERSION}
  <<: *uv-setup
  script:
    - echo "=== Testing Teamwork API Connection ==="
    - |
      uv run python << 'PYTHON_SCRIPT'
      import os
      import httpx

      TEAMWORK_URL = os.environ.get("TEAMWORK_URL", "https://projects.ebs-integrator.com")
      TEAMWORK_API_KEY = os.environ.get("TEAMWORK_API_KEY")

      if not TEAMWORK_API_KEY:
          print("⚠️ TEAMWORK_API_KEY not set, skipping Teamwork API test")
          exit(0)

      try:
          with httpx.Client() as client:
              response = client.get(
                  f"{TEAMWORK_URL}/me.json",
                  auth=(TEAMWORK_API_KEY, "")
              )
              response.raise_for_status()
              data = response.json()
              user = data.get("person", {})
              print(f"✓ Connected to Teamwork as: {user.get('first-name', 'Unknown')} {user.get('last-name', '')}")
              print(f"✓ Teamwork URL: {TEAMWORK_URL}")
              print("\n✓ Teamwork API test passed!")
      except Exception as e:
          print(f"❌ Teamwork API test failed: {e}")
          exit(1)
      PYTHON_SCRIPT
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
  allow_failure: true

demo:full-workflow:
  stage: demo
  image: python:${PYTHON_VERSION}
  <<: *uv-setup
  script:
    - echo "=== Full Gilfoyle Workflow Demonstration ==="
    - |
      uv run python << 'PYTHON_SCRIPT'
      import asyncio
      import os
      import re
      from pydantic import BaseModel
      from pydantic_ai import Agent, RunContext
      from typing import Literal
      from dataclasses import dataclass

      # Models
      class InlineComment(BaseModel):
          file_path: str
          line_number: int
          line_type: Literal["old", "new"]
          comment: str
          severity: Literal["info", "suggestion", "warning", "error"]

      class ReviewResult(BaseModel):
          summary: str
          overall_assessment: Literal["approved", "needs_changes", "needs_discussion"]
          inline_comments: list[InlineComment]
          general_comments: list[str]
          referenced_standards: list[str]
          task_context_used: bool

      @dataclass
      class ReviewDeps:
          project_docs: str
          coding_standards: str
          task_info: str | None

      # Sample data for demonstration
      SAMPLE_CODING_STANDARDS = """
      # Coding Standards

      1. No hardcoded secrets or API keys
      2. Use parameterized queries for database access
      3. All functions must have docstrings
      4. Use type hints for function parameters and return values
      5. Handle exceptions explicitly, don't use bare except
      """

      SAMPLE_DIFF = '''
      diff --git a/app/api.py b/app/api.py
      --- a/app/api.py
      +++ b/app/api.py
      @@ -5,8 +5,15 @@ from fastapi import FastAPI
       app = FastAPI()

       @app.get("/users/{user_id}")
      -def get_user(user_id: int):
      -    return {"user_id": user_id}
      +async def get_user(user_id):
      +    try:
      +        query = f"SELECT * FROM users WHERE id = {user_id}"
      +        result = db.execute(query)
      +        return result
      +    except:
      +        return {"error": "Something went wrong"}
      +
      +API_KEY = "sk-secret-key-12345"
      '''

      SAMPLE_TASK = """
      Task #TW-1234: Implement user fetching endpoint
      Description: Add a new endpoint to fetch user details by ID.
      Acceptance Criteria:
      - Endpoint should be async
      - Should handle user not found cases
      - Should return proper error messages
      """

      # Create agent with tools
      agent = Agent(
          "anthropic:claude-sonnet-4-20250514",
          deps_type=ReviewDeps,
          result_type=ReviewResult,
          system_prompt="""You are Gilfoyle, a meticulous senior code reviewer.
          You have access to:
          - Project coding standards
          - Task context from the project management tool

          Review code changes thoroughly for:
          1. Security vulnerabilities
          2. Adherence to coding standards
          3. Best practices
          4. Task requirement fulfillment

          Be direct, specific, and reference the standards when applicable.
          Provide line-specific feedback when possible."""
      )

      @agent.tool
      async def get_coding_standards(ctx: RunContext[ReviewDeps]) -> str:
          """Get the project's coding standards."""
          return ctx.deps.coding_standards

      @agent.tool
      async def get_task_context(ctx: RunContext[ReviewDeps]) -> str:
          """Get the task context if available."""
          return ctx.deps.task_info or "No task context available."

      async def run_demo():
          print("=" * 70)
          print("GILFOYLE FULL WORKFLOW DEMONSTRATION")
          print("=" * 70)

          print("\n📄 MR Description: Implements TW-1234 - User endpoint")
          print("\n📝 Diff to review:")
          print(SAMPLE_DIFF)

          # Create dependencies
          deps = ReviewDeps(
              project_docs="docs/",
              coding_standards=SAMPLE_CODING_STANDARDS,
              task_info=SAMPLE_TASK
          )

          print("\n🤖 Running Gilfoyle review...")
          print("-" * 70)

          result = await agent.run(
              f"Review this merge request:\n\nDiff:\n{SAMPLE_DIFF}",
              deps=deps
          )

          review = result.data

          print(f"\n📋 SUMMARY:\n{review.summary}")
          print(f"\n🎯 VERDICT: {review.overall_assessment.upper()}")
          print(f"\n📚 Standards Referenced: {', '.join(review.referenced_standards) or 'None'}")
          print(f"📌 Task Context Used: {'Yes' if review.task_context_used else 'No'}")

          print(f"\n💬 INLINE COMMENTS ({len(review.inline_comments)}):")
          for comment in review.inline_comments:
              severity_map = {"info": "ℹ️", "suggestion": "💡", "warning": "⚠️", "error": "❌"}
              emoji = severity_map.get(comment.severity, "•")
              print(f"\n  {emoji} [{comment.severity.upper()}] {comment.file_path}:{comment.line_number}")
              print(f"     └─ {comment.comment}")

          if review.general_comments:
              print(f"\n📝 GENERAL COMMENTS:")
              for comment in review.general_comments:
                  print(f"  • {comment}")

          print("\n" + "=" * 70)
          print("✅ Full workflow demonstration completed!")
          print("=" * 70)

      asyncio.run(run_demo())
      PYTHON_SCRIPT
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
  needs:
    - demo:agent-health-check
    - demo:review-simulation

# ===========================================
# Stage: Deploy
# ===========================================

deploy:staging:
  stage: deploy
  image: docker:24
  services:
    - docker:24-dind
  script:
    - echo "Deploying to staging environment..."
    # Add your deployment commands here
    - echo "docker-compose -f docker-compose.staging.yml up -d"
  environment:
    name: staging
    url: https://gilfoyle-staging.your-domain.com
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
  when: manual

deploy:production:
  stage: deploy
  image: docker:24
  services:
    - docker:24-dind
  script:
    - echo "Deploying to production environment..."
    # Add your deployment commands here
    - echo "docker-compose -f docker-compose.prod.yml up -d"
  environment:
    name: production
    url: https://gilfoyle.your-domain.com
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
  when: manual
  needs:
    - deploy:staging
```

---

## Testing Plan

### Phase 1: Local Development Testing

#### Step 1: Environment Setup Verification

```bash
# 1. Verify uv installation
uv --version
# Expected: uv 0.9.17 or higher

# 2. Verify Python version
uv run python --version
# Expected: Python 3.11.x or higher

# 3. Verify dependencies installed
uv run python -c "import pydantic_ai; import fastapi; import gitlab; print('All dependencies OK')"
```

#### Step 2: API Key Validation

```bash
# Test Anthropic API Key
uv run python << 'EOF'
import os
from anthropic import Anthropic

client = Anthropic()  # Uses ANTHROPIC_API_KEY env var
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=100,
    messages=[{"role": "user", "content": "Say 'API working' if you can read this."}]
)
print(f"✓ Anthropic API: {response.content[0].text}")
EOF

# Test GitLab API Key
uv run python << 'EOF'
import os
import gitlab

gl = gitlab.Gitlab(os.environ["GITLAB_URL"], private_token=os.environ["GITLAB_TOKEN"])
gl.auth()
print(f"✓ GitLab API: Connected as {gl.user.username}")
EOF

# Test Teamwork API Key
uv run python << 'EOF'
import os
import httpx

response = httpx.get(
    f"{os.environ['TEAMWORK_URL']}/me.json",
    auth=(os.environ["TEAMWORK_API_KEY"], "")
)
data = response.json()
print(f"✓ Teamwork API: Connected as {data['person']['first-name']}")
EOF
```

#### Step 3: Unit Tests

```bash
# Run all unit tests
uv run pytest tests/unit/ -v

# Run with coverage
uv run pytest tests/unit/ -v --cov=src/gilfoyle --cov-report=html

# Open coverage report
open htmlcov/index.html
```

### Phase 2: Integration Testing

#### Step 1: Create Test MR in GitLab

```bash
# Clone the test repository
git clone https://gitlab.your-domain.com/your-group/gilfoyle-test-repo.git
cd gilfoyle-test-repo

# Create a test branch
git checkout -b test/gilfoyle-review-$(date +%s)

# Create a file with intentional issues for Gilfoyle to find
cat > src/example.py << 'EOF'
# Example file with issues for Gilfoyle to review

import os

def get_user(user_id):
    # SQL Injection vulnerability
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return execute(query)

# Hardcoded secret
API_KEY = "sk-secret-12345"

def process_data(data):
    try:
        return data.process()
    except:
        pass  # Silent exception
EOF

# Commit and push
git add .
git commit -m "Add example code for Gilfoyle review test"
git push -u origin test/gilfoyle-review-$(date +%s)
```

#### Step 2: Create MR with Task Reference

1. Go to GitLab → Your test repo → Create Merge Request
2. Title: `Test: Add example code for review`
3. Description:
   ```markdown
   ## Description
   This MR adds example code for testing Gilfoyle AI review.

   ## Related Task
   https://projects.ebs-integrator.com/app/tasks/12345

   ## Checklist
   - [ ] Code reviewed by Gilfoyle
   ```
4. Create the MR

#### Step 3: Trigger Gilfoyle Review

**Option A: Comment Trigger**
1. Go to the MR
2. Add a comment: `@gilfoyle please review this MR`
3. Wait for Gilfoyle to respond

**Option B: Reviewer Trigger**
1. Go to the MR
2. Edit MR → Add `gilfoyle` as Reviewer
3. Wait for Gilfoyle to respond

#### Step 4: Verify Review Output

Check that Gilfoyle:
- [ ] Posted a summary comment on the MR
- [ ] Added inline comments on specific lines
- [ ] Identified the SQL injection vulnerability
- [ ] Flagged the hardcoded API key
- [ ] Noted the silent exception handling
- [ ] Referenced coding standards (if available)
- [ ] Mentioned task context (if task ID was valid)

### Phase 3: Webhook Testing

#### Step 1: Start Local Server

```bash
# Start Gilfoyle server locally
uv run uvicorn src.gilfoyle.main:app --reload --port 8000

# In another terminal, expose with ngrok (for testing webhooks)
ngrok http 8000
```

#### Step 2: Update Webhook URL

1. Go to GitLab → Project → Settings → Webhooks
2. Edit the webhook URL to your ngrok URL: `https://xxxx.ngrok.io/webhook/gitlab`
3. Save

#### Step 3: Test Webhook Delivery

```bash
# Trigger a test event from GitLab
# Go to Settings → Webhooks → Test → Select "Merge request events"

# Check server logs for received webhook
```

#### Step 4: Verify Webhook Processing

```bash
# Check webhook signature validation
curl -X POST http://localhost:8000/webhook/gitlab \
  -H "Content-Type: application/json" \
  -H "X-Gitlab-Token: wrong-token" \
  -d '{"test": "data"}'
# Expected: 401 Unauthorized

# Check with correct token
curl -X POST http://localhost:8000/webhook/gitlab \
  -H "Content-Type: application/json" \
  -H "X-Gitlab-Token: $GITLAB_WEBHOOK_SECRET" \
  -d '{"object_kind": "note", "object_attributes": {"note": "@gilfoyle review"}}'
# Expected: 200 OK
```

### Phase 4: End-to-End Testing Checklist

| Test Case | Steps | Expected Result | Status |
|-----------|-------|-----------------|--------|
| **Agent Initialization** | Start server | Server starts without errors | ⬜ |
| **Webhook Receipt** | Send test webhook from GitLab | Webhook received and logged | ⬜ |
| **Comment Trigger** | Comment `@gilfoyle` on MR | Review triggered | ⬜ |
| **Reviewer Trigger** | Assign gilfoyle as reviewer | Review triggered | ⬜ |
| **Diff Fetching** | Trigger review on MR with changes | Diff fetched correctly | ⬜ |
| **Inline Comments** | Review code with issues | Inline comments posted | ⬜ |
| **Summary Comment** | Complete review | Summary posted on MR | ⬜ |
| **Docs Reading** | Have docs/ folder in repo | Standards referenced in review | ⬜ |
| **ADR Reading** | Have ADRs in docs/adr/ | ADRs referenced when relevant | ⬜ |
| **Task Extraction** | Include TW-123 in MR description | Task ID extracted | ⬜ |
| **Teamwork Integration** | Valid task reference | Task context included in review | ⬜ |
| **Error Handling** | Invalid MR/Project | Graceful error, no crash | ⬜ |
| **Rate Limiting** | Multiple rapid triggers | Requests queued properly | ⬜ |

### Phase 5: CI/CD Pipeline Testing

#### Step 1: Push CI Configuration

```bash
# Add the .gitlab-ci.yml to your repo
git add .gitlab-ci.yml
git commit -m "Add CI/CD pipeline with Gilfoyle demo"
git push
```

#### Step 2: Verify Pipeline Runs

1. Go to CI/CD → Pipelines
2. Check that all stages pass:
   - ✓ validate:lint
   - ✓ validate:typecheck
   - ✓ build:docker
   - ✓ test:unit
   - ✓ demo:agent-health-check
   - ✓ demo:review-simulation

#### Step 3: Review Demo Job Outputs

1. Click on `demo:full-workflow` job
2. Verify the Gilfoyle review output is displayed
3. Check that all checks passed

---

## Troubleshooting

### Common Issues

#### 1. Anthropic API Errors

```
Error: AuthenticationError: Invalid API key
```

**Solution:**
- Verify `ANTHROPIC_API_KEY` is set correctly
- Check key hasn't expired
- Ensure key has proper permissions

#### 2. GitLab Webhook Not Triggering

**Checklist:**
- [ ] Webhook URL is correct and accessible
- [ ] Secret token matches `GITLAB_WEBHOOK_SECRET`
- [ ] Required events are selected (Comments, MR events)
- [ ] SSL verification settings match your setup

**Debug:**
```bash
# Check webhook delivery history
# GitLab → Settings → Webhooks → Edit → Recent Deliveries
```

#### 3. Inline Comments Not Appearing

**Possible causes:**
- Incorrect diff refs (base_sha, head_sha, start_sha)
- Line numbers don't match actual diff
- Position type incorrect

**Debug:**
```python
# Get correct diff refs
mr = project.mergerequests.get(mr_iid)
diff_refs = mr.diff_refs
print(f"base_sha: {diff_refs['base_sha']}")
print(f"head_sha: {diff_refs['head_sha']}")
print(f"start_sha: {diff_refs['start_sha']}")
```

#### 4. Teamwork API 401 Unauthorized

**Solution:**
- Verify API key format (should be used as Basic Auth username)
- Check key hasn't been revoked
- Ensure proper URL (no trailing slash)

```bash
# Test API key
curl -u "YOUR_API_KEY:" https://projects.ebs-integrator.com/me.json
```

#### 5. Rate Limiting

**Anthropic Rate Limits:**
- claude-sonnet-4-20250514: ~50 requests/minute (varies by plan)

**Solution:**
```python
# Implement exponential backoff
import asyncio
from tenacity import retry, wait_exponential, stop_after_attempt

@retry(wait=wait_exponential(multiplier=1, min=4, max=60), stop=stop_after_attempt(5))
async def run_review_with_retry(agent, prompt, deps):
    return await agent.run(prompt, deps=deps)
```

---

## Quick Reference: Environment Variables

```bash
# Required
GITLAB_URL=https://gitlab.your-domain.com
GITLAB_TOKEN=glpat-xxxxxxxxxxxxxxxxxxxx
GITLAB_WEBHOOK_SECRET=your-random-secret
GILFOYLE_USER_ID=123
ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxx

# Required for Teamwork integration
TEAMWORK_URL=https://projects.ebs-integrator.com
TEAMWORK_API_KEY=tkn.xxxxxxxxxxxxxxxxxxxx

# Optional
LLM_MODEL=claude-sonnet-4-20250514
LOG_LEVEL=INFO
DEBUG=false
```

---

## Next Steps

After completing the testing plan:

1. **Document findings** - Note any issues encountered and resolutions
2. **Performance baseline** - Record average review times
3. **Feedback collection** - Gather team feedback on review quality
4. **Iteration** - Adjust prompts and tools based on feedback
5. **Production deployment** - Follow the deploy stage in CI/CD
