"""
FastAPI application for Short-Term Rental System API.

This API provides endpoints for querying property data, market analysis,
and investment scores from the PostgreSQL/Supabase database.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from api.routes import properties, markets, investment_scores, health

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    logger.info("Starting up Short-Term Rental System API...")
    yield
    # Shutdown
    logger.info("Shutting down Short-Term Rental System API...")


# Create FastAPI application
app = FastAPI(
    title="Short-Term Rental System API",
    description="API for querying property data, market analysis, and investment scores",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(properties.router, prefix="/api/v1", tags=["properties"])
app.include_router(markets.router, prefix="/api/v1", tags=["markets"])
app.include_router(investment_scores.router, prefix="/api/v1", tags=["investment-scores"])


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Short-Term Rental System API",
        "version": "1.0.0",
        "status": "operational",
        "documentation": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
