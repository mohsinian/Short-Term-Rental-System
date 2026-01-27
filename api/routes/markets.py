"""
Market routes for API.

This module provides endpoints for querying market data.
"""

from fastapi import APIRouter, HTTPException, Query
import logging

from api.models import Market, MarketListResponse, MarketDetailResponse
from api.database import get_all_markets, get_market_by_id, get_market_count

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/markets", response_model=MarketListResponse, tags=["markets"])
async def list_markets(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Number of items per page")
):
    """
    List all markets with pagination.
    
    Args:
        page: Page number (1-indexed)
        page_size: Number of items per page
    
    Returns:
        Paginated list of markets
    """
    try:
        # Get total count
        total = get_market_count()
        
        # Calculate offset
        offset = (page - 1) * page_size
        
        # Get markets
        markets_data = get_all_markets(limit=page_size, offset=offset)
        
        # Convert to Pydantic models
        markets = [Market(**market) for market in markets_data]
        
        # Calculate total pages
        total_pages = (total + page_size - 1) // page_size
        
        return MarketListResponse(
            success=True,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            data=markets
        )
    except Exception as e:
        logger.error(f"Error listing markets: {e}")
        raise HTTPException(status_code=500, detail=f"Error listing markets: {str(e)}")


@router.get("/markets/{market_id}", response_model=MarketDetailResponse, tags=["markets"])
async def get_market(market_id: str):
    """
    Get a market by its ID.
    
    Args:
        market_id: UUID of the market
    
    Returns:
        Market details
    """
    try:
        market_data = get_market_by_id(market_id)
        
        if not market_data:
            raise HTTPException(status_code=404, detail=f"Market with ID {market_id} not found")
        
        market = Market(**market_data)
        
        return MarketDetailResponse(
            success=True,
            data=market
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting market {market_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting market: {str(e)}")
