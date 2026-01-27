"""
Investment Scoring System for STR Properties
============================================

Scoring Components (weighted to sum to 100%):
1. Revenue Performance (25%) - Revenue vs market average for same bedroom count
2. Occupancy Consistency (15%) - How well the property maintains bookings
3. ADR Positioning (15%) - Average Daily Rate optimization
4. Review Score (15%) - Review volume and ratings combined
5. Amenity Value (10%) - High-value amenities that correlate with revenue
6. Host Status (5%) - Superhost and guest favorite indicators
7. Seasonal Stability (10%) - Consistency across seasons (low missing months)
8. Market Strength (5%) - Overall market performance indicators
"""

import logging
from dataclasses import dataclass
from typing import Optional, List, Dict

import numpy as np
from dotenv import load_dotenv
from supabase import Client

from src.database.supabase_client import get_supabase_client


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================


@dataclass
class ScoringWeights:
    """Configurable weights for each scoring component"""

    revenue: float = 0.25
    occupancy: float = 0.15
    adr: float = 0.15
    review: float = 0.15
    amenity: float = 0.10
    host: float = 0.05
    seasonal: float = 0.10
    market: float = 0.05

    def __post_init__(self):
        total = (
            self.revenue
            + self.occupancy
            + self.adr
            + self.review
            + self.amenity
            + self.host
            + self.seasonal
            + self.market
        )
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"Weights must sum to 1.0, got {total}")


# High-value amenities based on revenue correlation research
HIGH_VALUE_AMENITIES = {
    "tier_1": {  # Highest revenue impact
        "amenities": ["pool", "hot tub", "hot_tub", "jacuzzi", "sauna"],
        "weight": 20,
    },
    "tier_2": {  # Strong revenue impact
        "amenities": ["game room", "arcade", "pool table", "theater", "movie"],
        "weight": 15,
    },
    "tier_3": {  # Moderate revenue impact
        "amenities": ["fire pit", "firepit", "grill", "bbq", "ev charger"],
        "weight": 10,
    },
    "tier_4": {  # Standard premium amenities
        "amenities": ["gym", "exercise", "view", "waterfront", "beach"],
        "weight": 8,
    },
    "tier_5": {  # Family-friendly amenities
        "amenities": ["crib", "pack n play", "high chair", "playground"],
        "weight": 5,
    },
}


# =============================================================================
# SCORING FUNCTIONS
# =============================================================================


def calculate_revenue_score(
    property_revenue: Optional[float],
    market_avg_revenue: Optional[float],
    market_max_revenue: Optional[float],
) -> float:
    """
    Score based on revenue performance vs market average.

    Scoring Logic:
    - At market average = 50 points
    - Top performer (2x average or max) = 100 points
    - Below average scaled down from 50
    """
    if property_revenue is None or market_avg_revenue is None:
        return 0.0

    if market_avg_revenue <= 0:
        return 50.0  # Default if no market data

    ratio = property_revenue / market_avg_revenue

    if ratio >= 2.0:
        return 100.0
    elif ratio >= 1.0:
        # Linear scale from 50 (at average) to 100 (at 2x average)
        return 50.0 + (ratio - 1.0) * 50.0
    else:
        # Linear scale from 0 (at 0) to 50 (at average)
        return ratio * 50.0


def calculate_occupancy_score(occupancy: Optional[float]) -> float:
    """
    Score based on occupancy rate.

    Scoring Logic:
    - 80%+ occupancy = 100 points (exceptional)
    - 70%+ = 90 points (excellent)
    - 60%+ = 75 points (good)
    - 50%+ = 60 points (average)
    - Below 50% scaled down
    """
    if occupancy is None:
        return 0.0

    # Handle both 0-1 and 0-100 formats
    if occupancy > 1:
        occupancy = occupancy / 100.0

    if occupancy >= 0.80:
        return 100.0
    elif occupancy >= 0.70:
        return 90.0 + (occupancy - 0.70) * 100.0  # 90-100
    elif occupancy >= 0.60:
        return 75.0 + (occupancy - 0.60) * 150.0  # 75-90
    elif occupancy >= 0.50:
        return 60.0 + (occupancy - 0.50) * 150.0  # 60-75
    else:
        return occupancy * 120.0  # 0-60


def calculate_adr_score(
    property_adr: Optional[float],
    market_avg_adr: Optional[float],
    property_occupancy: Optional[float],
) -> float:
    """
    Score ADR positioning - balance between rate and occupancy.

    High ADR with good occupancy = optimal pricing
    High ADR with low occupancy = potentially overpriced
    Low ADR with high occupancy = potential upside opportunity
    """
    if property_adr is None or market_avg_adr is None:
        return 0.0

    if market_avg_adr <= 0:
        return 50.0

    adr_ratio = property_adr / market_avg_adr

    # Base score from ADR ratio
    if adr_ratio >= 1.5:
        base_score = 100.0
    elif adr_ratio >= 1.0:
        base_score = 70.0 + (adr_ratio - 1.0) * 60.0  # 70-100
    else:
        base_score = adr_ratio * 70.0  # 0-70

    # Adjust based on occupancy (reward high ADR + high occupancy)
    if property_occupancy is not None:
        occ = (
            property_occupancy
            if property_occupancy <= 1
            else property_occupancy / 100.0
        )
        if adr_ratio >= 1.0 and occ >= 0.60:
            # Bonus for maintaining high rates with good occupancy
            base_score = min(100.0, base_score * (1 + (occ - 0.60) * 0.25))
        elif adr_ratio < 0.8 and occ >= 0.70:
            # Opportunity flag: underpriced but high demand
            base_score = min(100.0, base_score * 1.15)

    return base_score


def calculate_review_score(
    total_reviews: Optional[int],
    rating: Optional[float],
    avg_reviews_per_month: Optional[float],
) -> float:
    """
    Combined score for review volume and quality.

    Components:
    - Rating quality (60% weight)
    - Review velocity (40% weight)
    """
    score = 0.0

    # Rating component (60%)
    if rating is not None:
        if rating >= 4.9:
            rating_score = 100.0
        elif rating >= 4.7:
            rating_score = 90.0
        elif rating >= 4.5:
            rating_score = 75.0
        elif rating >= 4.0:
            rating_score = 50.0
        else:
            rating_score = rating * 12.5  # 0-50 for ratings below 4.0
        score += rating_score * 0.6

    # Review velocity component (40%)
    if avg_reviews_per_month is not None:
        if avg_reviews_per_month >= 10:
            velocity_score = 100.0
        elif avg_reviews_per_month >= 5:
            velocity_score = 80.0 + (avg_reviews_per_month - 5) * 4.0
        elif avg_reviews_per_month >= 2:
            velocity_score = 50.0 + (avg_reviews_per_month - 2) * 10.0
        else:
            velocity_score = avg_reviews_per_month * 25.0
        score += velocity_score * 0.4
    elif total_reviews is not None:
        # Fallback to total reviews if no velocity
        if total_reviews >= 100:
            velocity_score = 100.0
        elif total_reviews >= 50:
            velocity_score = 70.0 + (total_reviews - 50) * 0.6
        elif total_reviews >= 20:
            velocity_score = 40.0 + (total_reviews - 20) * 1.0
        else:
            velocity_score = total_reviews * 2.0
        score += velocity_score * 0.4

    return score


def calculate_amenity_score(amenities_text: Optional[str]) -> float:
    """
    Score based on high-value amenities that correlate with revenue.

    Uses tiered system where premium amenities contribute more.
    """
    if not amenities_text:
        return 30.0  # Base score for having a listing

    amenities_lower = str(amenities_text).lower()
    total_points = 0
    max_possible = sum(tier["weight"] for tier in HIGH_VALUE_AMENITIES.values())

    for tier_name, tier_data in HIGH_VALUE_AMENITIES.items():
        for amenity in tier_data["amenities"]:
            if amenity in amenities_lower:
                total_points += tier_data["weight"]
                break  # Only count once per tier

    # Scale to 0-100
    # Properties with 50%+ of premium amenities get near-perfect scores
    score = min(100.0, (total_points / max_possible) * 150.0 + 30.0)

    return score


def calculate_host_score(
    is_superhost: Optional[bool], is_guest_favorite: Optional[bool]
) -> float:
    """
    Score based on host status indicators.

    - Superhost: +50 points
    - Guest Favorite: +50 points
    - Neither: 30 points (base)
    """
    score = 30.0  # Base score

    if is_superhost:
        score += 35.0

    if is_guest_favorite:
        score += 35.0

    return min(100.0, score)


def calculate_seasonal_score(
    total_months: Optional[int],
    missing_months: Optional[int],
    high_season_reviews: Optional[int],
    total_reviews: Optional[int],
) -> float:
    """
    Score based on seasonal stability and consistency.

    Properties with consistent bookings across seasons are more reliable investments.
    """
    score = 50.0  # Base score

    # Consistency component (50% of score)
    if total_months is not None and missing_months is not None and total_months > 0:
        active_ratio = (total_months - missing_months) / total_months
        consistency_score = active_ratio * 100.0
        score = consistency_score * 0.5

    # Seasonal distribution component (50% of score)
    if (
        high_season_reviews is not None
        and total_reviews is not None
        and total_reviews > 0
    ):
        # Ideal: high season accounts for 25-40% of reviews (roughly proportional)
        high_season_ratio = high_season_reviews / total_reviews
        if 0.20 <= high_season_ratio <= 0.45:
            # Well-distributed across seasons
            distribution_score = 100.0
        elif high_season_ratio > 0.45:
            # Too dependent on high season
            distribution_score = 100.0 - (high_season_ratio - 0.45) * 150.0
        else:
            # Underperforming in high season
            distribution_score = high_season_ratio * 500.0
        score += max(0.0, distribution_score) * 0.5
    else:
        score += 25.0  # Default if no seasonal data

    return min(100.0, max(0.0, score))


def calculate_market_score(
    market_avg_occupancy: Optional[float],
    market_avg_revenue: Optional[float],
    property_count_in_category: Optional[int],
) -> float:
    """
    Score the overall market strength.

    Strong markets have:
    - High average occupancy (demand indicator)
    - High average revenue (pricing power)
    - Sufficient inventory (established market)
    """
    score = 0.0
    components = 0

    # Market occupancy health (40%)
    if market_avg_occupancy is not None:
        occ = (
            market_avg_occupancy
            if market_avg_occupancy <= 1
            else market_avg_occupancy / 100.0
        )
        if occ >= 0.70:
            occ_score = 100.0
        elif occ >= 0.60:
            occ_score = 80.0
        elif occ >= 0.50:
            occ_score = 60.0
        else:
            occ_score = occ * 120.0
        score += occ_score * 0.4
        components += 0.4

    # Market revenue health (40%)
    if market_avg_revenue is not None:
        # Normalize based on observed ranges (adjust based on your data)
        if market_avg_revenue >= 100000:
            rev_score = 100.0
        elif market_avg_revenue >= 75000:
            rev_score = 85.0
        elif market_avg_revenue >= 50000:
            rev_score = 70.0
        elif market_avg_revenue >= 25000:
            rev_score = 50.0
        else:
            rev_score = (market_avg_revenue / 25000) * 50.0
        score += rev_score * 0.4
        components += 0.4

    # Market maturity (20%)
    if property_count_in_category is not None:
        if property_count_in_category >= 50:
            maturity_score = 100.0
        elif property_count_in_category >= 20:
            maturity_score = 70.0
        elif property_count_in_category >= 10:
            maturity_score = 50.0
        else:
            maturity_score = property_count_in_category * 5.0
        score += maturity_score * 0.2
        components += 0.2

    # Normalize if not all components available
    if components > 0 and components < 1.0:
        score = score / components

    return score


# =============================================================================
# COMPOSITE SCORING & TIER ASSIGNMENT
# =============================================================================


@dataclass
class PropertyScore:
    """Complete scoring result for a property"""

    property_id: str
    revenue_score: float
    occupancy_score: float
    adr_score: float
    review_score: float
    amenity_score: float
    host_score: float
    seasonal_score: float
    market_score: float
    total_score: float
    percentile_rank: Optional[float] = None
    is_top_opportunity: bool = False
    opportunity_tier: str = "BRONZE"


def calculate_total_score(
    revenue_score: float,
    occupancy_score: float,
    adr_score: float,
    review_score: float,
    amenity_score: float,
    host_score: float,
    seasonal_score: float,
    market_score: float,
    weights: Optional[ScoringWeights] = None,
) -> float:
    """Calculate weighted composite score"""
    if weights is None:
        weights = ScoringWeights()

    total = (
        revenue_score * weights.revenue
        + occupancy_score * weights.occupancy
        + adr_score * weights.adr
        + review_score * weights.review
        + amenity_score * weights.amenity
        + host_score * weights.host
        + seasonal_score * weights.seasonal
        + market_score * weights.market
    )

    return round(total, 2)


def assign_opportunity_tier(
    total_score: float, percentile: Optional[float] = None
) -> str:
    """
    Assign investment opportunity tier based on score and percentile.

    Tiers:
    - PLATINUM: Top 5% or score >= 85
    - GOLD: Top 15% or score >= 75
    - SILVER: Top 35% or score >= 60
    - BRONZE: Everything else
    """
    if percentile is not None:
        if percentile >= 95 or total_score >= 85:
            return "PLATINUM"
        elif percentile >= 85 or total_score >= 75:
            return "GOLD"
        elif percentile >= 65 or total_score >= 60:
            return "SILVER"
    else:
        if total_score >= 85:
            return "PLATINUM"
        elif total_score >= 75:
            return "GOLD"
        elif total_score >= 60:
            return "SILVER"

    return "BRONZE"


# =============================================================================
# MAIN SCORING PIPELINE
# =============================================================================


class InvestmentScorer:
    """Main class for calculating investment scores using Supabase"""

    def __init__(
        self, weights: Optional[ScoringWeights] = None, limit: Optional[int] = None
    ):
        load_dotenv()
        self.client: Optional[Client] = None
        self.weights = weights or ScoringWeights()
        self.scoring_version = "1.0"
        self.limit = limit

    def connect(self) -> None:
        """Establish Supabase client connection."""
        try:
            # Configure client to reduce verbose logging
            import logging

            supabase_logger = logging.getLogger("httpx")
            supabase_logger.setLevel(logging.WARNING)  # Reduce HTTP request logging

            self.client = get_supabase_client()
            logger.info("Supabase client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            raise

    def disconnect(self) -> None:
        """Close Supabase client connection (no-op for supabase-py)."""
        logger.info("Supabase client session ended")

    def fetch_property_data(self) -> List[Dict]:
        """
        Fetch all required data for scoring using Supabase client with optimized batch queries.

        Returns:
            List of property dictionaries with all required data.
        """
        logger.info("Fetching property data from database...")

        try:
            # First, fetch market statistics (single request)
            market_stats_response = self.client.rpc(
                "get_market_stats",
                {},  # No parameters needed
            ).execute()

            # Build market stats lookup dictionary
            market_stats = {}
            if market_stats_response.data:
                for stat in market_stats_response.data:
                    key = (stat["market_id"], stat["bedrooms"])
                    market_stats[key] = stat
            else:
                logger.warning("No market stats returned from get_market_stats()")

            # Fetch all properties with their related data in a single batch query
            # Note: Supabase has a default limit of 1000 rows per RPC call
            # We need to use the Supabase client's count and limit features

            logger.info("Fetching all properties from RPC function...")

            # Supabase RPC calls have a default limit, we need to paginate
            # Fetch in batches to handle more than 1000 properties
            all_properties_data = []
            batch_size = 1000
            offset = 0

            while True:
                # Note: Supabase RPC doesn't support limit/offset in params
                # So we use the PostgREST range headers
                response = (
                    self.client.rpc("get_properties_for_scoring", {})
                    .range(offset, offset + batch_size - 1)
                    .execute()
                )

                if not response.data:
                    break

                all_properties_data.extend(response.data)
                logger.info(
                    f"Fetched {len(response.data)} properties (total: {len(all_properties_data)})"
                )

                # If we got less than batch_size, we're done
                if len(response.data) < batch_size:
                    break

                offset += batch_size

            properties_data = all_properties_data

            # Fallback to batched table queries if RPC didn't return data
            if not all_properties_data:
                logger.info("Using batched table queries as fallback...")
                properties_data = self._fetch_properties_batched(market_stats)
            else:
                properties_data = all_properties_data

            # Process and enrich data
            properties = []
            if not properties_data:
                logger.warning("No properties returned from database query")
                logger.info("This may mean:")
                logger.info("1. No properties in database yet (run data loading first)")
                logger.info("2. All properties have is_reliable_data = FALSE")
                return properties

            for row in properties_data:
                # Skip if not reliable data
                is_reliable = row.get("is_reliable_data")
                if is_reliable is False or is_reliable is None:
                    continue

                property_uuid = row["id"]
                market_id = row.get("market_id")
                bedrooms = row.get("bedrooms")

                # Get market stats
                stats_key = (market_id, bedrooms)
                market_stat = market_stats.get(stats_key, {})

                # Build property dictionary
                property_data = {
                    "property_id": property_uuid,  # Internal UUID
                    "external_property_id": row.get("property_id"),
                    "title": row.get("title"),
                    "bedrooms": bedrooms,
                    "market_id": market_id,
                    "market_name": row.get("market_name"),
                    # Performance data
                    "revenue": row.get("revenue"),
                    "occupancy": row.get("occupancy"),
                    "adr": row.get("adr"),
                    "total_reviews": row.get("total_reviews"),
                    "rating": row.get("rating"),
                    "high_season_reviews": row.get("high_season_reviews"),
                    # Review analysis data
                    "total_months": row.get("total_months"),
                    "missing_months": row.get("missing_months"),
                    "avg_reviews_per_month": row.get("avg_reviews_per_month"),
                    # Host/property flags
                    "is_super_host": row.get("is_super_host"),
                    "is_guest_favorite": row.get("is_guest_favorite"),
                    # Amenities
                    "amenities_text": str(row.get("amenities", ""))
                    if row.get("amenities")
                    else None,
                    # Market stats
                    "market_avg_revenue": market_stat.get("avg_revenue"),
                    "market_max_revenue": market_stat.get("max_revenue"),
                    "market_avg_occupancy": market_stat.get("avg_occupancy"),
                    "market_avg_adr": market_stat.get("avg_adr"),
                    "market_property_count": market_stat.get("property_count"),
                }

                properties.append(property_data)

            # Apply limit if specified
            if self.limit:
                properties = properties[: self.limit]
                logger.info(f"Limited to {self.limit} properties for scoring")

            logger.info(f"Found {len(properties)} properties to score")
            return properties

        except Exception as e:
            logger.error(f"Error fetching property data: {e}")
            raise

    def _fetch_properties_batched(self, market_stats: Dict) -> List[Dict]:
        """
        Fallback method to fetch properties using batched table queries.

        This method fetches all data in 5 batch queries instead of N*5 individual queries.
        """
        # Fetch all properties with basic data
        properties_response = (
            self.client.table("properties")
            .select(
                "id, property_id, title, bedrooms, market_id, host_id, is_guest_favorite, is_reliable_data"
            )
            .execute()
        )

        if not properties_response.data:
            return []

        properties_list = properties_response.data
        property_ids = [p["id"] for p in properties_list]

        # Fetch all performance data in one batch
        perf_response = (
            self.client.table("property_performance")
            .select(
                "property_id, revenue, occupancy, adr, total_reviews, rating, high_season_reviews"
            )
            .in_("property_id", property_ids)
            .execute()
        )

        # Build performance lookup
        perf_lookup = (
            {p["property_id"]: p for p in perf_response.data}
            if perf_response.data
            else {}
        )

        # Fetch all review data in one batch
        reviews_response = (
            self.client.table("property_reviews")
            .select("property_id, total_months, missing_months, avg_reviews_per_month")
            .in_("property_id", property_ids)
            .execute()
        )

        # Build reviews lookup
        reviews_lookup = (
            {r["property_id"]: r for r in reviews_response.data}
            if reviews_response.data
            else {}
        )

        # Fetch all amenities in one batch
        amenities_response = (
            self.client.table("property_amenities")
            .select("property_id, amenities")
            .in_("property_id", property_ids)
            .execute()
        )

        # Build amenities lookup
        amenities_lookup = (
            {a["property_id"]: a for a in amenities_response.data}
            if amenities_response.data
            else {}
        )

        # Fetch all host data in one batch
        host_ids = [p["host_id"] for p in properties_list if p.get("host_id")]
        host_lookup = {}
        if host_ids:
            host_response = (
                self.client.table("hosts")
                .select("id, is_super_host")
                .in_("id", host_ids)
                .execute()
            )
            host_lookup = (
                {h["id"]: h for h in host_response.data} if host_response.data else {}
            )

        # Fetch all market names in one batch
        market_ids = [p["market_id"] for p in properties_list if p.get("market_id")]
        market_lookup = {}
        if market_ids:
            market_response = (
                self.client.table("markets")
                .select("id, name")
                .in_("id", market_ids)
                .execute()
            )
            market_lookup = (
                {m["id"]: m for m in market_response.data}
                if market_response.data
                else {}
            )

        # Combine all data
        combined_data = []
        for prop in properties_list:
            prop_id = prop["id"]
            combined_row = {
                **prop,
                "is_super_host": host_lookup.get(prop.get("host_id"), {}).get(
                    "is_super_host"
                ),
                "market_name": market_lookup.get(prop.get("market_id"), {}).get("name"),
                **perf_lookup.get(prop_id, {}),
                **reviews_lookup.get(prop_id, {}),
                **amenities_lookup.get(prop_id, {}),
            }
            combined_data.append(combined_row)

        return combined_data

    def score_property(self, property_data: dict) -> PropertyScore:
        """Calculate all scores for a single property"""

        # Calculate individual component scores
        revenue_score = calculate_revenue_score(
            property_data.get("revenue"),
            property_data.get("market_avg_revenue"),
            property_data.get("market_max_revenue"),
        )

        occupancy_score = calculate_occupancy_score(property_data.get("occupancy"))

        adr_score = calculate_adr_score(
            property_data.get("adr"),
            property_data.get("market_avg_adr"),
            property_data.get("occupancy"),
        )

        review_score = calculate_review_score(
            property_data.get("total_reviews"),
            property_data.get("rating"),
            property_data.get("avg_reviews_per_month"),
        )

        amenity_score = calculate_amenity_score(property_data.get("amenities_text"))

        host_score = calculate_host_score(
            property_data.get("is_super_host"), property_data.get("is_guest_favorite")
        )

        seasonal_score = calculate_seasonal_score(
            property_data.get("total_months"),
            property_data.get("missing_months"),
            property_data.get("high_season_reviews"),
            property_data.get("total_reviews"),
        )

        market_score = calculate_market_score(
            property_data.get("market_avg_occupancy"),
            property_data.get("market_avg_revenue"),
            property_data.get("market_property_count"),
        )

        # Calculate total
        total_score = calculate_total_score(
            revenue_score,
            occupancy_score,
            adr_score,
            review_score,
            amenity_score,
            host_score,
            seasonal_score,
            market_score,
            self.weights,
        )

        return PropertyScore(
            property_id=str(property_data["property_id"]),
            revenue_score=round(revenue_score, 2),
            occupancy_score=round(occupancy_score, 2),
            adr_score=round(adr_score, 2),
            review_score=round(review_score, 2),
            amenity_score=round(amenity_score, 2),
            host_score=round(host_score, 2),
            seasonal_score=round(seasonal_score, 2),
            market_score=round(market_score, 2),
            total_score=total_score,
        )

    def calculate_percentiles(self, scores: List[PropertyScore]) -> List[PropertyScore]:
        """Calculate percentile ranks within the dataset"""
        sorted_scores = sorted(scores, key=lambda x: x.total_score)
        n = len(sorted_scores)

        for i, score in enumerate(sorted_scores):
            percentile = (i / n) * 100 if n > 0 else 50
            score.percentile_rank = round(percentile, 2)
            score.opportunity_tier = assign_opportunity_tier(
                score.total_score, percentile
            )
            score.is_top_opportunity = score.opportunity_tier in ["PLATINUM", "GOLD"]

        return sorted_scores

    def save_scores(self, scores: List[PropertyScore]) -> Dict[str, int]:
        """
        Save scores to database using optimized bulk upsert operations.

        This method uses batch operations to reduce the number of database requests
        from 2*N (check + insert/update per property) to approximately 2 total requests
        (bulk upsert + temp table cleanup).

        Returns:
            Dictionary with 'inserted' and 'updated' counts.
        """
        logger.info(f"Saving scores for {len(scores)} properties...")

        try:
            # Prepare batch data for bulk upsert
            batch_data = []
            for score in scores:
                batch_data.append(
                    {
                        "property_id": score.property_id,
                        "revenue_score": score.revenue_score,
                        "occupancy_score": score.occupancy_score,
                        "adr_score": score.adr_score,
                        "review_score": score.review_score,
                        "amenity_score": score.amenity_score,
                        "host_score": score.host_score,
                        "seasonal_score": score.seasonal_score,
                        "market_score": score.market_score,
                        "total_score": score.total_score,
                        "percentile_rank": score.percentile_rank,
                        "is_top_opportunity": score.is_top_opportunity,
                        "opportunity_tier": score.opportunity_tier,
                        "scoring_version": self.scoring_version,
                    }
                )

            # Try to use the temp table upsert approach (most efficient)
            try:
                # Step 1: Insert all scores into temp table
                logger.info("Inserting scores into temp table...")
                self.client.table("property_investment_scores_temp").insert(
                    batch_data
                ).execute()

                # Step 2: Call the upsert function to merge temp table into main table
                logger.info("Upserting scores from temp table...")
                upsert_response = self.client.rpc(
                    "upsert_investment_scores_from_temp", {}
                ).execute()

                if upsert_response.data:
                    result = upsert_response.data[0]
                    inserted_count = result.get("inserted", 0)
                    updated_count = result.get("updated", 0)
                else:
                    # Fallback: count manually
                    inserted_count = len(batch_data)
                    updated_count = 0

                logger.info(
                    f"Scores saved: {inserted_count} inserted, {updated_count} updated"
                )
                return {"inserted": inserted_count, "updated": updated_count}

            except Exception as temp_table_error:
                logger.warning(
                    f"Temp table approach failed ({temp_table_error}), falling back to batch upsert..."
                )

                # Fallback: Use batch upsert with ON CONFLICT
                # This is still much better than individual operations
                inserted_count = 0
                updated_count = 0

                # Process in batches of 100 to avoid payload size limits
                batch_size = 100
                for i in range(0, len(batch_data), batch_size):
                    batch = batch_data[i : i + batch_size]

                    try:
                        # Try bulk insert with upsert
                        response = (
                            self.client.table("property_investment_scores")
                            .upsert(batch, on_conflict="property_id")
                            .execute()
                        )

                        # Count results
                        if response.data:
                            # Supabase doesn't distinguish between insert/update in upsert response
                            # We'll count all as updates for simplicity
                            updated_count += len(response.data)
                        else:
                            inserted_count += len(batch)

                    except Exception as batch_error:
                        logger.error(f"Error in batch {i // batch_size}: {batch_error}")
                        # If batch fails, try individual inserts for this batch
                        for item in batch:
                            try:
                                self.client.table("property_investment_scores").upsert(
                                    item, on_conflict="property_id"
                                ).execute()
                                updated_count += 1
                            except Exception as individual_error:
                                logger.error(
                                    f"Error saving score for property {item['property_id']}: {individual_error}"
                                )
                                continue

                logger.info(
                    f"Scores saved: {inserted_count} inserted, {updated_count} updated"
                )
                return {"inserted": inserted_count, "updated": updated_count}

        except Exception as e:
            logger.error(f"Error saving scores: {e}")
            raise

    def run(self) -> List[PropertyScore]:
        """Execute full scoring pipeline"""
        logger.info("Starting investment scoring pipeline...")

        # Connect to database
        self.connect()

        try:
            # Fetch data
            logger.info("Fetching property data...")
            properties = self.fetch_property_data()

            if not properties:
                logger.warning("No properties found to score")
                return []

            # Score each property
            logger.info("Calculating scores...")
            scores = [self.score_property(p) for p in properties]

            # Calculate percentiles and assign tiers
            logger.info("Calculating percentiles and assigning tiers...")
            scores = self.calculate_percentiles(scores)

            # Save to database
            logger.info("Saving scores to database...")
            self.save_scores(scores)

            # Log summary
            self._print_summary(scores)

            return scores

        except Exception as e:
            logger.error(f"Error during scoring: {e}")
            raise
        finally:
            self.disconnect()

    def _print_summary(self, scores: List[PropertyScore]) -> None:
        """Print summary of scoring results"""
        logger.info("=" * 60)
        logger.info("Scoring Summary")
        logger.info("=" * 60)

        if not scores:
            logger.info("No properties scored")
            return

        # Calculate statistics
        total_scores = [s.total_score for s in scores]
        avg_score = np.mean(total_scores)
        max_score = np.max(total_scores)
        min_score = np.min(total_scores)

        # Count by tier
        tier_counts = {}
        top_opportunities = 0

        for score in scores:
            tier = score.opportunity_tier
            tier_counts[tier] = tier_counts.get(tier, 0) + 1
            if score.is_top_opportunity:
                top_opportunities += 1

        # Print statistics
        logger.info(f"Total properties scored: {len(scores)}")
        logger.info(f"Average total score: {avg_score:.2f}")
        logger.info(f"Score range: {min_score:.2f} - {max_score:.2f}")
        logger.info(f"Top opportunities: {top_opportunities}")
        logger.info("")
        logger.info("Tier distribution:")
        for tier in ["PLATINUM", "GOLD", "SILVER", "BRONZE"]:
            count = tier_counts.get(tier, 0)
            percentage = (count / len(scores)) * 100 if scores else 0
            logger.info(f"  {tier}: {count} ({percentage:.1f}%)")
        logger.info("=" * 60)


# =============================================================================
# QUERY HELPERS
# =============================================================================


def get_top_opportunities(limit: int = 20) -> List[Dict]:
    """Retrieve top investment opportunities"""
    load_dotenv()
    client = get_supabase_client()

    try:
        response = client.rpc("get_top_opportunities", {"limit_count": limit}).execute()
        return response.data if response.data else []
    except Exception as e:
        logger.error(f"Error fetching top opportunities: {e}")
        return []


def get_undervalued_opportunities(limit: int = 10) -> List[Dict]:
    """
    Find undervalued properties: high potential but underperforming on revenue.
    These are properties with strong fundamentals that may be underpriced.
    """
    load_dotenv()
    client = get_supabase_client()

    try:
        response = client.rpc(
            "get_undervalued_opportunities", {"limit_count": limit}
        ).execute()
        return response.data if response.data else []
    except Exception as e:
        logger.error(f"Error fetching undervalued opportunities: {e}")
        return []


# =============================================================================
# USAGE EXAMPLE
# =============================================================================


def main():
    """Main entry point for property scoring."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Calculate investment opportunity scores for properties"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of properties to score (for testing, e.g., --limit 10)",
    )

    args = parser.parse_args()

    try:
        scorer = InvestmentScorer(limit=args.limit)
        scores = scorer.run()

        # Print top opportunities
        if scores:
            top_scores = sorted(scores, key=lambda x: x.total_score, reverse=True)[:10]
            logger.info("\n=== TOP 10 INVESTMENT OPPORTUNITIES ===")
            for score in top_scores:
                logger.info(
                    f"Score: {score.total_score} | Tier: {score.opportunity_tier} | Property ID: {score.property_id}"
                )

        return 0
    except Exception as e:
        logger.error(f"Property scoring failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
