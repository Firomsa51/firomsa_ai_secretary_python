"""
FastAPI dependency injection helpers.
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.ai.providers import get_ai_provider, AIProvider

# ── Type aliases ──────────────────────────────────────────────────────────────
# Use these as FastAPI parameter types for clean dependency injection.

DBSession = Annotated[AsyncSession, Depends(get_db)]
ActiveAIProvider = Annotated[AIProvider, Depends(get_ai_provider)]
