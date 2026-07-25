"""
Firomsa AI Secretary — FastAPI Application Entry Point
"""

import contextlib
import logging
from collections.abc import AsyncGenerator

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base
from app.api import router as api_router
from app.telegram.client import telegram_client

logger = logging.getLogger(__name__)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown lifecycle."""
    # ── Startup ───────────────────────────────────────────────────────────────
    logger.info("Starting Firomsa AI Secretary…")

    # Create database tables (use Alembic in production)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables verified.")

    # Initialise Telegram client (does not log in automatically)
    await telegram_client.initialise()
    logger.info("Telegram client ready (not connected — awaiting credentials).")

    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    logger.info("Shutting down Firomsa AI Secretary…")
    await telegram_client.disconnect()
    await engine.dispose()
    logger.info("Shutdown complete.")


def create_app() -> FastAPI:
    """Factory that returns a configured FastAPI instance."""
    app = FastAPI(
        title="Firomsa AI Secretary",
        description=(
            "A personal AI secretary that connects to your Telegram account "
            "via MTProto, manages your inbox, and assists with professional communication."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routes ────────────────────────────────────────────────────────────────
    app.include_router(api_router)

    return app


app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
