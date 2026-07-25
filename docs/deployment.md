# Deployment Guide — Firomsa AI Secretary

## Render (Recommended)

Firomsa is configured as a **Render worker service** — it runs continuously as a background process (no inbound HTTP from the public internet required for the Telegram listener). The FastAPI server is exposed only for internal management and webhook purposes.

### Steps

1. **Push to GitHub**
   ```bash
   git push origin main
   ```

2. **Connect your repo to Render**
   - Go to [render.com](https://render.com) → New → Web Service (or use `render.yaml` for blueprint deploy)
   - Select your repository

3. **Set environment variables in the Render dashboard**

   | Key | Value |
   |---|---|
   | `DATABASE_URL` | Your PostgreSQL connection string |
   | `SECRET_KEY` | Generated random hex string |
   | `TELEGRAM_API_ID` | From my.telegram.org |
   | `TELEGRAM_API_HASH` | From my.telegram.org |
   | `TELEGRAM_PHONE` | Your phone number |
   | `TELEGRAM_SESSION` | *(leave blank on first deploy; fill after auth)* |
   | `AI_PROVIDER` | `openai` or `groq` |
   | `OPENAI_API_KEY` | If using OpenAI |
   | `GROQ_API_KEY` | If using Groq |

4. **Deploy**
   - Render will run `alembic upgrade head` then start `uvicorn` as defined in `render.yaml`

5. **Authenticate with Telegram** *(Phase 2)*
   - After the first deploy, trigger the auth flow via the admin endpoint
   - Copy the exported `TELEGRAM_SESSION` string into Render env vars
   - Redeploy to activate the persistent session

---

## Docker (Self-hosted)

### Build

```bash
cd backend
docker build -t firomsa-ai-secretary .
```

### Run

```bash
docker run -d \
  --name firomsa \
  --env-file .env \
  -p 8000:8000 \
  firomsa-ai-secretary
```

### Docker Compose (with PostgreSQL)

```yaml
version: "3.9"
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: firomsa
      POSTGRES_PASSWORD: secret
      POSTGRES_DB: firomsa
    volumes:
      - pgdata:/var/lib/postgresql/data

  app:
    build: ./backend
    env_file: ./backend/.env
    environment:
      DATABASE_URL: postgresql+asyncpg://firomsa:secret@db:5432/firomsa
    ports:
      - "8000:8000"
    depends_on:
      - db

volumes:
  pgdata:
```

```bash
docker compose up -d
```

---

## Production Checklist

- [ ] `DEBUG=false` in production
- [ ] `SECRET_KEY` is a securely generated random value (≥ 32 bytes)
- [ ] `DATABASE_URL` points to a managed PostgreSQL instance (Render DB, Supabase, Neon, etc.)
- [ ] `TELEGRAM_SESSION` is populated with an exported session string
- [ ] Alembic migrations applied (`alembic upgrade head`)
- [ ] AI provider key is valid and has sufficient quota
- [ ] `CORS_ORIGINS` is locked to your actual frontend domain (not `*`)
- [ ] Application logs are streamed to a log aggregator (Render logs, Datadog, etc.)
