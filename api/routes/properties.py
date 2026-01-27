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
    PropertyReviews, Market
)
from api.database import (
    get_properties, get_property_by_id, get_properties_count
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
