# Architecture — Firomsa AI Secretary

## Overview

Firomsa AI Secretary is a **Python 3.12 / FastAPI** application that acts as an intelligent inbox manager for a personal Telegram account. It connects via the **Telethon MTProto library** (not the Bot API), so it operates as a full Telegram user account — reading every message, understanding context, and optionally drafting or sending replies.

---

## High-Level Component Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                    Telegram MTProto Layer                     │
│                 (Telethon — personal account)                 │
└────────────────────┬─────────────────────────────────────────┘
                     │ events (new message, edit, read)
                     ▼
┌──────────────────────────────────────────────────────────────┐
│                   Event Handler (Phase 2)                    │
│   handlers.py — receives, persists, routes to AI agent       │
└────────────────────┬─────────────────────────────────────────┘
                     │
          ┌──────────┴──────────┐
          ▼                     ▼
┌─────────────────┐   ┌──────────────────────────────────────┐
│   PostgreSQL DB │   │              AI Agent                │
│  (SQLAlchemy)   │   │  providers.py → prompts.py → reply   │
└─────────────────┘   └──────────────────────────────────────┘
          ▲                     │
          └─────────────────────┘
                     │
┌──────────────────────────────────────────────────────────────┐
│                   FastAPI REST API                           │
│         /api/v1/{health,users,conversations,...}             │
└──────────────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
backend/
├── app/
│   ├── main.py          # FastAPI app factory + lifespan
│   ├── config.py        # Pydantic Settings (env-based)
│   ├── database.py      # Async SQLAlchemy engine + session
│   ├── dependencies.py  # FastAPI dependency aliases
│   │
│   ├── models/          # SQLAlchemy ORM models
│   │   ├── user.py
│   │   ├── conversation.py
│   │   ├── message.py
│   │   ├── memory.py
│   │   └── settings.py
│   │
│   ├── schemas/         # Pydantic v2 request/response schemas
│   │
│   ├── api/             # FastAPI routers
│   │   └── v1/
│   │       ├── health.py
│   │       ├── users.py
│   │       ├── conversations.py
│   │       ├── messages.py
│   │       ├── memories.py
│   │       └── settings.py
│   │
│   ├── telegram/        # MTProto client & event handlers
│   │   ├── client.py    # FiromsaTelegramClient wrapper
│   │   ├── handlers.py  # Event handler registration
│   │   └── session.py   # StringSession utilities
│   │
│   ├── ai/              # AI layer
│   │   ├── providers.py # OpenAI / Groq provider implementations
│   │   ├── agent.py     # Orchestration agent
│   │   ├── prompts.py   # All system + user prompt templates
│   │   └── memory.py    # MemoryService (DB-backed context store)
│   │
│   ├── services/        # Business logic (Phase 2 expansion)
│   └── utils/           # Shared helpers (Phase 2 expansion)
│
├── migrations/          # Alembic migration scripts
│   ├── env.py           # Async migration runner
│   ├── script.py.mako   # Migration file template
│   └── versions/        # Auto-generated revision files
│
├── alembic.ini
├── requirements.txt
├── Dockerfile
└── .env.example
```

---

## Data Model

### Entity Relationships

```
User ─────────────────┬──── Conversation ──── Message
  │  (telegram_id)    │         (1:N)          (1:N)
  │                   │
  └──── Memory        └──── (category, priority, title)
        (key/value)
```

### Assistant Mode (Settings)

| Mode | Behaviour |
|---|---|
| `passive` | Reads and categorises. No auto-replies. |
| `suggestive` | Drafts replies for owner approval via API. |
| `autonomous` | Sends AI-generated replies automatically. |

---

## AI Provider Architecture

The AI layer is **provider-agnostic**. Both OpenAI and Groq expose an OpenAI-compatible REST API, so the same `openai` SDK client drives both — only the `base_url` and `api_key` differ.

Adding a new provider (e.g. Anthropic, local Ollama) requires:
1. Subclass `AIProvider` in `providers.py`
2. Register it in `_PROVIDERS`
3. Add corresponding env vars to `config.py` and `.env.example`

---

## Session Persistence (Telegram)

Telethon's `StringSession` serialises the MTProto authentication state as a plain string. This string is stored in `TELEGRAM_SESSION` and loaded on startup — no session file on disk. This makes the application stateless from a filesystem perspective and compatible with Render, Fly.io, Railway, and other ephemeral container platforms.

---

## Phase Roadmap

| Phase | Focus |
|---|---|
| **1 (current)** | Foundation: models, API, Telegram client, AI provider wiring |
| **2** | Telegram authentication endpoints, message persistence, agent integration |
| **3** | Suggestive mode UI, draft approval workflow |
| **4** | Autonomous mode, smart memory extraction, multi-language support |
| **5** | Analytics dashboard, priority inbox, calendar integration |
