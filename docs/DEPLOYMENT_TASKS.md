# Gilfoyle AI Agent - Deployment Task List

## Overview

This document provides a step-by-step checklist for deploying Gilfoyle from local development to production.

---

## Part 1: Prerequisites Setup

### 1.1 Local Machine Setup

- [ ] **Install Python 3.11+**
  ```bash
  python3 --version  # Should be 3.11 or higher
  ```

- [ ] **Install uv package manager**
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  source ~/.bashrc  # or restart terminal
  uv --version  # Should be 0.9.17+
  ```

- [ ] **Install Docker and Docker Compose**
  ```bash
  docker --version
  docker-compose --version
  ```

- [ ] **Install ngrok (for webhook testing)**
  ```bash
  # macOS
  brew install ngrok
  
  # Linux
  curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | \
    sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null && \
    echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | \
    sudo tee /etc/apt/sources.list.d/ngrok.list && \
    sudo apt update && sudo apt install ngrok
  ```

### 1.2 API Keys Generation

- [ ] **Generate Anthropic API Key**
  1. Go to https://console.anthropic.com/
  2. Sign in / Create account
  3. Navigate to **API Keys**
  4. Click **Create Key**
  5. Copy the key (format: `sk-ant-api03-...`)
  6. Save securely (you won't see it again)

- [ ] **Create GitLab Gilfoyle User**
  1. Login to GitLab as **Administrator**
  2. Go to **Admin Area** → **Users** → **New User**
  3. Fill in:
     - Name: `Gilfoyle`
     - Username: `gilfoyle`
     - Email: `gilfoyle@your-domain.com`
  4. Click **Create User**
  5. Set password for the account
  6. Note the **User ID** (visible in Admin Area → Users → gilfoyle)

- [ ] **Generate GitLab Personal Access Token**
  1. Login as `gilfoyle` user
  2. Go to **User Settings** → **Access Tokens**
  3. Create token with:
     - Name: `gilfoyle-agent-token`
     - Expiration: 1 year (set reminder to rotate)
     - Scopes: ✓ `api`, ✓ `read_repository`, ✓ `write_repository`, ✓ `read_user`
  4. Click **Create personal access token**
  5. Copy immediately (format: `glpat-...`)

- [ ] **Generate GitLab Webhook Secret**
  ```bash
  openssl rand -hex 32
  # Save this value securely
  ```

- [ ] **Get Teamwork API Key**
  1. Login to https://projects.ebs-integrator.com/
  2. Go to Profile → **Settings** → **API & Integrations**
  3. Generate or copy existing API token
  4. Save securely (format: `tkn....`)

---

## Part 2: Local Development Setup

### 2.1 Clone and Configure Project

- [ ] **Clone the repository**
  ```bash
  git clone <repository-url>
  cd gilfoyle
  ```

- [ ] **Create environment file**
  ```bash
  cp .env.example .env
  ```

- [ ] **Configure .env with your values**
  ```bash
  # Edit .env with your actual values
  nano .env
  ```
  
  Required values:
  ```env
  GITLAB_URL=https://gitlab.your-domain.com
  GITLAB_TOKEN=glpat-xxxxxxxxxxxxxxxxxxxx
  GITLAB_WEBHOOK_SECRET=<your-generated-secret>
  GILFOYLE_USER_ID=<gilfoyle-user-id>
  ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxx
  TEAMWORK_URL=https://projects.ebs-integrator.com
  TEAMWORK_API_KEY=tkn.xxxxxxxxxxxxxxxxxxxx
  LLM_MODEL=claude-sonnet-4-20250514
  LOG_LEVEL=DEBUG
  DEBUG=true
  ```

### 2.2 Install Dependencies

- [ ] **Sync dependencies with uv**
  ```bash
  uv sync --dev
  ```

- [ ] **Verify installation**
  ```bash
  uv run python -c "import pydantic_ai; import fastapi; print('OK')"
  ```

### 2.3 Run Tests

- [ ] **Run unit tests**
  ```bash
  uv run pytest tests/unit/ -v
  ```

- [ ] **Run all tests**
  ```bash
  uv run pytest -v
  ```

---

## Part 3: Local Testing with GitLab

### 3.1 Start Local Server

- [ ] **Start Gilfoyle server**
  ```bash
  uv run uvicorn gilfoyle.main:app --reload --host 0.0.0.0 --port 8000
  ```

- [ ] **Verify health check**
  ```bash
  curl http://localhost:8000/health
  # Expected: {"status":"healthy","version":"0.1.0"}
  ```

### 3.2 Expose Local Server with ngrok

- [ ] **Start ngrok tunnel**
  ```bash
  # In a new terminal
  ngrok http 8000
  ```

- [ ] **Copy the HTTPS URL**
  ```
  Example: https://abc123.ngrok.io
  ```

### 3.3 Configure GitLab Test Project

- [ ] **Create test repository in GitLab**
  1. Go to GitLab → **New Project** → **Create blank project**
  2. Name: `gilfoyle-test`
  3. Visibility: Private
  4. Initialize with README: ✓

- [ ] **Add Gilfoyle as project member**
  1. Go to project → **Settings** → **Members**
  2. Invite `gilfoyle` with **Developer** role

- [ ] **Configure webhook**
  1. Go to **Settings** → **Webhooks**
  2. URL: `https://abc123.ngrok.io/webhook/gitlab`
  3. Secret token: Your `GITLAB_WEBHOOK_SECRET`
  4. Triggers: ✓ Comments, ✓ Merge request events
  5. SSL verification: ✓ Enable
  6. Click **Add webhook**

- [ ] **Test webhook delivery**
  1. Click **Test** → **Merge request events**
  2. Check ngrok terminal and server logs
  3. Should see 200 response

### 3.4 Create Test Merge Request

- [ ] **Create test branch with sample code**
  ```bash
  git clone https://gitlab.your-domain.com/your-group/gilfoyle-test.git
  cd gilfoyle-test
  
  git checkout -b test/gilfoyle-review
  
  # Create test file with intentional issues
  mkdir -p src
  cat > src/example.py << 'EOF'
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
  
  git add .
  git commit -m "Add example code for Gilfoyle review"
  git push -u origin test/gilfoyle-review
  ```

- [ ] **Create Merge Request**
  1. Go to GitLab → Repository → Branches
  2. Click **Merge Request** next to your branch
  3. Title: `Test: Gilfoyle Review Demo`
  4. Description: 
     ```
     Testing Gilfoyle AI review.
     
     Related task: https://projects.ebs-integrator.com/app/tasks/12345
     ```
  5. Create MR

### 3.5 Trigger Gilfoyle Review

- [ ] **Option A: Comment trigger**
  1. Go to MR
  2. Add comment: `@gilfoyle please review this MR`
  3. Watch server logs for processing

- [ ] **Option B: Reviewer trigger**
  1. Edit MR
  2. Add `gilfoyle` as Reviewer
  3. Watch server logs for processing

### 3.6 Verify Review Results

- [ ] **Check MR for Gilfoyle's response**
  - [ ] Summary comment posted
  - [ ] Inline comments on specific lines
  - [ ] Security issues identified
  - [ ] Coding standard violations noted

- [ ] **Verify in server logs**
  ```bash
  # Should see:
  # - Webhook received
  # - Review triggered
  # - LLM API called
  # - Comments posted
  ```

---

## Part 4: Docker Deployment (Staging)

### 4.1 Build Docker Image

- [ ] **Build the image**
  ```bash
  docker build -t gilfoyle:latest .
  ```

- [ ] **Test the container locally**
  ```bash
  docker run -d --name gilfoyle-test \
    --env-file .env \
    -p 8000:8000 \
    gilfoyle:latest
  
  # Check logs
  docker logs -f gilfoyle-test
  
  # Test health
  curl http://localhost:8000/health
  
  # Cleanup
  docker stop gilfoyle-test && docker rm gilfoyle-test
  ```

### 4.2 Deploy with Docker Compose

- [ ] **Start with docker-compose**
  ```bash
  docker-compose up -d
  ```

- [ ] **Check status**
  ```bash
  docker-compose ps
  docker-compose logs -f gilfoyle
  ```

- [ ] **Verify health**
  ```bash
  curl http://localhost:8000/health
  ```

### 4.3 Update GitLab Webhook

- [ ] **Update webhook URL to staging server**
  1. Go to GitLab → Project → Settings → Webhooks
  2. Edit webhook URL to: `https://gilfoyle-staging.your-domain.com/webhook/gitlab`
  3. Save

- [ ] **Test webhook again**
  1. Create new comment on test MR: `@gilfoyle review again please`
  2. Verify review is processed

---

## Part 5: Production Deployment

### 5.1 Production Environment Setup

- [ ] **Provision production server**
  - Recommended: 2 CPU, 4GB RAM minimum
  - Ubuntu 22.04 LTS or similar
  - Docker and Docker Compose installed

- [ ] **Configure DNS**
  - Create A record: `gilfoyle.your-domain.com` → Server IP

- [ ] **Set up SSL/TLS**
  ```bash
  # Using Let's Encrypt with Certbot
  sudo apt install certbot
  sudo certbot certonly --standalone -d gilfoyle.your-domain.com
  ```

- [ ] **Configure reverse proxy (nginx)**
  ```nginx
  server {
      listen 443 ssl http2;
      server_name gilfoyle.your-domain.com;
      
      ssl_certificate /etc/letsencrypt/live/gilfoyle.your-domain.com/fullchain.pem;
      ssl_certificate_key /etc/letsencrypt/live/gilfoyle.your-domain.com/privkey.pem;
      
      location / {
          proxy_pass http://localhost:8000;
          proxy_set_header Host $host;
          proxy_set_header X-Real-IP $remote_addr;
          proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
          proxy_set_header X-Forwarded-Proto $scheme;
      }
  }
  ```

### 5.2 Production Configuration

- [ ] **Create production .env**
  ```bash
  # On production server
  cat > /opt/gilfoyle/.env << 'EOF'
  # Production configuration
  DEBUG=false
  LOG_LEVEL=INFO
  
  GITLAB_URL=https://gitlab.your-domain.com
  GITLAB_TOKEN=<production-token>
  GITLAB_WEBHOOK_SECRET=<production-secret>
  GILFOYLE_USER_ID=<user-id>
  
  ANTHROPIC_API_KEY=<production-api-key>
  
  TEAMWORK_URL=https://projects.ebs-integrator.com
  TEAMWORK_API_KEY=<production-teamwork-key>
  
  LLM_MODEL=claude-sonnet-4-20250514
  EOF
  
  chmod 600 /opt/gilfoyle/.env
  ```

- [ ] **Create production docker-compose.prod.yml**
  ```yaml
  version: "3.8"
  services:
    gilfoyle:
      image: gilfoyle:latest
      restart: always
      env_file:
        - .env
      ports:
        - "127.0.0.1:8000:8000"
      healthcheck:
        test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
        interval: 30s
        timeout: 10s
        retries: 3
      logging:
        driver: "json-file"
        options:
          max-size: "10m"
          max-file: "3"
  ```

### 5.3 Deploy to Production

- [ ] **Copy files to server**
  ```bash
  scp -r . user@production-server:/opt/gilfoyle/
  ```

- [ ] **Start production service**
  ```bash
  ssh user@production-server
  cd /opt/gilfoyle
  docker-compose -f docker-compose.prod.yml up -d
  ```

- [ ] **Verify production health**
  ```bash
  curl https://gilfoyle.your-domain.com/health
  ```

### 5.4 Update Production Webhook

- [ ] **Update all project webhooks**
  For each project that should use Gilfoyle:
  1. Go to **Settings** → **Webhooks**
  2. URL: `https://gilfoyle.your-domain.com/webhook/gitlab`
  3. Secret: Production webhook secret
  4. Triggers: ✓ Comments, ✓ Merge request events

- [ ] **Add Gilfoyle to projects**
  For each project:
  1. Go to **Settings** → **Members**
  2. Invite `gilfoyle` with **Developer** role

---

## Part 6: Production Testing

### 6.1 Smoke Tests

- [ ] **Health check**
  ```bash
  curl https://gilfoyle.your-domain.com/health
  ```

- [ ] **Metrics check (if enabled)**
  ```bash
  curl https://gilfoyle.your-domain.com/metrics
  ```

### 6.2 Functional Tests

- [ ] **Create production test MR**
  1. Create a branch in a test project
  2. Add some code changes
  3. Create MR

- [ ] **Test comment trigger**
  1. Comment `@gilfoyle please review`
  2. Verify review is posted within 60 seconds

- [ ] **Test reviewer trigger**
  1. Assign `gilfoyle` as reviewer
  2. Verify review is posted

- [ ] **Verify inline comments**
  - [ ] Comments appear on correct lines
  - [ ] Severity levels are appropriate
  - [ ] Suggestions are actionable

- [ ] **Verify Teamwork integration**
  1. Create MR with task reference in description
  2. Verify task context is mentioned in review

- [ ] **Verify docs/ADR integration**
  1. Add `docs/CODING_STANDARDS.md` to a project
  2. Create MR that violates standards
  3. Verify standards are referenced in review

### 6.3 Load Testing (Optional)

- [ ] **Test concurrent reviews**
  ```bash
  # Trigger multiple reviews simultaneously
  # Verify all are processed correctly
  ```

- [ ] **Monitor resource usage**
  ```bash
  docker stats gilfoyle
  ```

---

## Part 7: Monitoring & Maintenance

### 7.1 Set Up Monitoring

- [ ] **Configure log aggregation**
  ```bash
  # View logs
  docker-compose logs -f gilfoyle
  
  # Or set up external logging (ELK, Loki, etc.)
  ```

- [ ] **Set up alerting**
  - Alert on: Container restart
  - Alert on: Health check failure
  - Alert on: High error rate in logs

### 7.2 Regular Maintenance

- [ ] **Weekly tasks**
  - [ ] Review error logs
  - [ ] Check API usage/costs
  - [ ] Review Gilfoyle's feedback quality

- [ ] **Monthly tasks**
  - [ ] Update dependencies (`uv sync --upgrade`)
  - [ ] Review and rotate API keys if needed
  - [ ] Update LLM model if new version available

- [ ] **Quarterly tasks**
  - [ ] Rotate GitLab access token
  - [ ] Review and update system prompts
  - [ ] Gather team feedback and improve

### 7.3 Troubleshooting Checklist

If Gilfoyle stops working:

- [ ] Check container is running: `docker-compose ps`
- [ ] Check logs: `docker-compose logs gilfoyle`
- [ ] Verify health: `curl https://gilfoyle.your-domain.com/health`
- [ ] Check API keys are valid
- [ ] Verify webhook is configured correctly
- [ ] Check GitLab can reach the webhook URL
- [ ] Verify Gilfoyle user has project access

---

## Quick Reference

### URLs

| Environment | URL |
|-------------|-----|
| Local | http://localhost:8000 |
| Local (ngrok) | https://xxx.ngrok.io |
| Staging | https://gilfoyle-staging.your-domain.com |
| Production | https://gilfoyle.your-domain.com |

### Commands

```bash
# Start local dev
uv run uvicorn gilfoyle.main:app --reload --port 8000

# Run tests
uv run pytest -v

# Build Docker
docker build -t gilfoyle:latest .

# Start with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f gilfoyle

# Stop
docker-compose down
```

### Environment Variables

```env
# Required
GITLAB_URL=https://gitlab.your-domain.com
GITLAB_TOKEN=glpat-...
GITLAB_WEBHOOK_SECRET=...
GILFOYLE_USER_ID=123
ANTHROPIC_API_KEY=sk-ant-api03-...
TEAMWORK_URL=https://projects.ebs-integrator.com
TEAMWORK_API_KEY=tkn....

# Optional
LLM_MODEL=claude-sonnet-4-20250514
LOG_LEVEL=INFO
DEBUG=false
```

---

## Completion Checklist

### Local Development ✅
- [ ] All prerequisites installed
- [ ] API keys generated and configured
- [ ] Local server running
- [ ] Tests passing

### Local Testing with GitLab ✅
- [ ] ngrok tunnel working
- [ ] Webhook configured
- [ ] Test MR created
- [ ] Review triggered and completed

### Staging Deployment ✅
- [ ] Docker image built
- [ ] Container running
- [ ] Staging webhook configured
- [ ] Staging tests passing

### Production Deployment ✅
- [ ] Production server provisioned
- [ ] SSL configured
- [ ] Production secrets set
- [ ] Production webhook configured
- [ ] All functional tests passing

### Go Live ✅
- [ ] Team notified
- [ ] Documentation shared
- [ ] Monitoring in place
- [ ] Maintenance schedule set

---

**Congratulations! Gilfoyle is now reviewing your code! 🎉**
