"""
Telethon MTProto client wrapper.

On startup the client:
  1. Tries to load a StringSession from the DB (preferred — survives restarts).
  2. Falls back to the TELEGRAM_SESSION env var.
  3. If neither exists, starts unauthenticated — use /api/v1/telegram/auth/request
     to complete the OTP flow and persist a session.

The client connects automatically when a session is found and reconnects
transparently if the link drops.
"""

from __future__ import annotations

import logging

from telethon import TelegramClient
from telethon.sessions import StringSession

from app.config import settings

logger = logging.getLogger(__name__)


class FiromsaTelegramClient:
    """Lifecycle wrapper around a single TelegramClient instance."""

    def __init__(self) -> None:
        self._session_string: str = settings.telegram_session or ""
        self._client: TelegramClient = self._build_client(self._session_string)
        self._connected: bool = False
        self._handlers_registered: bool = False

    # ── Private helpers ───────────────────────────────────────────────────────

    def _build_client(self, session_string: str) -> TelegramClient:
        """Construct a TelegramClient from a StringSession."""
        return TelegramClient(
            StringSession(session_string),
            api_id=settings.telegram_api_id,
            api_hash=settings.telegram_api_hash,
        )

    async def _try_connect(self) -> None:
        """
        Connect to Telegram and register event handlers if the session is
        already authorised.  Safe to call multiple times — no-op if already
        connected.
        """
        if self._connected:
            return

        await self._client.connect()
        self._connected = True
        logger.info("Connected to Telegram MTProto servers.")

        if await self._client.is_user_authorized():
            logger.info("Session is valid — user is authorised.")
            if not self._handlers_registered:
                self._register_handlers()
        else:
            logger.warning(
                "Session found but not yet authorised. "
                "Call POST /api/v1/telegram/auth/request to authenticate."
            )

    def _register_handlers(self) -> None:
        """Wire event handlers onto the current client instance."""
        from app.telegram.handlers import register_handlers  # avoid circular import

        register_handlers(self._client)
        self._handlers_registered = True
        logger.info("Telegram event handlers registered.")

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def initialise(self, db_session_string: str | None = None) -> None:
        """
        Called once during application startup.

        Resolution order for the session string:
          1. *db_session_string* argument (loaded from DB by main.py)
          2. TELEGRAM_SESSION env var
          3. Empty (unauthenticated)

        If a usable session is found the client connects immediately.
        """
        resolved = db_session_string or settings.telegram_session or ""

        if resolved and resolved != self._session_string:
            # Replace the client with one using the fresher session
            logger.info("Using session string from database (len=%d).", len(resolved))
            self._session_string = resolved
            self._connected = False
            self._handlers_registered = False
            self._client = self._build_client(resolved)
        elif resolved:
            logger.info(
                "Using session string from TELEGRAM_SESSION env var (len=%d).",
                len(resolved),
            )
        else:
            logger.info(
                "No session string found. "
                "The client will start unauthenticated."
            )

        if resolved:
            await self._try_connect()
        else:
            logger.info(
                "Telegram client ready (not connected). "
                "Authenticate via POST /api/v1/telegram/auth/request."
            )

    async def reconnect_with_session(self, session_string: str) -> None:
        """
        Replace the active client with a new one using *session_string*
        and connect immediately.  Called after a successful OTP verification.
        """
        logger.info(
            "Reconnecting Telegram client with new session (len=%d).",
            len(session_string),
        )
        # Tear down existing connection gracefully
        if self._connected:
            try:
                await self._client.disconnect()
            except Exception as exc:  # noqa: BLE001
                logger.warning("Error disconnecting old client: %s", exc)
            self._connected = False
            self._handlers_registered = False

        self._session_string = session_string
        self._client = self._build_client(session_string)
        await self._try_connect()

    async def disconnect(self) -> None:
        """Gracefully disconnect — called during application shutdown."""
        if self._connected:
            await self._client.disconnect()
            self._connected = False
            logger.info("Telegram client disconnected.")

    # ── Public accessors ──────────────────────────────────────────────────────

    @property
    def client(self) -> TelegramClient:
        """Return the underlying Telethon client."""
        return self._client

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def is_authorised(self) -> bool:
        if not self._connected:
            return False
        return await self._client.is_user_authorized()

    def get_session_string(self) -> str:
        """Export the current session as a string (empty if not authenticated)."""
        return self._client.session.save()


# Module-level singleton used throughout the application.
telegram_client = FiromsaTelegramClient()
