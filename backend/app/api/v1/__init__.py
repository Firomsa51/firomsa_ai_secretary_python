"""API v1 — routes aggregator."""

from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.api.v1.users import router as users_router
from app.api.v1.conversations import router as conversations_router
from app.api.v1.messages import router as messages_router
from app.api.v1.memories import router as memories_router
from app.api.v1.settings import router as settings_router
from app.api.v1.telegram import router as telegram_router
from app.api.v1.drafts import router as drafts_router

router = APIRouter()
router.include_router(health_router, tags=["Health"])
router.include_router(users_router, prefix="/users", tags=["Users"])
router.include_router(conversations_router, prefix="/conversations", tags=["Conversations"])
router.include_router(messages_router, prefix="/messages", tags=["Messages"])
router.include_router(memories_router, prefix="/memories", tags=["Memories"])
router.include_router(settings_router, prefix="/settings", tags=["Settings"])
router.include_router(telegram_router)   # prefix="/telegram" set on the router itself
router.include_router(drafts_router, prefix="/drafts", tags=["Drafts"])
