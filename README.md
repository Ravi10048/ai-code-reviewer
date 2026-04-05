# AI Code Reviewer

AI-powered code review bot for GitHub Pull Requests. Installs as a GitHub App, automatically reviews PRs using open-source LLMs (Llama 3.3, DeepSeek), and posts inline comments with bug reports, security warnings, and improvement suggestions.

## Demo

### Bot automatically reviews PRs and posts comments
![PR Review](docs/pr-review.png.jpeg)

### Detailed issue breakdown with severity and suggestions
![Inline Comments](docs/inline-comment.jpeg)

### Web dashboard to track all reviews
![Dashboard](docs/dashboard.png.jpeg)

### Review detail with expandable issues
![Review Detail](docs/review-detail1.jpeg)
![Review Detail 2](docs/review-detail2.jpeg)

## How It Works

```
1. Developer opens a Pull Request
2. GitHub sends webhook to your server
3. Server fetches the PR diff
4. LLM (Llama 3.3 / DeepSeek) analyzes code file-by-file
5. Bot posts summary comment + inline comments on the PR
6. Review saved to database, visible on dashboard
```

```
┌──────────────┐     webhook      ┌─────────────────┐     LLM call     ┌──────────────┐
│   GitHub PR   │ ──────────────→ │  FastAPI Backend  │ ──────────────→ │  Groq / Ollama│
│   opened      │ ←────────────── │  (review engine)  │ ←────────────── │  (Llama 3.3)  │
└──────────────┘  review comments └────────┬──────────┘                 └──────────────┘
                                           │
                                    ┌──────▼──────┐
                                    │   SQLite DB   │
                                    │   (history)   │
                                    └──────┬──────┘
                                           │
                                    ┌──────▼──────┐
                                    │    React     │
                                    │  Dashboard   │
                                    └─────────────┘
```

## Features

- **Automatic PR Reviews** — Triggered on PR open, push, or reopen
- **Inline Comments** — Line-level comments directly on the PR diff
- **Summary Reports** — Overall review with severity table and key issues
- **Multi-Model** — Groq (free cloud: Llama, DeepSeek, Mixtral) or Ollama (self-hosted)
- **Web Dashboard** — Review history, analytics charts, settings
- **Language-Aware** — Tailored prompts for Python, JavaScript, TypeScript, Java, Go
- **Configurable** — Severity thresholds, file limits, model selection via UI or `.codereview.yml`

## What It Detects

| Category | Examples |
|----------|----------|
| **Security** | SQL injection, hardcoded secrets, path traversal, XSS |
| **Bugs** | Null access, off-by-one, type mismatches, division by zero |
| **Performance** | N+1 queries, missing indexes, unnecessary loops |
| **Error Handling** | Missing try/catch, silent failures, unhandled promises |
| **Style** | Dead code, poor naming, overly complex expressions |

## Quick Start

### 1. Create a GitHub App

1. Go to **GitHub Settings → Developer Settings → GitHub Apps → New GitHub App**
2. Set:
   - **Webhook URL**: `https://your-server.com/webhook/github`
   - **Webhook Secret**: Generate a random string
   - **Permissions**: Pull Requests (Read & Write), Contents (Read), Metadata (Read)
   - **Events**: Pull Request
3. Generate a **Private Key** (downloads `.pem` file)
4. Note the **App ID**

### 2. Configure

```bash
git clone https://github.com/Ravi10048/ai-code-reviewer.git
cd ai-code-reviewer

cp .env.example .env
# Edit .env → set GITHUB_APP_ID, GITHUB_WEBHOOK_SECRET, GROQ_API_KEY

# Place your private key
cp ~/Downloads/your-app.private-key.pem ./github-app.pem
```

### 3. Run with Docker Compose

```bash
docker compose up -d

# Dashboard: http://localhost:3000
# API Docs:  http://localhost:8080/docs
```

### 4. Run Locally (Development)

```bash
# Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080

# Frontend (separate terminal)
cd frontend
npm install && npm run dev

# Tunnel for webhooks
ngrok http 8080
```

### 5. Install the App

Go to `https://github.com/apps/your-app-name` → Install on your repos → Open a PR → Bot reviews automatically!

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GITHUB_APP_ID` | Yes | — | GitHub App ID |
| `GITHUB_PRIVATE_KEY_PATH` | Yes | `./github-app.pem` | Path to `.pem` file |
| `GITHUB_WEBHOOK_SECRET` | Yes | — | Webhook secret |
| `LLM_PROVIDER` | No | `groq` | `groq` or `ollama` |
| `GROQ_API_KEY` | If Groq | — | Free key from console.groq.com |
| `GROQ_MODEL` | No | `llama-3.3-70b-versatile` | Groq model |
| `OLLAMA_MODEL` | No | `deepseek-coder-v2` | Ollama model |

### Per-Repository Config

Add `.codereview.yml` to any repo:

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

## Supported Models

| Provider | Models | Cost |
|----------|--------|------|
| **Groq** | Llama 3.3 70B, DeepSeek R1 70B, Mixtral 8x7B, Gemma 2 9B | Free |
| **Ollama** | DeepSeek Coder V2, Llama 3.1, CodeLlama, any compatible model | Free (local) |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python, FastAPI, SQLAlchemy, SQLite |
| **Frontend** | React, TypeScript, Tailwind CSS, Recharts |
| **LLM** | Groq API (cloud), Ollama (self-hosted) |
| **GitHub** | PyGithub, JWT auth, Webhooks |
| **Deploy** | Docker Compose, Railway/Render |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/webhook/github` | GitHub webhook receiver |
| `GET` | `/api/reviews` | List reviews (paginated) |
| `GET` | `/api/reviews/:id` | Review detail with issues |
| `GET` | `/api/analytics/summary` | Dashboard analytics |
| `GET` | `/api/analytics/repos` | Connected repositories |
| `GET/PUT` | `/api/settings` | App settings |
| `GET` | `/api/settings/health` | LLM health check |

## Project Structure

```
ai-code-reviewer/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── config.py            # Settings (env vars)
│   │   ├── github/              # GitHub App auth, diff parser, comment poster
│   │   ├── llm/                 # Multi-provider LLM (Groq, Ollama, factory)
│   │   ├── review/              # Review engine, prompts, models
│   │   ├── webhook/             # Webhook handler, signature verification
│   │   ├── routers/             # API routes (reviews, analytics, settings)
│   │   └── db/                  # SQLAlchemy models, repository pattern
│   └── tests/                   # 18 unit tests
├── frontend/
│   ├── src/
│   │   ├── pages/               # Dashboard, Reviews, Analytics, Settings
│   │   ├── components/          # Sidebar, StatsCard, SeverityBadge
│   │   └── api/                 # API client
├── docker-compose.yml           # Backend + Frontend + Ollama
└── README.md
```

## License

MIT
