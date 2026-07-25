"""Health check endpoint."""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


@router.get("/health", response_model=HealthResponse, summary="Health check")
async def health_check() -> HealthResponse:
    """Returns 200 OK when the service is running."""
    return HealthResponse(
        status="running",
        service="Firomsa AI Secretary",
        version="0.1.0",
    )
