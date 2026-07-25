# Firomsa AI Secretary

> A personal AI secretary that connects to your Telegram account via MTProto,
> manages your inbox, understands conversations, remembers context, and assists
> with professional communication.

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](https://fastapi.tiangolo.com)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-orange.svg)](https://sqlalchemy.org)

---

## What It Does

Firomsa runs as a background service connected to **your personal Telegram account** (not a bot). It:

- **Reads every incoming message** via the Telegram MTProto protocol (Telethon)
- **Categorises and prioritises** conversations automatically
- **Drafts context-aware replies** using OpenAI GPT-4o or Groq Llama
- **Remembers facts** about each contact (preferences, commitments, history)
- **Exposes a management API** for reviewing drafts, adjusting settings, and querying conversation history

---

## Features Roadmap

### Phase 1 — Foundation ✅ (current)
- [x] FastAPI application skeleton
- [x] Async SQLAlchemy + PostgreSQL + Alembic migrations
- [x] Pydantic v2 settings (env-based, no hardcoded secrets)
- [x] Telethon MTProto client (connection-ready, no auto-login)
- [x] Modular AI provider interface (OpenAI + Groq)
- [x] Prompt management system
- [x] Memory service (per-user key/value store)
- [x] AI agent orchestration skeleton
- [x] REST CRUD API for all entities
- [x] Docker + Render deployment config

### Phase 2 — Telegram Integration
- [ ] Telegram auth endpoints (OTP + 2FA flow via API)
- [ ] Session string export and persistence
- [ ] Message persistence on incoming events
- [ ] Conversation auto-open / auto-close logic
- [ ] Full agent integration in event handlers

### Phase 3 — Suggestive Mode
- [ ] Draft reply review API
- [ ] Owner approval/reject/edit workflow
- [ ] Notification webhook for pending drafts

### Phase 4 — Autonomous Mode
- [ ] Configurable auto-reply rules
- [ ] Smart memory extraction from conversations
- [ ] Multi-language support (English + Amharic)
- [ ] Priority inbox scoring

### Phase 5 — Intelligence & Analytics
- [ ] Conversation analytics dashboard
- [ ] Calendar integration (meeting scheduling)
- [ ] Contact relationship graph
- [ ] Weekly digest reports

---

## Architecture

```
Telegram MTProto
      │ (Telethon)
      ▼
Event Handlers ──► AI Agent (providers.py + prompts.py)
      │                    │
      ▼                    ▼
PostgreSQL DB ◄──── Memory Service
      ▲
      │
FastAPI REST API
/api/v1/{health,users,conversations,messages,memories,settings}
```

See [docs/architecture.md](docs/architecture.md) for the full diagram and design decisions.

---

## Quick Start

### 1. Clone
```bash
git clone <your-repo-url>
cd firomsa-ai-secretary/backend
```

### 2. Install
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure
```bash
cp .env.example .env
# Edit .env — see docs/setup.md for step-by-step instructions
```

### 4. Migrate
```bash
alembic upgrade head
```

### 5. Run
```bash
uvicorn app.main:app --reload --port 8000
```

API docs → **http://localhost:8000/docs**

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | ✅ | Random secret for session signing |
| `DATABASE_URL` | ✅ | `postgresql+asyncpg://user:pass@host/db` |
| `TELEGRAM_API_ID` | ✅ | From [my.telegram.org/apps](https://my.telegram.org/apps) |
| `TELEGRAM_API_HASH` | ✅ | From [my.telegram.org/apps](https://my.telegram.org/apps) |
| `TELEGRAM_PHONE` | ✅ | Your phone number with country code |
| `TELEGRAM_SESSION` | — | StringSession (populate after first auth) |
| `AI_PROVIDER` | — | `openai` (default) or `groq` |
| `OPENAI_API_KEY` | ✅* | *Required if AI_PROVIDER=openai |
| `GROQ_API_KEY` | ✅* | *Required if AI_PROVIDER=groq |

Full list and explanations in [backend/.env.example](backend/.env.example).

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/health` | Health check |
| `POST` | `/api/v1/users/` | Register a user |
| `GET` | `/api/v1/users/{telegram_id}` | Get user by Telegram ID |
| `POST` | `/api/v1/conversations/` | Create a conversation |
| `GET` | `/api/v1/conversations/` | List conversations |
| `POST` | `/api/v1/messages/` | Store a message |
| `GET` | `/api/v1/messages/` | List messages |
| `POST` | `/api/v1/memories/` | Store a memory |
| `GET` | `/api/v1/memories/` | List memories |
| `GET` | `/api/v1/settings/` | Get assistant settings |
| `PATCH` | `/api/v1/settings/` | Update assistant settings |

Interactive Swagger UI available at `/docs` when running locally.

---

## Deployment

See [docs/deployment.md](docs/deployment.md) for Render, Docker, and Docker Compose instructions.

---

## Important Notes

- **This is NOT a Telegram Bot.** It connects to your personal account via MTProto. Treat your API credentials and session string as highly sensitive secrets.
- **TELEGRAM_SESSION** must never be committed to version control. It grants full access to your Telegram account.
- The Telegram Terms of Service permit personal automation scripts — use responsibly and do not spam other users.

---

## License

MIT — see [LICENSE](LICENSE) for details.
