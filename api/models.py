"""
Pydantic models for API request and response schemas.

These models define the structure of data exchanged between the API and clients.
"""

from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


# ============================================================================
# Base Models
# ============================================================================


class BaseResponse(BaseModel):
    """Base response model with common fields."""

    success: bool = True
    message: Optional[str] = None


class PaginatedResponse(BaseResponse):
    """Paginated response model."""

    total: int
    page: int
    page_size: int
    total_pages: int


# ============================================================================
# Market Models
# ============================================================================


class Market(BaseModel):
    """Market model."""

    id: str
    name: str
    state_name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class MarketListResponse(PaginatedResponse):
    """Response model for market list."""

    data: List[Market]


class MarketDetailResponse(BaseResponse):
    """Response model for market detail."""

    data: Market


# ============================================================================
# Property Models
# ============================================================================


class PropertyBasic(BaseModel):
    """Basic property information."""

    id: str
    property_id: str
    title: Optional[str] = None
    bedrooms: Optional[float] = None
    bathrooms: Optional[float] = None
    accommodates: Optional[int] = None
    property_type: Optional[str] = None
    room_type: Optional[str] = None
    beds: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    city_name: Optional[str] = None
    zipcode: Optional[str] = None
    airbnb_listing_url: Optional[str] = None
    vrbo_listing_url: Optional[str] = None
    is_guest_favorite: bool = False
    is_reliable_data: bool = True


class PropertyPerformance(BaseModel):
    """Property performance metrics."""

    revenue: Optional[float] = None
    revenue_potential: Optional[float] = None
    adr: Optional[float] = None
    cleaning_fee: Optional[float] = None
    occupancy: Optional[float] = None
    available_nights: Optional[int] = None
    total_reviews: Optional[int] = None
    rating: Optional[float] = None
    property_reviews_count: Optional[int] = None
    high_season_reviews: Optional[int] = None
    high_season_label: Optional[str] = None


class PropertyAmenities(BaseModel):
    """Property amenities (JSONB)."""

    amenities: Optional[dict] = None


class PropertyReviews(BaseModel):
    """Property review statistics."""

    total_months: Optional[int] = None
    missing_months: Optional[int] = None
    avg_reviews_per_month: Optional[float] = None
    review_pct_stayed_with_kids: Optional[float] = None
    review_pct_group_trip: Optional[float] = None
    review_pct_stayed_with_a_pet: Optional[float] = None


class PropertyDetail(PropertyBasic):
    """Complete property detail with all related data."""

    market: Optional[Market] = None
    performance: Optional[PropertyPerformance] = None
    amenities: Optional[PropertyAmenities] = None
    reviews: Optional[PropertyReviews] = None
    host_is_super_host: Optional[bool] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PropertyListResponse(PaginatedResponse):
    """Response model for property list."""

    data: List[PropertyBasic]


class PropertyDetailResponse(BaseResponse):
    """Response model for property detail."""

    data: PropertyDetail


# ============================================================================
# Investment Score Models
# ============================================================================


class InvestmentScore(BaseModel):
    """Investment score model."""

    id: str
    property_id: str
    revenue_score: Optional[float] = None
    occupancy_score: Optional[float] = None
    adr_score: Optional[float] = None
    review_score: Optional[float] = None
    amenity_score: Optional[float] = None
    host_score: Optional[float] = None
    seasonal_score: Optional[float] = None
    market_score: Optional[float] = None
    total_score: Optional[float] = None
    percentile_rank: Optional[float] = None
    is_top_opportunity: bool = False
    opportunity_tier: Optional[str] = None
    scoring_version: Optional[str] = "1.0"
    calculated_at: Optional[datetime] = None


class InvestmentScoreWithProperty(InvestmentScore):
    """Investment score with property details."""

    property_title: Optional[str] = None
    property_bedrooms: Optional[float] = None
    market_name: Optional[str] = None
    property_revenue: Optional[float] = None
    property_occupancy: Optional[float] = None
    property_adr: Optional[float] = None
    property_rating: Optional[float] = None


class InvestmentScoreListResponse(PaginatedResponse):
    """Response model for investment score list."""

    data: List[InvestmentScoreWithProperty]


class TopOpportunityResponse(BaseResponse):
    """Response model for top opportunities."""

    data: List[InvestmentScoreWithProperty]


class UndervaluedOpportunityResponse(BaseResponse):
    """Response model for undervalued opportunities."""

    data: List[InvestmentScoreWithProperty]


# ============================================================================
# Query Parameters Models
# ============================================================================


class PropertyQueryParams(BaseModel):
    """Query parameters for property search."""

    market_id: Optional[str] = None
    min_bedrooms: Optional[int] = None
    max_bedrooms: Optional[int] = None
    min_revenue: Optional[float] = None
    max_revenue: Optional[float] = None
    min_occupancy: Optional[float] = None
    max_occupancy: Optional[float] = None
    min_rating: Optional[float] = None
    is_guest_favorite: Optional[bool] = None
    is_reliable_data: Optional[bool] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort_by: Optional[str] = None
    sort_order: Optional[str] = Field(default="desc", pattern="^(asc|desc)$")


class InvestmentScoreQueryParams(BaseModel):
    """Query parameters for investment score search."""

    market_id: Optional[str] = None
    min_total_score: Optional[float] = None
    max_total_score: Optional[float] = None
    opportunity_tier: Optional[str] = Field(
        None, pattern="^(PLATINUM|GOLD|SILVER|BRONZE)$"
    )
    is_top_opportunity: Optional[bool] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort_by: Optional[str] = None
    sort_order: Optional[str] = Field(default="desc", pattern="^(asc|desc)$")


# ============================================================================
# Health Check Models
# ============================================================================


class HealthCheckResponse(BaseModel):
    """Health check response model."""

    status: str
    database: str
    timestamp: datetime
    version: str


# ============================================================================
# Properties with Scores Models (Materialized View)
# ============================================================================


class PropertyWithScores(PropertyBasic):
    """Property with investment scores and performance metrics."""

    market_id: Optional[str] = None
    market_name: Optional[str] = None
    market_state: Optional[str] = None
    revenue: Optional[float] = None
    revenue_potential: Optional[float] = None
    adr: Optional[float] = None
    cleaning_fee: Optional[float] = None
    occupancy: Optional[float] = None
    available_nights: Optional[int] = None
    total_reviews: Optional[int] = None
    rating: Optional[float] = None
    property_reviews_count: Optional[int] = None
    high_season_reviews: Optional[int] = None
    high_season_label: Optional[str] = None
    revenue_score: Optional[float] = None
    occupancy_score: Optional[float] = None
    adr_score: Optional[float] = None
    review_score: Optional[float] = None
    amenity_score: Optional[float] = None
    host_score: Optional[float] = None
    seasonal_score: Optional[float] = None
    market_score: Optional[float] = None
    total_score: Optional[float] = None
    percentile_rank: Optional[float] = None
    is_top_opportunity: bool = False
    opportunity_tier: Optional[str] = None
    scoring_version: Optional[str] = "1.0"
    score_calculated_at: Optional[datetime] = None


class PropertyWithScoresListResponse(PaginatedResponse):
    """Response model for properties with scores list."""

    data: List[PropertyWithScores]


# ============================================================================
# Property Analysis Models
# ============================================================================


class MarketComparison(BaseModel):
    """Market comparison metrics."""

    property_count: Optional[int] = None
    avg_revenue: Optional[float] = None
    avg_occupancy: Optional[float] = None
    avg_adr: Optional[float] = None
    avg_rating: Optional[float] = None
    avg_total_score: Optional[float] = None
    median_revenue: Optional[float] = None
    median_occupancy: Optional[float] = None
    median_adr: Optional[float] = None
    median_rating: Optional[float] = None
    median_total_score: Optional[float] = None


class PerformanceVsMarket(BaseModel):
    """Performance compared to market averages."""

    revenue_vs_market_pct: Optional[float] = None
    occupancy_vs_market_pct: Optional[float] = None
    adr_vs_market_pct: Optional[float] = None
    rating_vs_market_pct: Optional[float] = None


class ComparableProperty(BaseModel):
    """Comparable property nearby."""

    id: str
    property_id: str
    title: Optional[str] = None
    bedrooms: Optional[float] = None
    bathrooms: Optional[float] = None
    distance_km: Optional[float] = None
    revenue: Optional[float] = None
    occupancy: Optional[float] = None
    adr: Optional[float] = None
    rating: Optional[float] = None
    total_score: Optional[float] = None
    opportunity_tier: Optional[str] = None


class PropertyAnalysis(PropertyWithScores):
    """Complete property analysis with market comparison."""

    host_is_super_host: Optional[bool] = None
    market_comparison: Optional[MarketComparison] = None
    performance_vs_market: Optional[PerformanceVsMarket] = None


class PropertyAnalysisResponse(BaseResponse):
    """Response model for property analysis."""

    data: PropertyAnalysis
    comparables: Optional[List[ComparableProperty]] = None


# ============================================================================
# Top Performers Models
# ============================================================================


class TopPerformer(PropertyWithScores):
    """Top performing property with ranking information."""

    market_state: Optional[str] = None
    total_reviews: Optional[int] = None
    is_guest_favorite: bool = False
    is_super_host: Optional[bool] = None
    rank_in_category: Optional[int] = None
    overall_rank: Optional[int] = None
    category_count: Optional[int] = None
    category_percentile: Optional[float] = None
    key_differentiator: Optional[str] = None


class TopPerformersGroup(BaseModel):
    """Group of top performers by market and bedroom category."""

    market_id: str
    market_name: str
    market_state: Optional[str] = None
    bedroom_count: Optional[float] = None
    properties: List[TopPerformer]
    count: int


class TopPerformersResponse(BaseResponse):
    """Response model for top performers."""

    data: List[TopPerformer]
    grouped_by_market: Optional[List[TopPerformersGroup]] = None
    total_count: int
