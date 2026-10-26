"""Health check routes."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: Literal["ok"]


@router.get("/health/live", response_model=HealthResponse, summary="Liveness probe")
def get_liveness() -> HealthResponse:
    """Report that the API process is responding."""
    return HealthResponse(status="ok")
