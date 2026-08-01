"""
Firomsa AI Secretary — FastAPI Application Entry Point
"""
import asyncio
import contextlib
import logging
from collections.abc import AsyncGenerator
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.database import engine, Base, AsyncSessionLocal
from app.api import router as api_router
from app.telegram.client import telegram_client
from app.telegram.session_store import load_session_string
logger = logging.getLogger(__name__)

_TELEGRAM_KEEPALIVE_INTERVAL_SECONDS = 180  # 3 minutes


async def _telegram_keepalive_loop() -> None:
    """
    Periodically touches the live Telegram MTProto connection.

    HTTP uptime pings (e.g. UptimeRobot) only keep the web process itself
    from spinning down — they do nothing for the separate MTProto socket
    Telethon holds open to Telegram's servers. On Render's free tier that
    socket can go idle and get silently dropped by the network layer
    without Telethon's high-level `is_connected` flag ever flipping to
    False, which means new-message events silently stop arriving even
    though /telegram/status still reports connected=true. Calling
    get_me() periodically forces real traffic on that socket, which
    either keeps it alive or triggers Telethon's own reconnect logic if
    it had already died.
    """
    while True:
        try:
            await asyncio.sleep(_TELEGRAM_KEEPALIVE_INTERVAL_SECONDS)
            if telegram_client.is_connected:
                await telegram_client.client.get_me()
                logger.debug("Telegram keepalive ping OK.")
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.warning("Telegram keepalive ping failed: %s", exc)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown lifecycle."""
    # ── Startup ───────────────────────────────────────────────────────────────
    logger.info("Starting Firomsa AI Secretary...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables verified.")
    # Load any previously-persisted Telegram session from the database so
    # the client reconnects automatically after a restart, instead of
    # only ever checking the TELEGRAM_SESSION env var (the Phase 1 bug).
    async with AsyncSessionLocal() as db:
        db_session_string = await load_session_string(db)
    await telegram_client.initialise(db_session_string=db_session_string)
    if db_session_string:
        logger.info("Telegram client initialised with session restored from database.")
    else:
        logger.info("Telegram client ready (not connected — awaiting credentials).")

    keepalive_task = asyncio.create_task(_telegram_keepalive_loop())
    logger.info(
        "Telegram keepalive task started (interval=%ss).",
        _TELEGRAM_KEEPALIVE_INTERVAL_SECONDS,
    )

    yield
    # ── Shutdown ──────────────────────────────────────────────────────────────
    logger.info("Shutting down Firomsa AI Secretary...")
    keepalive_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await keepalive_task
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
        version="0.2.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # Root route to fix 404 on base URL
    @app.get("/", tags=["Health"])
    async def root():
        return JSONResponse(
            content={
                "status": "online",
                "message": "Firomsa AI Secretary Backend Server is Running!",
                "docs": "/docs",
            }
        )
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
