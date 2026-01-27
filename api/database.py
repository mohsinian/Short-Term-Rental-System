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

def get_all_markets(limit: Optional[int] = None, offset: int = 0) -> List[Dict[str, Any]]:
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
    sort_order: str = "desc"
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
            param_count = 0
            
            # Add filters
            if market_id:
                param_count += 1
                query += f" AND p.market_id = ${param_count}"
                params.append(market_id)
            
            if min_bedrooms is not None:
                param_count += 1
                query += f" AND p.bedrooms >= ${param_count}"
                params.append(min_bedrooms)
            
            if max_bedrooms is not None:
                param_count += 1
                query += f" AND p.bedrooms <= ${param_count}"
                params.append(max_bedrooms)
            
            if is_guest_favorite is not None:
                param_count += 1
                query += f" AND p.is_guest_favorite = ${param_count}"
                params.append(is_guest_favorite)
            
            if is_reliable_data is not None:
                param_count += 1
                query += f" AND p.is_reliable_data = ${param_count}"
                params.append(is_reliable_data)
            
            # Add sorting
            if sort_by:
                # Validate sort_by field
                valid_sort_fields = [
                    'title', 'bedrooms', 'bathrooms', 'accommodates',
                    'created_at', 'updated_at'
                ]
                if sort_by in valid_sort_fields:
                    query += f" ORDER BY p.{sort_by} {sort_order.upper()}"
                else:
                    query += " ORDER BY p.title ASC"
            else:
                query += " ORDER BY p.title ASC"
            
            # Add pagination
            param_count += 1
            query += f" LIMIT ${param_count}"
            params.append(limit)
            
            param_count += 1
            query += f" OFFSET ${param_count}"
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
            param_count = 0
            
            if market_id:
                param_count += 1
                query += f" AND p.market_id = ${param_count}"
                params.append(market_id)
            
            if min_bedrooms is not None:
                param_count += 1
                query += f" AND p.bedrooms >= ${param_count}"
                params.append(min_bedrooms)
            
            if max_bedrooms is not None:
                param_count += 1
                query += f" AND p.bedrooms <= ${param_count}"
                params.append(max_bedrooms)
            
            if is_guest_favorite is not None:
                param_count += 1
                query += f" AND p.is_guest_favorite = ${param_count}"
                params.append(is_guest_favorite)
            
            if is_reliable_data is not None:
                param_count += 1
                query += f" AND p.is_reliable_data = ${param_count}"
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
    sort_order: str = "desc"
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
            param_count = 0
            
            if market_id:
                param_count += 1
                query += f" AND p.market_id = ${param_count}"
                params.append(market_id)
            
            if min_total_score is not None:
                param_count += 1
                query += f" AND pis.total_score >= ${param_count}"
                params.append(min_total_score)
            
            if max_total_score is not None:
                param_count += 1
                query += f" AND pis.total_score <= ${param_count}"
                params.append(max_total_score)
            
            if opportunity_tier:
                param_count += 1
                query += f" AND pis.opportunity_tier = ${param_count}"
                params.append(opportunity_tier)
            
            if is_top_opportunity is not None:
                param_count += 1
                query += f" AND pis.is_top_opportunity = ${param_count}"
                params.append(is_top_opportunity)
            
            # Add sorting
            if sort_by:
                valid_sort_fields = [
                    'total_score', 'revenue_score', 'occupancy_score',
                    'percentile_rank', 'calculated_at'
                ]
                if sort_by in valid_sort_fields:
                    query += f" ORDER BY pis.{sort_by} {sort_order.upper()}"
                else:
                    query += " ORDER BY pis.total_score DESC"
            else:
                query += " ORDER BY pis.total_score DESC"
            
            param_count += 1
            query += f" LIMIT ${param_count}"
            params.append(limit)
            
            param_count += 1
            query += f" OFFSET ${param_count}"
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
            param_count = 0
            
            if market_id:
                param_count += 1
                query += f" AND p.market_id = ${param_count}"
                params.append(market_id)
            
            if min_total_score is not None:
                param_count += 1
                query += f" AND pis.total_score >= ${param_count}"
                params.append(min_total_score)
            
            if max_total_score is not None:
                param_count += 1
                query += f" AND pis.total_score <= ${param_count}"
                params.append(max_total_score)
            
            if opportunity_tier:
                param_count += 1
                query += f" AND pis.opportunity_tier = ${param_count}"
                params.append(opportunity_tier)
            
            if is_top_opportunity is not None:
                param_count += 1
                query += f" AND pis.is_top_opportunity = ${param_count}"
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
