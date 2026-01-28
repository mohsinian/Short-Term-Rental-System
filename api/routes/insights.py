"""
Insights routes for API.

This module provides endpoints for investment insights and top performers.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import logging

from api.models import (
    TopPerformer,
    TopPerformersResponse,
    TopPerformersGroup,
    BaseResponse,
)
from api.database import (
    get_top_performers,
    get_top_performers_by_market,
    get_top_performers_grouped,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _convert_to_top_performer(performer_data: dict) -> TopPerformer:
    """
    Convert database row to TopPerformer model.

    Args:
        performer_data: Database row dictionary

    Returns:
        TopPerformer model
    """
    return TopPerformer(
        id=performer_data.get("id"),
        property_id=performer_data.get("property_id"),
        title=performer_data.get("title"),
        bedrooms=performer_data.get("bedrooms"),
        bathrooms=performer_data.get("bathrooms"),
        accommodates=performer_data.get("accommodates"),
        property_type=performer_data.get("property_type"),
        room_type=performer_data.get("room_type"),
        beds=performer_data.get("beds"),
        latitude=performer_data.get("latitude"),
        longitude=performer_data.get("longitude"),
        city_name=performer_data.get("city_name"),
        zipcode=performer_data.get("zipcode"),
        airbnb_listing_url=performer_data.get("airbnb_listing_url"),
        vrbo_listing_url=performer_data.get("vrbo_listing_url"),
        is_guest_favorite=performer_data.get("is_guest_favorite", False),
        is_reliable_data=performer_data.get("is_reliable_data", True),
        market_id=performer_data.get("market_id"),
        market_name=performer_data.get("market_name"),
        market_state=performer_data.get("market_state"),
        revenue=performer_data.get("revenue"),
        revenue_potential=performer_data.get("revenue_potential"),
        adr=performer_data.get("adr"),
        cleaning_fee=performer_data.get("cleaning_fee"),
        occupancy=performer_data.get("occupancy"),
        available_nights=performer_data.get("available_nights"),
        total_reviews=performer_data.get("total_reviews"),
        rating=performer_data.get("rating"),
        property_reviews_count=performer_data.get("property_reviews_count"),
        high_season_reviews=performer_data.get("high_season_reviews"),
        high_season_label=performer_data.get("high_season_label"),
        revenue_score=performer_data.get("revenue_score"),
        occupancy_score=performer_data.get("occupancy_score"),
        adr_score=performer_data.get("adr_score"),
        review_score=performer_data.get("review_score"),
        amenity_score=performer_data.get("amenity_score"),
        host_score=performer_data.get("host_score"),
        seasonal_score=performer_data.get("seasonal_score"),
        market_score=performer_data.get("market_score"),
        total_score=performer_data.get("total_score"),
        percentile_rank=performer_data.get("percentile_rank"),
        is_top_opportunity=performer_data.get("is_top_opportunity", False),
        opportunity_tier=performer_data.get("opportunity_tier"),
        scoring_version=performer_data.get("scoring_version"),
        score_calculated_at=performer_data.get("score_calculated_at"),
        is_super_host=performer_data.get("is_super_host"),
        rank_in_category=performer_data.get("rank_in_category"),
        overall_rank=performer_data.get("overall_rank"),
        category_count=performer_data.get("category_count"),
        category_percentile=performer_data.get("category_percentile"),
        key_differentiator=performer_data.get("key_differentiator"),
    )


def _convert_to_top_performers_group(group_data: dict) -> TopPerformersGroup:
    """
    Convert database row to TopPerformersGroup model.

    Args:
        group_data: Database row dictionary with properties array

    Returns:
        TopPerformersGroup model
    """
    properties = [TopPerformer(**prop) for prop in (group_data.get("properties") or [])]

    return TopPerformersGroup(
        market_id=group_data.get("market_id"),
        market_name=group_data.get("market_name"),
        market_state=group_data.get("market_state"),
        bedroom_count=group_data.get("bedroom_count"),
        properties=properties,
        count=len(properties),
    )


@router.get(
    "/insights/top-performers", response_model=TopPerformersResponse, tags=["insights"]
)
async def get_top_performers_endpoint(
    market_id: Optional[str] = Query(None, description="Filter by market ID"),
    group_by: Optional[str] = Query(
        None, pattern="^(market|none)$", description="Group results by market"
    ),
    limit: int = Query(
        20, ge=1, le=100, description="Maximum number of performers to return"
    ),
):
    """
    Get top 20 investment opportunities across all markets.

    This endpoint returns the highest-scoring investment properties,
    showing key differentiating factors and optionally grouping by market
    and bedroom category.

    Args:
        market_id: Optional filter to get top performers for a specific market
        group_by: Optional grouping strategy ('market' or 'none')
        limit: Maximum number of performers to return (1-100)

    Returns:
        Top performers with ranking and differentiating factors
    """
    try:
        if market_id:
            # Get top performers for specific market
            performers_data = get_top_performers_by_market(market_id)
        else:
            # Get top performers across all markets
            performers_data = get_top_performers(limit=limit)

        if not performers_data:
            return TopPerformersResponse(
                success=True, data=[], grouped_by_market=None, total_count=0
            )

        # Convert to Pydantic models
        performers = [_convert_to_top_performer(p) for p in performers_data]

        # Get grouped data if requested
        grouped_by_market = None
        if group_by == "market" and not market_id:
            groups_data = get_top_performers_grouped()
            grouped_by_market = [
                _convert_to_top_performers_group(g) for g in groups_data
            ]

        return TopPerformersResponse(
            success=True,
            data=performers,
            grouped_by_market=grouped_by_market,
            total_count=len(performers),
        )
    except Exception as e:
        logger.error(f"Error getting top performers: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error getting top performers: {str(e)}"
        )


@router.post("/insights/refresh-views", response_model=BaseResponse, tags=["insights"])
async def refresh_materialized_views():
    """
    Refresh all materialized views.

    This endpoint triggers a refresh of all materialized views to ensure
    the data is up-to-date. Use this after running the data pipeline
    or scoring operations.

    Returns:
        Success/failure message
    """
    try:
        from api.database import refresh_all_materialized_views

        success = refresh_all_materialized_views()

        if success:
            return BaseResponse(
                success=True, message="Materialized views refreshed successfully"
            )
        else:
            raise HTTPException(
                status_code=500, detail="Failed to refresh materialized views"
            )
    except Exception as e:
        logger.error(f"Error refreshing materialized views: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error refreshing materialized views: {str(e)}"
        )
