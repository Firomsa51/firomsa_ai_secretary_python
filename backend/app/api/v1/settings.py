"""Settings endpoints — read and update the singleton assistant configuration."""

from fastapi import APIRouter
from sqlalchemy import select

from app.dependencies import DBSession
from app.models.settings import Settings
from app.schemas.settings import SettingsRead, SettingsUpdate

router = APIRouter()


async def _get_or_create_settings(db: DBSession) -> Settings:
    """Return the singleton Settings row, creating it if missing."""
    settings = await db.scalar(select(Settings))
    if not settings:
        settings = Settings()
        db.add(settings)
        await db.flush()
        await db.refresh(settings)
    return settings


@router.get("/", response_model=SettingsRead)
async def get_settings(db: DBSession) -> Settings:
    """Retrieve the current assistant settings."""
    return await _get_or_create_settings(db)


@router.patch("/", response_model=SettingsRead)
async def update_settings(payload: SettingsUpdate, db: DBSession) -> Settings:
    """Partially update assistant settings."""
    settings = await _get_or_create_settings(db)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(settings, field, value)
    await db.flush()
    await db.refresh(settings)
    return settings
