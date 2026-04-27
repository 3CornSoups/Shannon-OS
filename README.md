# Shannon OS Agent

> AI-powered server operations assistant — talk to your infrastructure.

Shannon turns natural language into server commands. Describe what you need, and it plans, executes, and monitors operations across your machines.

## Features

- **Natural language ops** — "check disk usage on all servers" → AI generates and runs the commands
- **Multi-server management** — add, test, switch between SSH servers from the dashboard
- **Real-time monitoring** — CPU, memory, disk, network, processes with live ECharts dashboards
- **ReAct agent loop** — plan-approve-execute flow with risk assessment and self-healing
- **Operation history** — full audit trail per server with conversation replay
- **Template system** — save and reuse command templates for repetitive tasks
- **SSE streaming** — real-time event push for command output and agent thinking

## Quick Start

```bash
# install dependencies
pip install -r requirements.txt
cd web && npm install && cd ..

# start
python -m uvicorn app.main:app --reload
```

Open `http://localhost:8000`, then:

1. **Settings** → enter your DeepSeek API Key → test → save
2. **Servers** → add target server (host, port, user, password/key) → test → save
3. **Dashboard** → select server, describe what to do

No `.env` required — everything is configurable through the UI.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python / FastAPI / Uvicorn |
| Frontend | Vue 3 / Vite / Pinia / Tailwind |
| Database | SQLite (aiosqlite) |
| SSH | asyncssh + paramiko (dual engine) |
| AI | DeepSeek Chat (OpenAI-compatible API) |
| Realtime | SSE streaming + WebSocket terminal |
| Charts | ECharts |

## Project Structure

```
shannon/
├── app/                # Python backend
│   ├── agent.py        # Agent orchestration (ReAct loop)
│   ├── llm_client.py   # LLM API calls (streaming + tool calling)
│   ├── executor.py     # SSH command execution
│   ├── connection.py   # SSH connection pool
│   ├── database.py     # SQLite CRUD
│   ├── monitor.py      # System monitoring
│   ├── security.py     # Password encryption
│   ├── prompts.py      # System prompt management
│   └── routers/        # API routes (chat, hosts, settings, ...)
├── web/                # Vue 3 frontend
│   └── src/
│       ├── pages/      # Dashboard, Servers, Settings, Monitoring, ...
│       ├── stores/     # Pinia state management
│       └── services/   # Axios API client
├── run.py              # One-click launcher
└── requirements.txt
```

## Roadmap

We're building the next-generation server operations platform and looking for contributors.

**Near-term priorities:**

- **Smarter agent** — improve the ReAct loop with better planning, multi-step reasoning, error recovery, and context-aware decision making
- **Multi-LLM support** — pluggable backends for Claude, OpenAI, Gemini, local models
- **Agent memory** — persistent memory across sessions for learning server patterns and user preferences

**Mobile & desktop:**

- **Mobile app** — React Native / Flutter client for on-the-go monitoring and emergency ops
- **Desktop GUI** — Tauri or Electron app with native terminal emulation and offline mode

**Infrastructure & ecosystem:**

- **Plugin system** — community-contributed tools, custom monitors, notification channels
- **CI/CD integration** — trigger operations from GitHub Actions, GitLab CI, webhooks
- **Team collaboration** — role-based access, shared server inventory, operation approval workflows
- **Docker deployment** — one-command deploy with docker-compose
- **i18n** — English and more language support
- **Template marketplace** — share and discover operation templates

**Security & reliability:**

- **End-to-end encryption** for stored credentials
- **Comprehensive audit** — who did what, when, on which server
- **Alerting** — Slack / Discord / Email notifications on threshold breaches

## Deploy

See [DEPLOY.md](DEPLOY.md) for production deployment, environment variables, and API reference.

## Contributing

Contributions are welcome. Check the roadmap above — if something catches your interest, open an issue or a PR.

## License

MIT