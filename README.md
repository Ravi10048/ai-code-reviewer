# AI Code Reviewer

AI-powered code review bot for GitHub Pull Requests. Installs as a GitHub App, automatically reviews PRs using open-source LLMs, and posts inline comments with bug reports, security warnings, and improvement suggestions.

![Dashboard](docs/dashboard-preview.png)

## Features

- **Automatic PR Reviews** — Reviews triggered on PR open, push, or reopen
- **Inline Comments** — Posts line-level review comments directly on the PR
- **Summary Reports** — Overall review summary with severity breakdown
- **Multi-Model Support** — Groq (free cloud) or Ollama (self-hosted local)
- **Web Dashboard** — Review history, analytics charts, settings management
- **Language-Aware** — Tailored checks for Python, JavaScript, TypeScript, Java, Go
- **Configurable** — Severity thresholds, file limits, model selection via UI or `.codereview.yml`

## Architecture

```
GitHub PR → Webhook → FastAPI Backend → LLM (Groq/Ollama) → GitHub Comments
                            ↓
                    SQLite (review history)
                            ↓
                    React Dashboard (analytics, settings)
```

## Quick Start

### 1. Create a GitHub App

1. Go to **GitHub Settings → Developer Settings → GitHub Apps → New GitHub App**
2. Set:
   - **Webhook URL**: Your server URL + `/webhook/github`
   - **Webhook Secret**: Generate a random string
   - **Permissions**:
     - Pull Requests: Read & Write
     - Contents: Read
     - Metadata: Read
   - **Events**: Pull Request
3. Generate a **Private Key** (downloads a `.pem` file)
4. Note the **App ID**

### 2. Setup

```bash
# Clone
git clone https://github.com/your-username/ai-code-reviewer.git
cd ai-code-reviewer

# Copy env file and configure
cp .env.example .env
# Edit .env with your GitHub App ID, webhook secret, and Groq API key
```

### 3. Run with Docker Compose (Recommended)

```bash
# Place your github-app.pem in the project root
cp ~/Downloads/your-app.private-key.pem ./github-app.pem

# Start everything
docker compose up -d

# Pull an Ollama model (if using self-hosted)
docker exec -it ai-code-reviewer-ollama-1 ollama pull deepseek-coder-v2
```

- **Dashboard**: http://localhost:3000
- **API Docs**: http://localhost:8080/docs

### 4. Run Locally (Development)

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

### 5. Expose for Webhooks (Development)

```bash
# Using Cloudflare Tunnel (free, permanent)
cloudflared tunnel --url http://localhost:8080

# Or ngrok
ngrok http 8080
```

Update your GitHub App's webhook URL with the tunnel URL.

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GITHUB_APP_ID` | Yes | — | Your GitHub App ID |
| `GITHUB_PRIVATE_KEY_PATH` | Yes | `./github-app.pem` | Path to private key |
| `GITHUB_WEBHOOK_SECRET` | Yes | — | Webhook secret |
| `LLM_PROVIDER` | No | `groq` | `groq` or `ollama` |
| `GROQ_API_KEY` | If using Groq | — | Free API key from console.groq.com |
| `GROQ_MODEL` | No | `llama-3.1-70b-versatile` | Groq model |
| `OLLAMA_BASE_URL` | No | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | No | `deepseek-coder-v2` | Ollama model name |

### Per-Repository Config

Add `.codereview.yml` to your repo root:

```yaml
min_severity: warning
ignore:
  - "*.lock"
  - "dist/**"
categories:
  - bug
  - security
  - performance
max_files: 50
```

## Supported LLM Models

### Groq (Free Cloud)
- `llama-3.1-70b-versatile` (default, best quality)
- `llama-3.1-8b-instant` (faster)
- `llama-3.3-70b-versatile`
- `deepseek-r1-distill-llama-70b`
- `mixtral-8x7b-32768`

### Ollama (Self-Hosted)
- `deepseek-coder-v2` (recommended for code)
- `llama3.1`
- `codellama`
- Any Ollama-compatible model

## Tech Stack

- **Backend**: Python, FastAPI, SQLAlchemy, SQLite
- **Frontend**: React, TypeScript, Tailwind CSS, Recharts
- **LLM**: Groq API, Ollama
- **GitHub**: PyGithub, JWT auth, Webhooks
- **Deployment**: Docker Compose, Railway/Render

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/webhook/github` | GitHub webhook receiver |
| GET | `/api/reviews` | List reviews (paginated) |
| GET | `/api/reviews/:id` | Get review with issues |
| GET | `/api/analytics/summary` | Analytics dashboard data |
| GET | `/api/analytics/repos` | Connected repositories |
| GET | `/api/settings` | Get settings |
| PUT | `/api/settings` | Update settings |
| GET | `/api/settings/health` | LLM provider health check |

## License

MIT
