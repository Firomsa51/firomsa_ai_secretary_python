# Setup Guide — Firomsa AI Secretary

## Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.12+ |
| PostgreSQL | 15+ |
| pip / venv | latest |

---

## 1. Clone and enter the project

```bash
git clone <your-repo-url>
cd firomsa-ai-secretary/backend
```

---

## 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

---

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in every value:

### Telegram credentials
1. Go to **https://my.telegram.org/apps**
2. Create an application — you will receive `TELEGRAM_API_ID` and `TELEGRAM_API_HASH`
3. Set `TELEGRAM_PHONE` to your personal phone number (with country code)

### Database
Create a PostgreSQL database and set `DATABASE_URL`:
```
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/firomsa
```

### AI provider
Choose `AI_PROVIDER=openai` or `AI_PROVIDER=groq` and add the corresponding API key.

### Secret key
Generate a random secret:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## 5. Run database migrations

```bash
# Make sure your DATABASE_URL is set in .env
alembic upgrade head
```

---

## 6. Start the development server

```bash
uvicorn app.main:app --reload --port 8000
```

The API will be available at **http://localhost:8000**

Interactive docs: **http://localhost:8000/docs**

---

## 7. Authenticate with Telegram (first run only)

> **Note:** Automatic login is intentionally disabled in this foundation phase.
> The Telegram client is initialised but not connected at startup.
> Phase 2 will add `/api/v1/telegram/auth` endpoints to trigger the OTP flow
> and export the StringSession for storage in `TELEGRAM_SESSION`.

---

## Useful commands

```bash
# Generate a new migration after changing models
alembic revision --autogenerate -m "describe change"

# Apply migrations
alembic upgrade head

# Roll back one migration
alembic downgrade -1

# Run type checker
mypy app/

# Lint and format
ruff check app/
ruff format app/
```
