"""
API routes package.

This package contains all the route modules for the FastAPI application.
"""

from api.routes import health, properties, markets, investment_scores

__all__ = ["health", "properties", "markets", "investment_scores"]
