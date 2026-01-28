"""
Property routes for API.

This module provides endpoints for querying property data.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import logging

from api.models import (
    PropertyBasic, PropertyDetail, PropertyListResponse, 
    PropertyDetailResponse, PropertyPerformance, PropertyAmenities,
    PropertyReviews, Market, PropertyAnalysis, PropertyAnalysisResponse,
    MarketComparison, PerformanceVsMarket, ComparableProperty
)
from api.database import (
    get_properties, get_property_by_id, get_properties_count,
    get_property_analysis, get_comparable_properties
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _convert_to_property_detail(property_data: dict) -> PropertyDetail:
    """
    Convert database row to PropertyDetail model.
    
    Args:
        property_data: Database row dictionary
    
    Returns:
        PropertyDetail model
    """
    # Extract basic property info
    basic_info = {
        'id': property_data.get('id'),
        'property_id': property_data.get('property_id'),
        'title': property_data.get('title'),
        'bedrooms': property_data.get('bedrooms'),
        'bathrooms': property_data.get('bathrooms'),
        'accommodates': property_data.get('accommodates'),
        'property_type': property_data.get('property_type'),
        'room_type': property_data.get('room_type'),
        'beds': property_data.get('beds'),
        'latitude': property_data.get('latitude'),
        'longitude': property_data.get('longitude'),
        'city_name': property_data.get('city_name'),
        'zipcode': property_data.get('zipcode'),
        'airbnb_listing_url': property_data.get('airbnb_listing_url'),
        'vrbo_listing_url': property_data.get('vrbo_listing_url'),
        'is_guest_favorite': property_data.get('is_guest_favorite', False),
        'is_reliable_data': property_data.get('is_reliable_data', True),
        'created_at': property_data.get('created_at'),
        'updated_at': property_data.get('updated_at')
    }
    
    # Extract market info
    market = None
    if property_data.get('market_id'):
        market = Market(
            id=property_data['market_id'],
            name=property_data.get('market_name'),
            state_name=property_data.get('market_state')
        )
    
    # Extract performance info
    performance = None
    if property_data.get('revenue') is not None:
        performance = PropertyPerformance(
            revenue=property_data.get('revenue'),
            revenue_potential=property_data.get('revenue_potential'),
            adr=property_data.get('adr'),
            cleaning_fee=property_data.get('cleaning_fee'),
            occupancy=property_data.get('occupancy'),
            available_nights=property_data.get('available_nights'),
            total_reviews=property_data.get('total_reviews'),
            rating=property_data.get('rating'),
            property_reviews_count=property_data.get('property_reviews_count'),
            high_season_reviews=property_data.get('high_season_reviews'),
            high_season_label=property_data.get('high_season_label')
        )
    
    # Extract amenities info
    amenities = None
    if property_data.get('amenities') is not None:
        amenities = PropertyAmenities(amenities=property_data['amenities'])
    
    # Extract reviews info
    reviews = None
    if property_data.get('total_months') is not None:
        reviews = PropertyReviews(
            total_months=property_data.get('total_months'),
            missing_months=property_data.get('missing_months'),
            avg_reviews_per_month=property_data.get('avg_reviews_per_month'),
            review_pct_stayed_with_kids=property_data.get('review_pct_stayed_with_kids'),
            review_pct_group_trip=property_data.get('review_pct_group_trip'),
            review_pct_stayed_with_a_pet=property_data.get('review_pct_stayed_with_a_pet')
        )
    
    return PropertyDetail(
        **basic_info,
        market=market,
        performance=performance,
        amenities=amenities,
        reviews=reviews,
        host_is_super_host=property_data.get('host_is_super_host')
    )


@router.get("/properties", response_model=PropertyListResponse, tags=["properties"])
async def list_properties(
    market_id: Optional[str] = Query(None, description="Filter by market ID"),
    min_bedrooms: Optional[int] = Query(None, ge=0, description="Minimum bedrooms"),
    max_bedrooms: Optional[int] = Query(None, ge=0, description="Maximum bedrooms"),
    min_revenue: Optional[float] = Query(None, ge=0, description="Minimum revenue"),
    max_revenue: Optional[float] = Query(None, ge=0, description="Maximum revenue"),
    min_occupancy: Optional[float] = Query(None, ge=0, le=100, description="Minimum occupancy (0-100)"),
    max_occupancy: Optional[float] = Query(None, ge=0, le=100, description="Maximum occupancy (0-100)"),
    min_rating: Optional[float] = Query(None, ge=0, le=5, description="Minimum rating (0-5)"),
    is_guest_favorite: Optional[bool] = Query(None, description="Filter by guest favorite status"),
    is_reliable_data: Optional[bool] = Query(None, description="Filter by reliable data status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Number of items per page"),
    sort_by: Optional[str] = Query(None, description="Field to sort by"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order")
):
    """
    List properties with optional filters and pagination.
    
    Args:
        market_id: Filter by market ID
        min_bedrooms: Filter by minimum bedrooms
        max_bedrooms: Filter by maximum bedrooms
        min_revenue: Filter by minimum revenue
        max_revenue: Filter by maximum revenue
        min_occupancy: Filter by minimum occupancy (0-100)
        max_occupancy: Filter by maximum occupancy (0-100)
        min_rating: Filter by minimum rating (0-5)
        is_guest_favorite: Filter by guest favorite status
        is_reliable_data: Filter by reliable data status
        page: Page number (1-indexed)
        page_size: Number of items per page
        sort_by: Field to sort by
        sort_order: Sort order ('asc' or 'desc')
    
    Returns:
        Paginated list of properties
    """
    try:
        # Get total count
        total = get_properties_count(
            market_id=market_id,
            min_bedrooms=min_bedrooms,
            max_bedrooms=max_bedrooms,
            is_guest_favorite=is_guest_favorite,
            is_reliable_data=is_reliable_data
        )
        
        # Calculate offset
        offset = (page - 1) * page_size
        
        # Get properties
        properties_data = get_properties(
            market_id=market_id,
            min_bedrooms=min_bedrooms,
            max_bedrooms=max_bedrooms,
            min_revenue=min_revenue,
            max_revenue=max_revenue,
            min_occupancy=min_occupancy,
            max_occupancy=max_occupancy,
            min_rating=min_rating,
            is_guest_favorite=is_guest_favorite,
            is_reliable_data=is_reliable_data,
            limit=page_size,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        # Convert to Pydantic models
        properties = [PropertyBasic(**prop) for prop in properties_data]
        
        # Calculate total pages
        total_pages = (total + page_size - 1) // page_size
        
        return PropertyListResponse(
            success=True,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            data=properties
        )
    except Exception as e:
        logger.error(f"Error listing properties: {e}")
        raise HTTPException(status_code=500, detail=f"Error listing properties: {str(e)}")


@router.get("/properties/{property_id}", response_model=PropertyDetailResponse, tags=["properties"])
async def get_property(property_id: str):
    """
    Get a property by its ID with all related data.
    
    Args:
        property_id: UUID of property
    
    Returns:
        Property details with all related data
    """
    try:
        property_data = get_property_by_id(property_id)
        
        if not property_data:
            raise HTTPException(status_code=404, detail=f"Property with ID {property_id} not found")
        
        property_detail = _convert_to_property_detail(property_data)
        
        return PropertyDetailResponse(
            success=True,
            data=property_detail
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting property {property_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting property: {str(e)}")


@router.get("/properties/{property_id}/analysis", response_model=PropertyAnalysisResponse, tags=["properties"])
async def get_property_analysis_endpoint(
    property_id: str,
    include_comparables: bool = Query(True, description="Include comparable properties nearby")
):
    """
    Get property details with score breakdown and market comparison.
    
    This endpoint provides comprehensive property analysis including:
    - Score breakdown across all components
    - Comparison to market averages (same bedroom count, same market)
    - Comparable properties nearby (optional)
    
    Args:
        property_id: UUID of property
        include_comparables: Whether to include comparable properties nearby
    
    Returns:
        Property analysis with market comparison and optional comparables
    """
    try:
        # Get property analysis from materialized view
        analysis_data = get_property_analysis(property_id)
        
        if not analysis_data:
            raise HTTPException(status_code=404, detail=f"Property with ID {property_id} not found")
        
        # Build market comparison
        market_comparison = MarketComparison(
            property_count=analysis_data.get('market_property_count'),
            avg_revenue=analysis_data.get('market_avg_revenue'),
            avg_occupancy=analysis_data.get('market_avg_occupancy'),
            avg_adr=analysis_data.get('market_avg_adr'),
            avg_rating=analysis_data.get('market_avg_rating'),
            avg_total_score=analysis_data.get('market_avg_total_score'),
            median_revenue=analysis_data.get('market_median_revenue'),
            median_occupancy=analysis_data.get('market_median_occupancy'),
            median_adr=analysis_data.get('market_median_adr'),
            median_rating=analysis_data.get('market_median_rating'),
            median_total_score=analysis_data.get('market_median_total_score')
        )
        
        # Build performance vs market
        performance_vs_market = PerformanceVsMarket(
            revenue_vs_market_pct=analysis_data.get('revenue_vs_market_pct'),
            occupancy_vs_market_pct=analysis_data.get('occupancy_vs_market_pct'),
            adr_vs_market_pct=analysis_data.get('adr_vs_market_pct'),
            rating_vs_market_pct=analysis_data.get('rating_vs_market_pct')
        )
        
        # Build property analysis
        property_analysis = PropertyAnalysis(
            id=analysis_data.get('id'),
            property_id=analysis_data.get('property_id'),
            title=analysis_data.get('title'),
            bedrooms=analysis_data.get('bedrooms'),
            bathrooms=analysis_data.get('bathrooms'),
            accommodates=analysis_data.get('accommodates'),
            property_type=analysis_data.get('property_type'),
            room_type=analysis_data.get('room_type'),
            beds=analysis_data.get('beds'),
            latitude=analysis_data.get('latitude'),
            longitude=analysis_data.get('longitude'),
            city_name=analysis_data.get('city_name'),
            zipcode=analysis_data.get('zipcode'),
            airbnb_listing_url=analysis_data.get('airbnb_listing_url'),
            vrbo_listing_url=analysis_data.get('vrbo_listing_url'),
            is_guest_favorite=analysis_data.get('is_guest_favorite', False),
            is_reliable_data=analysis_data.get('is_reliable_data', True),
            market_id=analysis_data.get('market_id'),
            market_name=analysis_data.get('market_name'),
            market_state=analysis_data.get('market_state'),
            revenue=analysis_data.get('revenue'),
            revenue_potential=analysis_data.get('revenue_potential'),
            adr=analysis_data.get('adr'),
            cleaning_fee=analysis_data.get('cleaning_fee'),
            occupancy=analysis_data.get('occupancy'),
            available_nights=analysis_data.get('available_nights'),
            total_reviews=analysis_data.get('total_reviews'),
            rating=analysis_data.get('rating'),
            property_reviews_count=analysis_data.get('property_reviews_count'),
            high_season_reviews=analysis_data.get('high_season_reviews'),
            high_season_label=analysis_data.get('high_season_label'),
            revenue_score=analysis_data.get('revenue_score'),
            occupancy_score=analysis_data.get('occupancy_score'),
            adr_score=analysis_data.get('adr_score'),
            review_score=analysis_data.get('review_score'),
            amenity_score=analysis_data.get('amenity_score'),
            host_score=analysis_data.get('host_score'),
            seasonal_score=analysis_data.get('seasonal_score'),
            market_score=analysis_data.get('market_score'),
            total_score=analysis_data.get('total_score'),
            percentile_rank=analysis_data.get('percentile_rank'),
            is_top_opportunity=analysis_data.get('is_top_opportunity', False),
            opportunity_tier=analysis_data.get('opportunity_tier'),
            scoring_version=analysis_data.get('scoring_version'),
            score_calculated_at=analysis_data.get('score_calculated_at'),
            host_is_super_host=analysis_data.get('host_is_super_host'),
            market_comparison=market_comparison,
            performance_vs_market=performance_vs_market
        )
        
        # Get comparable properties if requested
        comparables = None
        if include_comparables:
            comparables_data = get_comparable_properties(
                property_id=property_id,
                market_id=analysis_data.get('market_id'),
                bedrooms=analysis_data.get('bedrooms'),
                latitude=analysis_data.get('latitude'),
                longitude=analysis_data.get('longitude'),
                limit=5
            )
            comparables = [
                ComparableProperty(
                    id=comp.get('id'),
                    property_id=comp.get('property_id'),
                    title=comp.get('title'),
                    bedrooms=comp.get('bedrooms'),
                    bathrooms=comp.get('bathrooms'),
                    distance_km=comp.get('distance_km'),
                    revenue=comp.get('revenue'),
                    occupancy=comp.get('occupancy'),
                    adr=comp.get('adr'),
                    rating=comp.get('rating'),
                    total_score=comp.get('total_score'),
                    opportunity_tier=comp.get('opportunity_tier')
                )
                for comp in comparables_data
            ]
        
        return PropertyAnalysisResponse(
            success=True,
            data=property_analysis,
            comparables=comparables
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting property analysis {property_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting property analysis: {str(e)}")
