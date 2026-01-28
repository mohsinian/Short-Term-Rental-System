"""
Database service layer for API operations.

This module provides database query functions for the API, using psycopg2
for direct PostgreSQL connections.
"""

import logging
from typing import Optional, List, Dict, Any
from psycopg2.extras import RealDictCursor

from src.database.connection import get_db_connection, close_connection

logger = logging.getLogger(__name__)


# ============================================================================
# Database Context Manager
# ============================================================================


class DatabaseConnection:
    """Context manager for database connections."""

    def __init__(self):
        self.conn = None

    def __enter__(self):
        self.conn = get_db_connection()
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            close_connection(self.conn)


# ============================================================================
# Market Queries
# ============================================================================


def get_all_markets(
    limit: Optional[int] = None, offset: int = 0
) -> List[Dict[str, Any]]:
    """
    Get all markets from the database.

    Args:
        limit: Maximum number of markets to return
        offset: Number of markets to skip

    Returns:
        List of market dictionaries
    """
    with DatabaseConnection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = """
                SELECT id, name, state_name, created_at, updated_at
                FROM markets
                ORDER BY name ASC
            """
            if limit:
                query += f" LIMIT {limit} OFFSET {offset}"
            else:
                query += f" OFFSET {offset}"

            cur.execute(query)
            return cur.fetchall()


def get_market_by_id(market_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a market by its ID.

    Args:
        market_id: UUID of the market

    Returns:
        Market dictionary or None if not found
    """
    with DatabaseConnection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = """
                SELECT id, name, state_name, created_at, updated_at
                FROM markets
                WHERE id = %s
            """
            cur.execute(query, (market_id,))
            return cur.fetchone()


def get_market_count() -> int:
    """
    Get the total count of markets.

    Returns:
        Total number of markets
    """
    with DatabaseConnection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM markets")
            return cur.fetchone()[0]


# ============================================================================
# Property Queries
# ============================================================================


def get_properties(
    market_id: Optional[str] = None,
    min_bedrooms: Optional[int] = None,
    max_bedrooms: Optional[int] = None,
    min_revenue: Optional[float] = None,
    max_revenue: Optional[float] = None,
    min_occupancy: Optional[float] = None,
    max_occupancy: Optional[float] = None,
    min_rating: Optional[float] = None,
    is_guest_favorite: Optional[bool] = None,
    is_reliable_data: Optional[bool] = None,
    limit: int = 20,
    offset: int = 0,
    sort_by: Optional[str] = None,
    sort_order: str = "desc",
) -> List[Dict[str, Any]]:
    """
    Get properties with optional filters.

    Args:
        market_id: Filter by market ID
        min_bedrooms: Filter by minimum bedrooms
        max_bedrooms: Filter by maximum bedrooms
        min_revenue: Filter by minimum revenue
        max_revenue: Filter by maximum revenue
        min_occupancy: Filter by minimum occupancy
        max_occupancy: Filter by maximum occupancy
        min_rating: Filter by minimum rating
        is_guest_favorite: Filter by guest favorite status
        is_reliable_data: Filter by reliable data status
        limit: Maximum number of properties to return
        offset: Number of properties to skip
        sort_by: Field to sort by
        sort_order: Sort order ('asc' or 'desc')

    Returns:
        List of property dictionaries
    """
    with DatabaseConnection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Build base query
            query = """
                SELECT 
                    p.id, p.property_id, p.title, p.bedrooms, p.bathrooms,
                    p.accommodates, p.property_type, p.room_type, p.beds,
                    p.latitude, p.longitude, p.city_name, p.zipcode,
                    p.airbnb_listing_url, p.vrbo_listing_url,
                    p.is_guest_favorite, p.is_reliable_data,
                    p.created_at, p.updated_at
                FROM properties p
                WHERE 1=1
            """
            params = []

            # Add filters
            if market_id:
                query += " AND p.market_id = %s"
                params.append(market_id)

            if min_bedrooms is not None:
                query += " AND p.bedrooms >= %s"
                params.append(min_bedrooms)

            if max_bedrooms is not None:
                query += " AND p.bedrooms <= %s"
                params.append(max_bedrooms)

            if is_guest_favorite is not None:
                query += " AND p.is_guest_favorite = %s"
                params.append(is_guest_favorite)

            if is_reliable_data is not None:
                query += " AND p.is_reliable_data = %s"
                params.append(is_reliable_data)

            # Add sorting
            if sort_by:
                # Validate sort_by field
                valid_sort_fields = [
                    "title",
                    "bedrooms",
                    "bathrooms",
                    "accommodates",
                    "created_at",
                    "updated_at",
                ]
                if sort_by in valid_sort_fields:
                    query += f" ORDER BY p.{sort_by} {sort_order.upper()}"
                else:
                    query += " ORDER BY p.title ASC"
            else:
                query += " ORDER BY p.title ASC"

            # Add pagination
            query += " LIMIT %s OFFSET %s"
            params.append(limit)
            params.append(offset)

            cur.execute(query, params)
            return cur.fetchall()


def get_property_by_id(property_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a property by its ID with all related data.

    Args:
        property_id: UUID of the property

    Returns:
        Property dictionary with all related data or None if not found
    """
    with DatabaseConnection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Get property with market, host, performance, amenities, and reviews
            query = """
                SELECT 
                    p.id, p.property_id, p.title, p.bedrooms, p.bathrooms,
                    p.accommodates, p.property_type, p.room_type, p.beds,
                    p.latitude, p.longitude, p.city_name, p.zipcode,
                    p.airbnb_listing_url, p.vrbo_listing_url,
                    p.is_guest_favorite, p.is_reliable_data,
                    p.created_at, p.updated_at,
                    m.id as market_id, m.name as market_name, m.state_name as market_state,
                    h.is_super_host as host_is_super_host,
                    pp.revenue, pp.revenue_potential, pp.adr, pp.cleaning_fee,
                    pp.occupancy, pp.available_nights, pp.total_reviews,
                    pp.rating, pp.property_reviews_count, pp.high_season_reviews,
                    pp.high_season_label,
                    pa.amenities,
                    pr.total_months, pr.missing_months, pr.avg_reviews_per_month,
                    pr.review_pct_stayed_with_kids, pr.review_pct_group_trip,
                    pr.review_pct_stayed_with_a_pet
                FROM properties p
                LEFT JOIN markets m ON m.id = p.market_id
                LEFT JOIN hosts h ON h.id = p.host_id
                LEFT JOIN property_performance pp ON pp.property_id = p.id
                LEFT JOIN property_amenities pa ON pa.property_id = p.id
                LEFT JOIN property_reviews pr ON pr.property_id = p.id
                WHERE p.id = %s
            """
            cur.execute(query, (property_id,))
            return cur.fetchone()


def get_properties_count(
    market_id: Optional[str] = None,
    min_bedrooms: Optional[int] = None,
    max_bedrooms: Optional[int] = None,
    is_guest_favorite: Optional[bool] = None,
    is_reliable_data: Optional[bool] = None,
) -> int:
    """
    Get the total count of properties matching filters.

    Args:
        market_id: Filter by market ID
        min_bedrooms: Filter by minimum bedrooms
        max_bedrooms: Filter by maximum bedrooms
        is_guest_favorite: Filter by guest favorite status
        is_reliable_data: Filter by reliable data status

    Returns:
        Total number of matching properties
    """
    with DatabaseConnection() as conn:
        with conn.cursor() as cur:
            query = "SELECT COUNT(*) FROM properties p WHERE 1=1"
            params = []

            if market_id:
                query += " AND p.market_id = %s"
                params.append(market_id)

            if min_bedrooms is not None:
                query += " AND p.bedrooms >= %s"
                params.append(min_bedrooms)

            if max_bedrooms is not None:
                query += " AND p.bedrooms <= %s"
                params.append(max_bedrooms)

            if is_guest_favorite is not None:
                query += " AND p.is_guest_favorite = %s"
                params.append(is_guest_favorite)

            if is_reliable_data is not None:
                query += " AND p.is_reliable_data = %s"
                params.append(is_reliable_data)

            cur.execute(query, params)
            return cur.fetchone()[0]


# ============================================================================
# Investment Score Queries
# ============================================================================


def get_investment_scores(
    market_id: Optional[str] = None,
    min_total_score: Optional[float] = None,
    max_total_score: Optional[float] = None,
    opportunity_tier: Optional[str] = None,
    is_top_opportunity: Optional[bool] = None,
    limit: int = 20,
    offset: int = 0,
    sort_by: Optional[str] = None,
    sort_order: str = "desc",
) -> List[Dict[str, Any]]:
    """
    Get investment scores with optional filters.

    Args:
        market_id: Filter by market ID
        min_total_score: Filter by minimum total score
        max_total_score: Filter by maximum total score
        opportunity_tier: Filter by opportunity tier
        is_top_opportunity: Filter by top opportunity status
        limit: Maximum number of scores to return
        offset: Number of scores to skip
        sort_by: Field to sort by
        sort_order: Sort order ('asc' or 'desc')

    Returns:
        List of investment score dictionaries with property details
    """
    with DatabaseConnection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = """
                SELECT 
                    pis.id, pis.property_id,
                    pis.revenue_score, pis.occupancy_score, pis.adr_score,
                    pis.review_score, pis.amenity_score, pis.host_score,
                    pis.seasonal_score, pis.market_score,
                    pis.total_score, pis.percentile_rank,
                    pis.is_top_opportunity, pis.opportunity_tier,
                    pis.scoring_version, pis.calculated_at,
                    p.title as property_title, p.bedrooms as property_bedrooms,
                    m.name as market_name,
                    pp.revenue as property_revenue,
                    pp.occupancy as property_occupancy,
                    pp.adr as property_adr,
                    pp.rating as property_rating
                FROM property_investment_scores pis
                JOIN properties p ON p.id = pis.property_id
                JOIN markets m ON m.id = p.market_id
                LEFT JOIN property_performance pp ON pp.property_id = p.id
                WHERE 1=1
            """
            params = []

            if market_id:
                query += " AND p.market_id = %s"
                params.append(market_id)

            if min_total_score is not None:
                query += " AND pis.total_score >= %s"
                params.append(min_total_score)

            if max_total_score is not None:
                query += " AND pis.total_score <= %s"
                params.append(max_total_score)

            if opportunity_tier:
                query += " AND pis.opportunity_tier = %s"
                params.append(opportunity_tier)

            if is_top_opportunity is not None:
                query += " AND pis.is_top_opportunity = %s"
                params.append(is_top_opportunity)

            # Add sorting
            if sort_by:
                valid_sort_fields = [
                    "total_score",
                    "revenue_score",
                    "occupancy_score",
                    "percentile_rank",
                    "calculated_at",
                ]
                if sort_by in valid_sort_fields:
                    query += f" ORDER BY pis.{sort_by} {sort_order.upper()}"
                else:
                    query += " ORDER BY pis.total_score DESC"
            else:
                query += " ORDER BY pis.total_score DESC"

            query += " LIMIT %s OFFSET %s"
            params.append(limit)
            params.append(offset)

            cur.execute(query, params)
            return cur.fetchall()


def get_top_opportunities(limit: int = 20) -> List[Dict[str, Any]]:
    """
    Get top investment opportunities using the database function.

    Args:
        limit: Maximum number of opportunities to return

    Returns:
        List of top opportunity dictionaries
    """
    with DatabaseConnection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = "SELECT * FROM get_top_opportunities(%s)"
            cur.execute(query, (limit,))
            return cur.fetchall()


def get_undervalued_opportunities(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get undervalued investment opportunities using the database function.

    Args:
        limit: Maximum number of opportunities to return

    Returns:
        List of undervalued opportunity dictionaries
    """
    with DatabaseConnection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = "SELECT * FROM get_undervalued_opportunities(%s)"
            cur.execute(query, (limit,))
            return cur.fetchall()


def get_investment_scores_count(
    market_id: Optional[str] = None,
    min_total_score: Optional[float] = None,
    max_total_score: Optional[float] = None,
    opportunity_tier: Optional[str] = None,
    is_top_opportunity: Optional[bool] = None,
) -> int:
    """
    Get the total count of investment scores matching filters.

    Args:
        market_id: Filter by market ID
        min_total_score: Filter by minimum total score
        max_total_score: Filter by maximum total score
        opportunity_tier: Filter by opportunity tier
        is_top_opportunity: Filter by top opportunity status

    Returns:
        Total number of matching investment scores
    """
    with DatabaseConnection() as conn:
        with conn.cursor() as cur:
            query = """
                SELECT COUNT(*)
                FROM property_investment_scores pis
                JOIN properties p ON p.id = pis.property_id
                WHERE 1=1
            """
            params = []

            if market_id:
                query += " AND p.market_id = %s"
                params.append(market_id)

            if min_total_score is not None:
                query += " AND pis.total_score >= %s"
                params.append(min_total_score)

            if max_total_score is not None:
                query += " AND pis.total_score <= %s"
                params.append(max_total_score)

            if opportunity_tier:
                query += " AND pis.opportunity_tier = %s"
                params.append(opportunity_tier)

            if is_top_opportunity is not None:
                query += " AND pis.is_top_opportunity = %s"
                params.append(is_top_opportunity)

            cur.execute(query, params)
            return cur.fetchone()[0]


# ============================================================================
# Health Check
# ============================================================================


def check_database_connection() -> bool:
    """
    Check if the database connection is working.

    Returns:
        True if connection is successful, False otherwise
    """
    try:
        with DatabaseConnection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
                return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


# ============================================================================
# Materialized View Queries - Properties with Scores
# ============================================================================


def get_properties_with_scores(
    market_id: Optional[str] = None,
    bedrooms: Optional[float] = None,
    min_revenue: Optional[float] = None,
    min_total_score: Optional[float] = None,
    opportunity_tier: Optional[str] = None,
    is_top_opportunity: Optional[bool] = None,
    limit: int = 20,
    offset: int = 0,
    sort_by: Optional[str] = None,
    sort_order: str = "desc",
) -> List[Dict[str, Any]]:
    """
    Get properties with investment scores from materialized view.

    Args:
        market_id: Filter by market ID
        bedrooms: Filter by bedroom count
        min_revenue: Filter by minimum revenue
        min_total_score: Filter by minimum total score
        opportunity_tier: Filter by opportunity tier
        is_top_opportunity: Filter by top opportunity status
        limit: Maximum number of properties to return
        offset: Number of properties to skip
        sort_by: Field to sort by
        sort_order: Sort order ('asc' or 'desc')

    Returns:
        List of property dictionaries with scores
    """
    with DatabaseConnection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = """
                SELECT 
                    id, property_id, title, bedrooms, bathrooms, accommodates,
                    property_type, room_type, beds, latitude, longitude,
                    city_name, zipcode, airbnb_listing_url, vrbo_listing_url,
                    is_guest_favorite, is_reliable_data, market_id, market_name,
                    market_state, revenue, revenue_potential, adr, cleaning_fee,
                    occupancy, available_nights, total_reviews, rating,
                    property_reviews_count, high_season_reviews, high_season_label,
                    revenue_score, occupancy_score, adr_score, review_score,
                    amenity_score, host_score, seasonal_score, market_score,
                    total_score, percentile_rank, is_top_opportunity,
                    opportunity_tier, scoring_version, score_calculated_at,
                    created_at, updated_at
                FROM mv_properties_with_scores
                WHERE 1=1
            """
            params = []

            if market_id:
                query += " AND market_id = %s"
                params.append(market_id)

            if bedrooms is not None:
                query += " AND bedrooms = %s"
                params.append(bedrooms)

            if min_revenue is not None:
                query += " AND revenue >= %s"
                params.append(min_revenue)

            if min_total_score is not None:
                query += " AND total_score >= %s"
                params.append(min_total_score)

            if opportunity_tier:
                query += " AND opportunity_tier = %s"
                params.append(opportunity_tier)

            if is_top_opportunity is not None:
                query += " AND is_top_opportunity = %s"
                params.append(is_top_opportunity)

            # Add sorting
            if sort_by:
                valid_sort_fields = [
                    "title",
                    "bedrooms",
                    "revenue",
                    "occupancy",
                    "adr",
                    "rating",
                    "total_score",
                    "revenue_score",
                    "occupancy_score",
                    "percentile_rank",
                    "opportunity_tier",
                    "created_at",
                ]
                if sort_by in valid_sort_fields:
                    query += f" ORDER BY {sort_by} {sort_order.upper()}"
                else:
                    query += " ORDER BY total_score DESC"
            else:
                query += " ORDER BY total_score DESC"

            query += " LIMIT %s"
            params.append(limit)

            query += " OFFSET %s"
            params.append(offset)

            cur.execute(query, params)
            return cur.fetchall()


def get_properties_with_scores_count(
    market_id: Optional[str] = None,
    bedrooms: Optional[float] = None,
    min_revenue: Optional[float] = None,
    min_total_score: Optional[float] = None,
    opportunity_tier: Optional[str] = None,
    is_top_opportunity: Optional[bool] = None,
) -> int:
    """
    Get the total count of properties with scores matching filters.

    Args:
        market_id: Filter by market ID
        bedrooms: Filter by bedroom count
        min_revenue: Filter by minimum revenue
        min_total_score: Filter by minimum total score
        opportunity_tier: Filter by opportunity tier
        is_top_opportunity: Filter by top opportunity status

    Returns:
        Total number of matching properties
    """
    with DatabaseConnection() as conn:
        with conn.cursor() as cur:
            query = "SELECT COUNT(*) FROM mv_properties_with_scores WHERE 1=1"
            params = []

            if market_id:
                query += " AND market_id = %s"
                params.append(market_id)

            if bedrooms is not None:
                query += " AND bedrooms = %s"
                params.append(bedrooms)

            if min_revenue is not None:
                query += " AND revenue >= %s"
                params.append(min_revenue)

            if min_total_score is not None:
                query += " AND total_score >= %s"
                params.append(min_total_score)

            if opportunity_tier:
                query += " AND opportunity_tier = %s"
                params.append(opportunity_tier)

            if is_top_opportunity is not None:
                query += " AND is_top_opportunity = %s"
                params.append(is_top_opportunity)

            cur.execute(query, params)
            return cur.fetchone()[0]


# ============================================================================
# Materialized View Queries - Property Analysis
# ============================================================================


def get_property_analysis(property_id: str) -> Optional[Dict[str, Any]]:
    """
    Get property analysis with market comparison from materialized view.

    Args:
        property_id: UUID of the property

    Returns:
        Property analysis dictionary or None if not found
    """
    with DatabaseConnection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = """
                SELECT 
                    id, property_id, title, bedrooms, bathrooms, accommodates,
                    property_type, room_type, beds, latitude, longitude,
                    city_name, zipcode, airbnb_listing_url, vrbo_listing_url,
                    is_guest_favorite, is_reliable_data, market_id, market_name,
                    market_state, revenue, revenue_potential, adr, cleaning_fee,
                    occupancy, available_nights, total_reviews, rating,
                    property_reviews_count, high_season_reviews, high_season_label,
                    revenue_score, occupancy_score, adr_score, review_score,
                    amenity_score, host_score, seasonal_score, market_score,
                    total_score, percentile_rank, is_top_opportunity,
                    opportunity_tier, scoring_version, score_calculated_at,
                    host_is_super_host,
                    market_property_count, market_avg_revenue, market_avg_occupancy,
                    market_avg_adr, market_avg_rating, market_avg_total_score,
                    market_median_revenue, market_median_occupancy, market_median_adr,
                    market_median_rating, market_median_total_score,
                    revenue_vs_market_pct, occupancy_vs_market_pct,
                    adr_vs_market_pct, rating_vs_market_pct,
                    created_at, updated_at
                FROM mv_property_analysis
                WHERE id = %s
            """
            cur.execute(query, (property_id,))
            return cur.fetchone()


def get_comparable_properties(
    property_id: str,
    market_id: str,
    bedrooms: float,
    latitude: float,
    longitude: float,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """
    Get comparable properties nearby (same market and bedroom count).

    Args:
        property_id: UUID of the property to exclude
        market_id: UUID of the market
        bedrooms: Bedroom count to match
        latitude: Latitude for distance calculation
        longitude: Longitude for distance calculation
        limit: Maximum number of comparables to return

    Returns:
        List of comparable property dictionaries
    """
    with DatabaseConnection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Use Haversine formula for distance calculation
            query = """
                SELECT 
                    id, property_id, title, bedrooms, bathrooms,
                    revenue, occupancy, adr, rating, total_score,
                    opportunity_tier,
                    111.0 * DEGREES(ACOS(LEAST(1.0, 
                        COS(RADIANS(%s)) * COS(RADIANS(latitude)) * 
                        COS(RADIANS(longitude - %s)) + 
                        SIN(RADIANS(%s)) * SIN(RADIANS(latitude))
                    ))) AS distance_km
                FROM mv_properties_with_scores
                WHERE market_id = %s
                  AND bedrooms = %s
                  AND id != %s
                  AND revenue IS NOT NULL
                ORDER BY distance_km ASC
                LIMIT %s
            """
            cur.execute(
                query,
                (
                    latitude,
                    longitude,
                    latitude,
                    market_id,
                    bedrooms,
                    property_id,
                    limit,
                ),
            )
            return cur.fetchall()


# ============================================================================
# Materialized View Queries - Top Performers
# ============================================================================


def get_top_performers(limit: int = 20) -> List[Dict[str, Any]]:
    """
    Get top investment opportunities from materialized view.

    Args:
        limit: Maximum number of performers to return

    Returns:
        List of top performer dictionaries
    """
    with DatabaseConnection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = """
                SELECT 
                    id, property_id, title, bedrooms, bathrooms, accommodates,
                    property_type, room_type, latitude, longitude, city_name,
                    zipcode, airbnb_listing_url, market_id, market_name,
                    market_state, revenue, occupancy, adr, rating, total_reviews,
                    revenue_score, occupancy_score, adr_score, review_score,
                    amenity_score, host_score, seasonal_score, market_score,
                    total_score, percentile_rank, opportunity_tier,
                    is_top_opportunity, is_guest_favorite, is_super_host,
                    rank_in_category, overall_rank, category_count,
                    category_percentile, key_differentiator
                FROM mv_top_performers
                ORDER BY overall_rank ASC
                LIMIT %s
            """
            cur.execute(query, (limit,))
            return cur.fetchall()


def get_top_performers_by_market(market_id: str) -> List[Dict[str, Any]]:
    """
    Get top performers for a specific market.

    Args:
        market_id: UUID of the market

    Returns:
        List of top performer dictionaries for the market
    """
    with DatabaseConnection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = """
                SELECT 
                    id, property_id, title, bedrooms, bathrooms, accommodates,
                    property_type, room_type, latitude, longitude, city_name,
                    zipcode, airbnb_listing_url, market_id, market_name,
                    market_state, revenue, occupancy, adr, rating, total_reviews,
                    revenue_score, occupancy_score, adr_score, review_score,
                    amenity_score, host_score, seasonal_score, market_score,
                    total_score, percentile_rank, opportunity_tier,
                    is_top_opportunity, is_guest_favorite, is_super_host,
                    rank_in_category, overall_rank, category_count,
                    category_percentile, key_differentiator
                FROM mv_top_performers
                WHERE market_id = %s
                ORDER BY overall_rank ASC
            """
            cur.execute(query, (market_id,))
            return cur.fetchall()


def get_top_performers_grouped() -> List[Dict[str, Any]]:
    """
    Get top performers grouped by market and bedroom category.

    Returns:
        List of grouped dictionaries with market, bedroom, and properties
    """
    with DatabaseConnection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = """
                SELECT 
                    market_id,
                    market_name,
                    market_state,
                    bedrooms as bedroom_count,
                    json_agg(
                        json_build_object(
                            'id', id,
                            'property_id', property_id,
                            'title', title,
                            'bedrooms', bedrooms,
                            'bathrooms', bathrooms,
                            'revenue', revenue,
                            'occupancy', occupancy,
                            'adr', adr,
                            'rating', rating,
                            'total_score', total_score,
                            'opportunity_tier', opportunity_tier,
                            'rank_in_category', rank_in_category,
                            'overall_rank', overall_rank,
                            'category_percentile', category_percentile,
                            'key_differentiator', key_differentiator
                        ) ORDER BY overall_rank ASC
                    ) as properties
                FROM mv_top_performers
                GROUP BY market_id, market_name, market_state, bedrooms
                ORDER BY market_name ASC, bedrooms ASC
            """
            cur.execute(query)
            return cur.fetchall()


# ============================================================================
# Materialized View Refresh Functions
# ============================================================================


def refresh_materialized_view(view_name: str) -> bool:
    """
    Refresh a specific materialized view.

    Args:
        view_name: Name of the materialized view to refresh

    Returns:
        True if successful, False otherwise
    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Try concurrent refresh first, fall back to regular refresh if it fails
            try:
                logger.info(f"Attempting concurrent refresh for {view_name}")
                cur.execute(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view_name}")
                conn.commit()
                logger.info(
                    f"Successfully refreshed materialized view concurrently: {view_name}"
                )
            except Exception as e:
                # Rollback the failed transaction
                conn.rollback()
                logger.warning(
                    f"Concurrent refresh failed for {view_name}, trying regular refresh: {e}"
                )
                cur.execute(f"REFRESH MATERIALIZED VIEW {view_name}")
                conn.commit()
                logger.info(
                    f"Successfully refreshed materialized view (non-concurrent): {view_name}"
                )
            return True
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Failed to refresh materialized view {view_name}: {e}")
        return False
    finally:
        if conn:
            close_connection(conn)


def refresh_all_materialized_views() -> bool:
    """
    Refresh all materialized views.

    Returns:
        True if successful, False otherwise
    """
    views = ["mv_properties_with_scores", "mv_property_analysis", "mv_top_performers"]

    all_successful = True
    for view in views:
        logger.info(f"Refreshing materialized view: {view}")
        if not refresh_materialized_view(view):
            all_successful = False
            logger.error(f"Failed to refresh view: {view}")

    if all_successful:
        logger.info("Successfully refreshed all materialized views")
    else:
        logger.error("Some materialized views failed to refresh")

    return all_successful
