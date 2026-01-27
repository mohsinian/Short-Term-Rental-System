"""
Health check routes for the API.

This module provides endpoints for checking the health status of the API
and its dependencies.
"""

from fastapi import APIRouter
from datetime import datetime
import logging

from api.models import HealthCheckResponse
from api.database import check_database_connection

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", response_model=HealthCheckResponse, tags=["health"])
async def health_check():
    """
    Health check endpoint.

    Returns the health status of the API and its dependencies.
    """
    db_status = "connected" if check_database_connection() else "disconnected"

    return HealthCheckResponse(
        status="healthy" if db_status == "connected" else "degraded",
        database=db_status,
        timestamp=datetime.utcnow(),
        version="1.0.0"
    )
