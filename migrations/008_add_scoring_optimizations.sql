-- Migration: 008_add_scoring_optimizations
-- Description: Add temp table and RPC functions for optimized batch scoring operations

-- Create temp table for bulk upsert operations
-- This table is used as a staging area for bulk insert operations
CREATE TABLE IF NOT EXISTS property_investment_scores_temp (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    property_id UUID NOT NULL,

    -- Individual Component Scores (0-100 scale)
    revenue_score NUMERIC,
    occupancy_score NUMERIC,
    adr_score NUMERIC,
    review_score NUMERIC,
    amenity_score NUMERIC,
    host_score NUMERIC,
    seasonal_score NUMERIC,
    market_score NUMERIC,

    -- Composite Scores
    total_score NUMERIC,
    percentile_rank NUMERIC,

    -- Investment Flags
    is_top_opportunity BOOLEAN,
    opportunity_tier VARCHAR(20),

    -- Metadata
    scoring_version VARCHAR(20),
    calculated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add index on property_id for faster lookups
CREATE INDEX IF NOT EXISTS idx_scores_temp_property_id ON property_investment_scores_temp(property_id);

-- Function to get all properties with their related data in a single query
-- This replaces multiple individual queries with one comprehensive JOIN
CREATE OR REPLACE FUNCTION get_properties_for_scoring()
RETURNS TABLE (
    id UUID,
    property_id VARCHAR,
    title VARCHAR,
    bedrooms NUMERIC,
    market_id UUID,
    is_guest_favorite BOOLEAN,
    is_reliable_data BOOLEAN,
    is_super_host BOOLEAN,
    market_name VARCHAR,
    revenue NUMERIC,
    occupancy NUMERIC,
    adr NUMERIC,
    total_reviews INTEGER,
    rating NUMERIC,
    high_season_reviews INTEGER,
    total_months INTEGER,
    missing_months INTEGER,
    avg_reviews_per_month NUMERIC,
    amenities TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.id,
        p.property_id,
        p.title,
        p.bedrooms,
        p.market_id,
        p.is_guest_favorite,
        p.is_reliable_data,
        h.is_super_host,
        m.name as market_name,
        pp.revenue,
        pp.occupancy,
        pp.adr,
        pp.total_reviews,
        pp.rating,
        pp.high_season_reviews,
        pr.total_months,
        pr.missing_months,
        pr.avg_reviews_per_month,
        CASE
            WHEN pa.amenities IS NULL THEN NULL
            ELSE pa.amenities #>> '{}'
        END as amenities
    FROM properties p
    LEFT JOIN hosts h ON h.id = p.host_id
    LEFT JOIN markets m ON m.id = p.market_id
    LEFT JOIN property_performance pp ON pp.property_id = p.id
    LEFT JOIN property_reviews pr ON pr.property_id = p.id
    LEFT JOIN property_amenities pa ON pa.property_id = p.id
    WHERE p.is_reliable_data = TRUE;
END;
$$ LANGUAGE plpgsql;

-- Add comments for documentation
COMMENT ON TABLE property_investment_scores_temp IS 'Temporary staging table for bulk upsert operations on property investment scores';
COMMENT ON FUNCTION get_properties_for_scoring() IS 'Returns all properties with their related data (performance, reviews, amenities, host, market) in a single optimized query';
