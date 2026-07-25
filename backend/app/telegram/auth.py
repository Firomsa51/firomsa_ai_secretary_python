"""
Telegram authentication service.

Manages the Telethon OTP + 2FA login flow and StringSession export.
The session string is written back to settings so it survives restarts
without touching the filesystem.

Flow
────
1. POST /auth/request  → send_code_request()  → stores phone_code_hash in memory
2. POST /auth/verify   → sign_in()             → exports StringSession
3.  ↳ if SessionPasswordNeededError → retry with 2FA password
"""

import logging
from dataclasses import dataclass, field

from telethon import TelegramClient
from telethon.errors import (
    PhoneCodeExpiredError,
    PhoneCodeInvalidError,
    SessionPasswordNeededError,
)
from telethon.sessions import StringSession
from telethon.tl.types import User as TelegramUser

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class PendingAuth:
    """Transient state held between /auth/request and /auth/verify."""
    phone: str
    phone_code_hash: str


# In-process store — one pending auth at a time.
# Phase 3: replace with Redis or DB-backed store for multi-instance deployments.
_pending: dict[str, PendingAuth] = {}


class TelegramAuthService:
    """
    Encapsulates the Telethon OTP / 2FA authentication flow.
    Works with a *disconnected* client and connects only when needed.
    """

    def __init__(self) -> None:
        # Build a fresh client that shares the same session type but
        # operates independently of the main singleton during auth.
        session = StringSession(settings.telegram_session or "")
        self._client = TelegramClient(
            session,
            api_id=settings.telegram_api_id,
            api_hash=settings.telegram_api_hash,
        )

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _ensure_connected(self) -> None:
        if not self._client.is_connected():
            await self._client.connect()
            logger.debug("Auth client connected.")

    async def _disconnect(self) -> None:
        if self._client.is_connected():
            await self._client.disconnect()
            logger.debug("Auth client disconnected.")

    # ── Public API ────────────────────────────────────────────────────────────

    async def request_code(self, phone: str) -> None:
        """
        Send a Telegram login OTP to *phone*.
        Stores the phone_code_hash needed for verification.

        Raises:
            RuntimeError: if Telegram rejects the request.
        """
        await self._ensure_connected()
        try:
            result = await self._client.send_code_request(phone)
            _pending[phone] = PendingAuth(
                phone=phone,
                phone_code_hash=result.phone_code_hash,
            )
            logger.info("OTP sent to %s.", phone)
        except Exception as exc:
            logger.error("send_code_request failed for %s: %s", phone, exc)
            raise RuntimeError(f"Failed to send Telegram OTP: {exc}") from exc

    async def verify_code(
        self,
        phone: str,
        code: str,
        password: str | None = None,
    ) -> str:
        """
        Verify the OTP (and optionally 2FA password).
        Returns the exported StringSession string on success.

        Raises:
            ValueError:  missing pending auth / wrong code / expired code.
            RuntimeError: unexpected Telegram error.
        """
        pending = _pending.get(phone)
        if not pending:
            raise ValueError(
                "No pending authentication for this phone number. "
                "Call /auth/request first."
            )

        await self._ensure_connected()

        try:
            await self._client.sign_in(
                phone=phone,
                code=code,
                phone_code_hash=pending.phone_code_hash,
            )
        except SessionPasswordNeededError:
            if not password:
                raise ValueError(
                    "This account has Two-Factor Authentication enabled. "
                    "Please provide the 'password' field."
                )
            logger.info("2FA required for %s — signing in with password.", phone)
            await self._client.sign_in(password=password)
        except PhoneCodeInvalidError as exc:
            raise ValueError("The OTP code is incorrect.") from exc
        except PhoneCodeExpiredError as exc:
            raise ValueError(
                "The OTP code has expired. Please request a new one."
            ) from exc
        except Exception as exc:
            logger.error("sign_in failed for %s: %s", phone, exc)
            raise RuntimeError(f"Telegram sign-in failed: {exc}") from exc

        # Export session string and clean up pending state
        session_string: str = self._client.session.save()
        _pending.pop(phone, None)

        me: TelegramUser = await self._client.get_me()  # type: ignore[assignment]
        logger.info(
            "Authentication successful for %s (@%s, id=%s).",
            phone,
            me.username,
            me.id,
        )

        await self._disconnect()
        return session_string

    async def get_me(self) -> TelegramUser | None:
        """
        Return the authenticated Telegram user, or None if not authorised.
        Uses the main singleton client's session (not the auth client).
        """
        from app.telegram.client import telegram_client  # avoid circular import

        if not telegram_client.is_connected:
            return None
        if not await telegram_client.is_authorised():
            return None
        me: TelegramUser = await telegram_client.client.get_me()  # type: ignore[assignment]
        return me


# Module-level singleton
telegram_auth_service = TelegramAuthService()
