"""
Telegram authentication and status endpoints.

POST /api/v1/telegram/auth/request  — send OTP to phone
POST /api/v1/telegram/auth/verify   — confirm OTP (+ optional 2FA password)
GET  /api/v1/telegram/status        — connection + authorisation info

TEMPORARY:
GET  /api/v1/telegram/debug/session-string — exports the current session
     string so it can be copied into the TELEGRAM_SESSION env var on Render.
     REMOVE THIS ENDPOINT after copying the value once — it is a secret.
"""

import logging

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.dependencies import DBSession
from app.telegram.auth import telegram_auth_service
from app.telegram.client import telegram_client
from app.telegram.session_store import load_session_string, save_session_string

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telegram", tags=["Telegram"])


# ── Request / Response schemas ────────────────────────────────────────────────

class AuthRequestPayload(BaseModel):
    phone: str = Field(
        ...,
        description="Phone number with country code, e.g. +1234567890",
        examples=["+1234567890"],
    )


class AuthRequestResponse(BaseModel):
    success: bool
    message: str


class AuthVerifyPayload(BaseModel):
    phone: str = Field(..., description="Same phone number used in /auth/request")
    code: str = Field(..., description="One-time password received via Telegram")
    password: str | None = Field(
        default=None,
        description="Two-Factor Authentication password (only if 2FA is enabled)",
    )


class AuthVerifyResponse(BaseModel):
    success: bool
    message: str
    # Session string is intentionally excluded — stored internally, never returned.


class TelegramStatusResponse(BaseModel):
    connected: bool
    authorised: bool
    username: str | None
    telegram_user_id: int | None
    first_name: str | None


class DebugSessionStringResponse(BaseModel):
    session_string: str | None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/auth/request",
    response_model=AuthRequestResponse,
    status_code=status.HTTP_200_OK,
    summary="Request Telegram OTP",
)
async def auth_request(payload: AuthRequestPayload) -> AuthRequestResponse:
    """
    Send a Telegram one-time password (OTP) to the given phone number.
    Must be called before /auth/verify.
    """
    logger.info("OTP request for phone=%s", payload.phone)
    try:
        await telegram_auth_service.request_code(payload.phone)
    except RuntimeError as exc:
        logger.error("OTP request failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return AuthRequestResponse(
        success=True,
        message="OTP sent. Check your Telegram app and call /auth/verify.",
    )


@router.post(
    "/auth/verify",
    response_model=AuthVerifyResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify OTP and authenticate",
)
async def auth_verify(
    payload: AuthVerifyPayload,
    db: DBSession,
) -> AuthVerifyResponse:
    """
    Verify the OTP received on Telegram.

    - Provide `password` only if the account has Two-Factor Authentication enabled.
    - On success, the StringSession is stored securely in the database and the
      main Telegram client is connected automatically.
    - The session string is **never** returned in the response.
    """
    logger.info("OTP verification attempt for phone=%s", payload.phone)

    try:
        session_string = await telegram_auth_service.verify_code(
            phone=payload.phone,
            code=payload.code,
            password=payload.password,
        )
    except ValueError as exc:
        # Expected user errors: wrong code, expired code, 2FA missing, etc.
        logger.warning("OTP verification rejected: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        logger.error("OTP verification failed unexpectedly: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    # Persist session to DB so it survives restarts
    await save_session_string(db, session_string)
    logger.info("Session string persisted to database.")

    # Connect the main runtime client with the new session
    try:
        await telegram_client.reconnect_with_session(session_string)
        logger.info("Main Telegram client reconnected with new session.")
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to reconnect main client after auth: %s", exc)
        # Auth succeeded — don't fail the request; client will reconnect on next restart.

    return AuthVerifyResponse(
        success=True,
        message="Authenticated successfully. Telegram client is now active.",
    )


@router.get(
    "/status",
    response_model=TelegramStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Telegram connection status",
)
async def telegram_status() -> TelegramStatusResponse:
    """
    Return the current Telegram connection and authorisation status.
    Includes the logged-in username and Telegram user ID when authorised.
    """
    connected = telegram_client.is_connected
    authorised = await telegram_client.is_authorised() if connected else False

    username: str | None = None
    telegram_user_id: int | None = None
    first_name: str | None = None

    if authorised:
        try:
            me = await telegram_client.client.get_me()
            if me is not None:
                username = getattr(me, "username", None)
                telegram_user_id = getattr(me, "id", None)
                first_name = getattr(me, "first_name", None)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not fetch 'get_me' during status check: %s", exc)

    return TelegramStatusResponse(
        connected=connected,
        authorised=authorised,
        username=username,
        telegram_user_id=telegram_user_id,
        first_name=first_name,
    )


@router.get(
    "/debug/session-string",
    response_model=DebugSessionStringResponse,
    status_code=status.HTTP_200_OK,
    summary="[TEMPORARY] Export current session string for backup",
)
async def debug_get_session_string(db: DBSession) -> DebugSessionStringResponse:
    """
    TEMPORARY DEBUG ENDPOINT.

    Returns the Telegram StringSession currently stored in the database so it
    can be copied into the TELEGRAM_SESSION environment variable on Render.
    This makes the session survive database resets/migrations, not just
    container restarts.

    SECURITY: This session string grants full access to the Telegram account.
    Remove this endpoint (and this route) immediately after copying the value
    once — do not leave it deployed.
    """
    session = await load_session_string(db)
    return DebugSessionStringResponse(session_string=session)
