-- Migration: 009_create_materialized_views
-- Description: Create materialized views for optimized API queries

-- ============================================================================
-- MATERIALIZED VIEW: Properties with Scores
-- ============================================================================
-- This view provides a pre-joined dataset of properties with their investment scores,
-- performance metrics, and market information for fast querying.

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_properties_with_scores AS
SELECT
    p.id,
    p.property_id,
    p.title,
    p.bedrooms,
    p.bathrooms,
    p.accommodates,
    p.property_type,
    p.room_type,
    p.beds,
    p.latitude,
    p.longitude,
    p.city_name,
    p.zipcode,
    p.airbnb_listing_url,
    p.vrbo_listing_url,
    p.is_guest_favorite,
    p.is_reliable_data,
    p.market_id,
    m.name AS market_name,
    m.state_name AS market_state,
    pp.revenue,
    pp.revenue_potential,
    pp.adr,
    pp.cleaning_fee,
    pp.occupancy,
    pp.available_nights,
    pp.total_reviews,
    pp.rating,
    pp.property_reviews_count,
    pp.high_season_reviews,
    pp.high_season_label,
    pis.revenue_score,
    pis.occupancy_score,
    pis.adr_score,
    pis.review_score,
    pis.amenity_score,
    pis.host_score,
    pis.seasonal_score,
    pis.market_score,
    pis.total_score,
    pis.percentile_rank,
    pis.is_top_opportunity,
    pis.opportunity_tier,
    pis.scoring_version,
    pis.calculated_at AS score_calculated_at,
    p.created_at,
    p.updated_at
FROM properties p
LEFT JOIN markets m ON m.id = p.market_id
LEFT JOIN property_performance pp ON pp.property_id = p.id
LEFT JOIN property_investment_scores pis ON pis.property_id = p.id
WHERE p.is_reliable_data = TRUE;

-- Create indexes for the materialized view
CREATE INDEX IF NOT EXISTS idx_mv_properties_market_id ON mv_properties_with_scores(market_id);
CREATE INDEX IF NOT EXISTS idx_mv_properties_bedrooms ON mv_properties_with_scores(bedrooms);
CREATE INDEX IF NOT EXISTS idx_mv_properties_revenue ON mv_properties_with_scores(revenue DESC);
CREATE INDEX IF NOT EXISTS idx_mv_properties_total_score ON mv_properties_with_scores(total_score DESC);
CREATE INDEX IF NOT EXISTS idx_mv_properties_opportunity_tier ON mv_properties_with_scores(opportunity_tier);
CREATE INDEX IF NOT EXISTS idx_mv_properties_top_opportunity ON mv_properties_with_scores(is_top_opportunity) WHERE is_top_opportunity = TRUE;
CREATE INDEX IF NOT EXISTS idx_mv_properties_location ON mv_properties_with_scores(latitude, longitude);

-- ============================================================================
-- MATERIALIZED VIEW: Property Analysis with Market Averages
-- ============================================================================
-- This view provides property details with market averages for comparison,
-- grouped by market and bedroom count.

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_property_analysis AS
WITH market_stats AS (
    SELECT
        p.market_id,
        p.bedrooms,
        COUNT(*) AS property_count,
        AVG(pp.revenue) AS avg_revenue,
        AVG(pp.occupancy) AS avg_occupancy,
        AVG(pp.adr) AS avg_adr,
        AVG(pp.rating) AS avg_rating,
        AVG(pis.total_score) AS avg_total_score,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY pp.revenue) AS median_revenue,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY pp.occupancy) AS median_occupancy,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY pp.adr) AS median_adr,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY pp.rating) AS median_rating,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY pis.total_score) AS median_total_score
    FROM properties p
    LEFT JOIN property_performance pp ON pp.property_id = p.id
    LEFT JOIN property_investment_scores pis ON pis.property_id = p.id
    WHERE p.is_reliable_data = TRUE
      AND p.bedrooms IS NOT NULL
    GROUP BY p.market_id, p.bedrooms
)
SELECT
    p.id,
    p.property_id,
    p.title,
    p.bedrooms,
    p.bathrooms,
    p.accommodates,
    p.property_type,
    p.room_type,
    p.beds,
    p.latitude,
    p.longitude,
    p.city_name,
    p.zipcode,
    p.airbnb_listing_url,
    p.vrbo_listing_url,
    p.is_guest_favorite,
    p.is_reliable_data,
    p.market_id,
    m.name AS market_name,
    m.state_name AS market_state,
    pp.revenue,
    pp.revenue_potential,
    pp.adr,
    pp.cleaning_fee,
    pp.occupancy,
    pp.available_nights,
    pp.total_reviews,
    pp.rating,
    pp.property_reviews_count,
    pp.high_season_reviews,
    pp.high_season_label,
    pis.revenue_score,
    pis.occupancy_score,
    pis.adr_score,
    pis.review_score,
    pis.amenity_score,
    pis.host_score,
    pis.seasonal_score,
    pis.market_score,
    pis.total_score,
    pis.percentile_rank,
    pis.is_top_opportunity,
    pis.opportunity_tier,
    pis.scoring_version,
    pis.calculated_at AS score_calculated_at,
    h.is_super_host AS host_is_super_host,
    -- Market averages for comparison
    ms.property_count AS market_property_count,
    ms.avg_revenue AS market_avg_revenue,
    ms.avg_occupancy AS market_avg_occupancy,
    ms.avg_adr AS market_avg_adr,
    ms.avg_rating AS market_avg_rating,
    ms.avg_total_score AS market_avg_total_score,
    ms.median_revenue AS market_median_revenue,
    ms.median_occupancy AS market_median_occupancy,
    ms.median_adr AS market_median_adr,
    ms.median_rating AS market_median_rating,
    ms.median_total_score AS market_median_total_score,
    -- Performance vs market
    CASE
        WHEN ms.avg_revenue > 0 THEN ROUND((pp.revenue / ms.avg_revenue - 1) * 100, 2)
        ELSE NULL
    END AS revenue_vs_market_pct,
    CASE
        WHEN ms.avg_occupancy > 0 THEN ROUND((pp.occupancy / ms.avg_occupancy - 1) * 100, 2)
        ELSE NULL
    END AS occupancy_vs_market_pct,
    CASE
        WHEN ms.avg_adr > 0 THEN ROUND((pp.adr / ms.avg_adr - 1) * 100, 2)
        ELSE NULL
    END AS adr_vs_market_pct,
    CASE
        WHEN ms.avg_rating > 0 THEN ROUND((pp.rating / ms.avg_rating - 1) * 100, 2)
        ELSE NULL
    END AS rating_vs_market_pct,
    p.created_at,
    p.updated_at
FROM properties p
LEFT JOIN markets m ON m.id = p.market_id
LEFT JOIN property_performance pp ON pp.property_id = p.id
LEFT JOIN property_investment_scores pis ON pis.property_id = p.id
LEFT JOIN hosts h ON h.id = p.host_id
LEFT JOIN market_stats ms ON ms.market_id = p.market_id AND ms.bedrooms = p.bedrooms
WHERE p.is_reliable_data = TRUE;

-- Create indexes for the property analysis view
CREATE INDEX IF NOT EXISTS idx_mv_analysis_id ON mv_property_analysis(id);
CREATE INDEX IF NOT EXISTS idx_mv_analysis_market_bedroom ON mv_property_analysis(market_id, bedrooms);
CREATE INDEX IF NOT EXISTS idx_mv_analysis_total_score ON mv_property_analysis(total_score DESC);

-- ============================================================================
-- MATERIALIZED VIEW: Top Performers
-- ============================================================================
-- This view provides the top 20 investment opportunities across all markets,
-- grouped by market and bedroom category.

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_top_performers AS
WITH ranked_properties AS (
    SELECT
        p.id,
        p.property_id,
        p.title,
        p.bedrooms,
        p.bathrooms,
        p.accommodates,
        p.property_type,
        p.room_type,
        p.latitude,
        p.longitude,
        p.city_name,
        p.zipcode,
        p.airbnb_listing_url,
        p.market_id,
        m.name AS market_name,
        m.state_name AS market_state,
        pp.revenue,
        pp.occupancy,
        pp.adr,
        pp.rating,
        pp.total_reviews,
        pis.revenue_score,
        pis.occupancy_score,
        pis.adr_score,
        pis.review_score,
        pis.amenity_score,
        pis.host_score,
        pis.seasonal_score,
        pis.market_score,
        pis.total_score,
        pis.percentile_rank,
        pis.opportunity_tier,
        pis.is_top_opportunity,
        p.is_guest_favorite,
        h.is_super_host,
        -- Rank within market and bedroom category
        ROW_NUMBER() OVER (
            PARTITION BY p.market_id, p.bedrooms 
            ORDER BY pis.total_score DESC
        ) AS rank_in_category,
        -- Rank overall
        ROW_NUMBER() OVER (ORDER BY pis.total_score DESC) AS overall_rank,
        -- Count properties in this category
        COUNT(*) OVER (PARTITION BY p.market_id, p.bedrooms) AS category_count
    FROM properties p
    LEFT JOIN markets m ON m.id = p.market_id
    LEFT JOIN property_performance pp ON pp.property_id = p.id
    LEFT JOIN property_investment_scores pis ON pis.property_id = p.id
    LEFT JOIN hosts h ON h.id = p.host_id
    WHERE p.is_reliable_data = TRUE
      AND pis.total_score IS NOT NULL
)
SELECT 
    id,
    property_id,
    title,
    bedrooms,
    bathrooms,
    accommodates,
    property_type,
    room_type,
    latitude,
    longitude,
    city_name,
    zipcode,
    airbnb_listing_url,
    market_id,
    market_name,
    market_state,
    revenue,
    occupancy,
    adr,
    rating,
    total_reviews,
    revenue_score,
    occupancy_score,
    adr_score,
    review_score,
    amenity_score,
    host_score,
    seasonal_score,
    market_score,
    total_score,
    percentile_rank,
    opportunity_tier,
    is_top_opportunity,
    is_guest_favorite,
    is_super_host,
    rank_in_category,
    overall_rank,
    category_count,
    -- Calculate percentile within category
    ROUND((rank_in_category::NUMERIC / category_count::NUMERIC) * 100, 2) AS category_percentile,
    -- Key differentiating factors
    CASE 
        WHEN revenue_score >= 80 THEN 'High Revenue Performance'
        WHEN occupancy_score >= 80 THEN 'Strong Occupancy'
        WHEN amenity_score >= 75 THEN 'Premium Amenities'
        WHEN review_score >= 75 THEN 'Excellent Reviews'
        WHEN host_score >= 80 THEN 'Superhost Quality'
        WHEN adr_score >= 80 THEN 'Premium Pricing'
        ELSE 'Balanced Performance'
    END AS key_differentiator
FROM ranked_properties
WHERE overall_rank <= 20;  -- Top 20 overall

-- Create indexes for top performers view
CREATE INDEX IF NOT EXISTS idx_mv_top_performers_market ON mv_top_performers(market_id);
CREATE INDEX IF NOT EXISTS idx_mv_top_performers_bedroom ON mv_top_performers(bedrooms);
CREATE INDEX IF NOT EXISTS idx_mv_top_performers_total_score ON mv_top_performers(total_score DESC);
CREATE INDEX IF NOT EXISTS idx_mv_top_performers_overall_rank ON mv_top_performers(overall_rank);

-- ============================================================================
-- REFRESH FUNCTIONS
-- ============================================================================

-- Function to refresh all materialized views
CREATE OR REPLACE FUNCTION refresh_all_materialized_views()
RETURNS VOID AS $$
BEGIN
    REFRESH MATERIALIZED VIEW mv_properties_with_scores;
    REFRESH MATERIALIZED VIEW mv_property_analysis;
    REFRESH MATERIALIZED VIEW mv_top_performers;
END;
$$ LANGUAGE plpgsql;

-- Function to refresh properties with scores view
CREATE OR REPLACE FUNCTION refresh_mv_properties_with_scores()
RETURNS VOID AS $$
BEGIN
    REFRESH MATERIALIZED VIEW mv_properties_with_scores;
END;
$$ LANGUAGE plpgsql;

-- Function to refresh property analysis view
CREATE OR REPLACE FUNCTION refresh_mv_property_analysis()
RETURNS VOID AS $$
BEGIN
    REFRESH MATERIALIZED VIEW mv_property_analysis;
END;
$$ LANGUAGE plpgsql;

-- Function to refresh top performers view
CREATE OR REPLACE FUNCTION refresh_mv_top_performers()
RETURNS VOID AS $$
BEGIN
    REFRESH MATERIALIZED VIEW mv_top_performers;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON MATERIALIZED VIEW mv_properties_with_scores IS 'Pre-joined view of properties with investment scores, performance metrics, and market information for fast querying';
COMMENT ON MATERIALIZED VIEW mv_property_analysis IS 'Property details with market averages for comparison, grouped by market and bedroom count';
COMMENT ON MATERIALIZED VIEW mv_top_performers IS 'Top 20 investment opportunities across all markets, grouped by market and bedroom category';

COMMENT ON FUNCTION refresh_all_materialized_views() IS 'Refresh all materialized views to update cached data';
COMMENT ON FUNCTION refresh_mv_properties_with_scores() IS 'Refresh the properties with scores materialized view';
COMMENT ON FUNCTION refresh_mv_property_analysis() IS 'Refresh the property analysis materialized view';
COMMENT ON FUNCTION refresh_mv_top_performers() IS 'Refresh the top performers materialized view';
