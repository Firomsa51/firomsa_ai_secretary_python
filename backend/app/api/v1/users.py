"""User CRUD endpoints."""

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.dependencies import DBSession
from app.models.user import User
from app.schemas.user import UserCreate, UserRead

router = APIRouter()


@router.post("/", response_model=UserRead, status_code=201)
async def create_user(payload: UserCreate, db: DBSession) -> User:
    """Register a Telegram user in the database."""
    existing = await db.scalar(select(User).where(User.telegram_id == payload.telegram_id))
    if existing:
        raise HTTPException(status_code=409, detail="User with this telegram_id already exists.")
    user = User(**payload.model_dump())
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@router.get("/{telegram_id}", response_model=UserRead)
async def get_user(telegram_id: int, db: DBSession) -> User:
    """Retrieve a user by their Telegram ID."""
    user = await db.scalar(select(User).where(User.telegram_id == telegram_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return user


@router.get("/", response_model=list[UserRead])
async def list_users(db: DBSession, limit: int = 50, offset: int = 0) -> list[User]:
    """List all tracked users (paginated)."""
    result = await db.scalars(select(User).order_by(User.created_at.desc()).limit(limit).offset(offset))
    return list(result.all())
