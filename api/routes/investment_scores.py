"""
Investment score routes for API.

This module provides endpoints for querying investment opportunity scores.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import logging

from api.models import (
    InvestmentScoreWithProperty,
    InvestmentScoreListResponse,
    TopOpportunityResponse,
    UndervaluedOpportunityResponse,
)
from api.database import (
    get_investment_scores,
    get_top_opportunities,
    get_top_opportunities_from_mv,
    get_undervalued_opportunities,
    get_investment_scores_count,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _convert_to_investment_score_with_property(
    score_data: dict,
) -> InvestmentScoreWithProperty:
    """
    Convert database row to InvestmentScoreWithProperty model.

    Handles column name differences between database function and API model.
    Supports both RPC function results and materialized view queries.

    Args:
        score_data: Database row dictionary

    Returns:
        InvestmentScoreWithProperty model
    """
    # Handle id - for mv_top_performers, id is the property UUID
    # For RPC functions, it might be in 'id' or 'property_id'
    record_id = score_data.get("id")
    if not record_id:
        record_id = score_data.get("property_id")
    if not record_id:
        raise ValueError(
            f"No id or property_id found in score_data: {list(score_data.keys())}"
        )

    # property_id field in mv_top_performers is the external_id (e.g., "12345678")
    # while id is the internal UUID
    external_property_id = score_data.get("property_id") or score_data.get(
        "external_id"
    )

    return InvestmentScoreWithProperty(
        id=str(record_id),
        property_id=str(external_property_id)
        if external_property_id
        else str(record_id),
        revenue_score=score_data.get("revenue_score"),
        occupancy_score=score_data.get("occupancy_score"),
        adr_score=score_data.get("adr_score"),
        review_score=score_data.get("review_score"),
        amenity_score=score_data.get("amenity_score"),
        host_score=score_data.get("host_score"),
        seasonal_score=score_data.get("seasonal_score"),
        market_score=score_data.get("market_score"),
        total_score=score_data.get("total_score"),
        percentile_rank=score_data.get("percentile_rank"),
        is_top_opportunity=score_data.get(
            "is_top_opportunity", True
        ),  # Default to True for top opportunities
        opportunity_tier=score_data.get("opportunity_tier"),
        scoring_version=score_data.get("scoring_version", "1.0"),
        calculated_at=score_data.get("calculated_at")
        or score_data.get("score_calculated_at"),
        property_title=score_data.get("title") or score_data.get("property_title"),
        property_bedrooms=score_data.get("bedrooms")
        or score_data.get("property_bedrooms"),
        market_name=score_data.get("market_name") or score_data.get("market"),
        property_revenue=score_data.get("revenue")
        or score_data.get("property_revenue"),
        property_occupancy=score_data.get("occupancy")
        or score_data.get("property_occupancy"),
        property_adr=score_data.get("adr") or score_data.get("property_adr"),
        property_rating=score_data.get("rating") or score_data.get("property_rating"),
    )


@router.get(
    "/investment-scores",
    response_model=InvestmentScoreListResponse,
    tags=["investment-scores"],
)
async def list_investment_scores(
    market_id: Optional[str] = Query(None, description="Filter by market ID"),
    min_total_score: Optional[float] = Query(
        None, ge=0, le=100, description="Minimum total score (0-100)"
    ),
    max_total_score: Optional[float] = Query(
        None, ge=0, le=100, description="Maximum total score (0-100)"
    ),
    opportunity_tier: Optional[str] = Query(
        None,
        pattern="^(PLATINUM|GOLD|SILVER|BRONZE)$",
        description="Filter by opportunity tier",
    ),
    is_top_opportunity: Optional[bool] = Query(
        None, description="Filter by top opportunity status"
    ),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Number of items per page"),
    sort_by: Optional[str] = Query(None, description="Field to sort by"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
):
    """
    List investment scores with optional filters and pagination.

    Args:
        market_id: Filter by market ID
        min_total_score: Filter by minimum total score (0-100)
        max_total_score: Filter by maximum total score (0-100)
        opportunity_tier: Filter by opportunity tier (PLATINUM, GOLD, SILVER, BRONZE)
        is_top_opportunity: Filter by top opportunity status
        page: Page number (1-indexed)
        page_size: Number of items per page
        sort_by: Field to sort by
        sort_order: Sort order ('asc' or 'desc')

    Returns:
        Paginated list of investment scores with property details
    """
    try:
        # Get total count
        total = get_investment_scores_count(
            market_id=market_id,
            min_total_score=min_total_score,
            max_total_score=max_total_score,
            opportunity_tier=opportunity_tier,
            is_top_opportunity=is_top_opportunity,
        )

        # Calculate offset
        offset = (page - 1) * page_size

        # Get investment scores
        scores_data = get_investment_scores(
            market_id=market_id,
            min_total_score=min_total_score,
            max_total_score=max_total_score,
            opportunity_tier=opportunity_tier,
            is_top_opportunity=is_top_opportunity,
            limit=page_size,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        # Convert to Pydantic models
        scores = [
            _convert_to_investment_score_with_property(score) for score in scores_data
        ]

        # Calculate total pages
        total_pages = (total + page_size - 1) // page_size

        return InvestmentScoreListResponse(
            success=True,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            data=scores,
        )
    except Exception as e:
        logger.error(f"Error listing investment scores: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error listing investment scores: {str(e)}"
        )


@router.get(
    "/investment-scores/top-opportunities",
    response_model=TopOpportunityResponse,
    tags=["investment-scores"],
)
async def get_top_opportunities_endpoint(
    limit: int = Query(
        20, ge=1, le=100, description="Maximum number of opportunities to return"
    ),
):
    """
    Get top investment opportunities.

    Uses the materialized view mv_top_performers for optimized performance,
    which returns properties with is_top_opportunity = TRUE, sorted by total_score DESC.

    Args:
        limit: Maximum number of opportunities to return (1-100)

    Returns:
        List of top investment opportunities
    """
    try:
        logger.info(f"Fetching top opportunities with limit={limit}")
        opportunities_data = get_top_opportunities_from_mv(limit=limit)
        logger.info(f"Retrieved {len(opportunities_data)} opportunities from database")

        # Log first row to see actual columns
        if opportunities_data:
            logger.info(
                f"First opportunity data keys: {list(opportunities_data[0].keys())}"
            )
            for key in ["id", "property_id", "title", "total_score"]:
                value = opportunities_data[0].get(key)
                logger.info(f"  {key}: {value} (type: {type(value).__name__})")

        # Convert to Pydantic models
        opportunities = [
            _convert_to_investment_score_with_property(opp)
            for opp in opportunities_data
        ]
        logger.info(
            f"Successfully converted {len(opportunities)} opportunities to Pydantic models"
        )

        return TopOpportunityResponse(success=True, data=opportunities)
    except Exception as e:
        logger.error(f"Error getting top opportunities: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error getting top opportunities: {str(e)}"
        )


@router.get(
    "/investment-scores/undervalued-opportunities",
    response_model=UndervaluedOpportunityResponse,
    tags=["investment-scores"],
)
async def get_undervalued_opportunities_endpoint(
    limit: int = Query(
        10, ge=1, le=100, description="Maximum number of opportunities to return"
    ),
):
    """
    Get undervalued investment opportunities.

    Uses the database function get_undervalued_opportunities() which returns
    properties with strong fundamentals (occupancy, reviews) but below-average
    revenue performance.

    Args:
        limit: Maximum number of opportunities to return (1-100)

    Returns:
        List of undervalued investment opportunities
    """
    try:
        opportunities_data = get_undervalued_opportunities(limit=limit)

        # Convert to Pydantic models
        opportunities = [
            _convert_to_investment_score_with_property(opp)
            for opp in opportunities_data
        ]

        return UndervaluedOpportunityResponse(success=True, data=opportunities)
    except Exception as e:
        logger.error(f"Error getting undervalued opportunities: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error getting undervalued opportunities: {str(e)}"
        )
