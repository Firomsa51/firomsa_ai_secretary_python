"""Settings endpoints — read and update the singleton assistant configuration.

Phase 4: now includes autonomous-mode rule fields (allow_auto_reply,
business_hours, cooldown, confidence_threshold, blocked lists, etc.), and
uses the shared settings_service (Phase 2) instead of a local duplicate
get-or-create helper.
"""

from fastapi import APIRouter

from app.dependencies import DBSession
from app.models.settings import Settings
from app.schemas.settings import SettingsRead, SettingsUpdate
from app.services.settings_service import get_or_create_settings

router = APIRouter()


@router.get("/", response_model=SettingsRead)
async def get_settings(db: DBSession) -> Settings:
    """Retrieve the current assistant settings."""
    return await get_or_create_settings(db)


@router.patch("/", response_model=SettingsRead)
async def update_settings(payload: SettingsUpdate, db: DBSession) -> Settings:
    """Partially update assistant settings, including Phase 4 auto-reply rules."""
    settings = await get_or_create_settings(db)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(settings, field, value)
    await db.flush()
    await db.refresh(settings)
    return settings
