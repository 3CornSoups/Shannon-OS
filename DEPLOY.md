# Shannon OS Agent — Deployment Guide

## Requirements

| Component | Version |
|-----------|---------|
| Python | >= 3.11 |
| Node.js | >= 18 |
| npm | >= 9 |

## Deploy

```bash
# 1. install Python dependencies
pip install -r requirements.txt

# 2. install frontend dependencies & build
cd web
npm install
npm run build        # output → web/dist/
cd ..

# 3. start
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Or one-click:

```bash
python run.py       # auto-creates venv, installs deps, builds frontend, starts server
```

## First Run

No `.env` needed. Open `http://localhost:8000` and configure through the UI:

1. **Settings** → enter DeepSeek API Key → test → save
2. **Servers** → add SSH target → test → save
3. **Dashboard** → select server → go

> All config (API keys, server credentials) is stored in local SQLite — nothing leaves your machine.

## Environment Variables (optional)

| Variable | Default | Description |
|----------|---------|-------------|
| `DEEPSEEK_API_KEY` | — | DeepSeek API key |
| `DEEPSEEK_API_BASE` | `https://api.deepseek.com` | API base URL |
| `DEEPSEEK_MODEL` | `deepseek-chat` | Model name |
| `SHANNON_DEFAULT_SSH_PORT` | `22` | Default SSH port |
| `SHANNON_PORT` | `8000` | Web service port |

Copy `.env.example` → `.env` to set these.

## Modes

| Mode | Behavior |
|------|----------|
| chat | Pure conversation, no command execution |
| auto | AI analyzes and executes automatically (low-risk) |
| agent | AI proposes a plan, user confirms, then executes |

## API Reference

| Path | Method | Description |
|------|--------|-------------|
| `/api/chat` | POST | Send message (SSE streaming) |
| `/api/stream/{task_id}` | GET | SSE event stream |
| `/api/execute/confirm` | POST | Confirm/cancel execution |
| `/api/conversations/{host_id}` | GET | List conversations |
| `/api/hosts` | GET/POST | Server management |
| `/api/settings` | GET/POST | App settings |
| `/api/monitor/{host_id}` | GET | Monitoring data |
| `/api/history` | GET | Operation history |
| `/api/files/list` | POST | File browser |
| `/api/ws/terminal` | WebSocket | Interactive terminal |

## Ports

- `8000` — Backend API + frontend static files (production)
- `5173` — Frontend dev server with API proxy (dev mode, `cd web && npm run dev`)
