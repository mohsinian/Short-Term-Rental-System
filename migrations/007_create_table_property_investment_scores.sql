-- Migration: 007_create_table_property_investment_scores
-- Description: Create table to store investment opportunity scores

CREATE TABLE IF NOT EXISTS property_investment_scores (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,

    -- Individual Component Scores (0-100 scale)
    revenue_score NUMERIC,           -- Revenue vs market average
    occupancy_score NUMERIC,         -- Occupancy consistency
    adr_score NUMERIC,               -- ADR positioning
    review_score NUMERIC,            -- Review volume and ratings
    amenity_score NUMERIC,           -- High-value amenities
    host_score NUMERIC,              -- Superhost/guest favorite status
    seasonal_score NUMERIC,          -- Seasonal stability
    market_score NUMERIC,            -- Market strength

    -- Composite Scores
    total_score NUMERIC,             -- Weighted composite score
    percentile_rank NUMERIC,         -- Percentile within market

    -- Investment Flags
    is_top_opportunity BOOLEAN DEFAULT FALSE,
    opportunity_tier VARCHAR(20),    -- 'PLATINUM', 'GOLD', 'SILVER', 'BRONZE'

    -- Metadata
    scoring_version VARCHAR(20) DEFAULT '1.0',
    calculated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(property_id)
);

CREATE INDEX IF NOT EXISTS idx_investment_scores_total ON property_investment_scores(total_score DESC);
CREATE INDEX IF NOT EXISTS idx_investment_scores_tier ON property_investment_scores(opportunity_tier);
CREATE INDEX IF NOT EXISTS idx_investment_scores_top ON property_investment_scores(is_top_opportunity) WHERE is_top_opportunity = TRUE;
CREATE INDEX IF NOT EXISTS idx_investment_scores_property_id ON property_investment_scores(property_id);

-- Function to upsert investment scores from temp table
CREATE OR REPLACE FUNCTION upsert_investment_scores_from_temp()
RETURNS TABLE(
    inserted INTEGER,
    updated INTEGER
) AS $$
DECLARE
    v_inserted INTEGER := 0;
    v_updated INTEGER := 0;
BEGIN
    -- Update existing scores
    UPDATE property_investment_scores p
    SET
        revenue_score = t.revenue_score,
        occupancy_score = t.occupancy_score,
        adr_score = t.adr_score,
        review_score = t.review_score,
        amenity_score = t.amenity_score,
        host_score = t.host_score,
        seasonal_score = t.seasonal_score,
        market_score = t.market_score,
        total_score = t.total_score,
        percentile_rank = t.percentile_rank,
        is_top_opportunity = t.is_top_opportunity,
        opportunity_tier = t.opportunity_tier,
        scoring_version = t.scoring_version,
        calculated_at = NOW()
    FROM property_investment_scores_temp t
    WHERE p.property_id = t.property_id;

    GET DIAGNOSTICS v_updated = ROW_COUNT;

    -- Insert new scores
    INSERT INTO property_investment_scores (
        id, property_id, revenue_score, occupancy_score, adr_score,
        review_score, amenity_score, host_score, seasonal_score, market_score,
        total_score, percentile_rank, is_top_opportunity, opportunity_tier,
        scoring_version, calculated_at
    )
    SELECT
        t.id, t.property_id, t.revenue_score, t.occupancy_score, t.adr_score,
        t.review_score, t.amenity_score, t.host_score, t.seasonal_score, t.market_score,
        t.total_score, t.percentile_rank, t.is_top_opportunity, t.opportunity_tier,
        t.scoring_version, t.calculated_at
    FROM property_investment_scores_temp t
    WHERE NOT EXISTS (
        SELECT 1 FROM property_investment_scores p WHERE p.property_id = t.property_id
    );

    GET DIAGNOSTICS v_inserted = ROW_COUNT;

    TRUNCATE TABLE property_investment_scores_temp;

    RETURN QUERY SELECT v_inserted, v_updated;
END;
$$ LANGUAGE plpgsql;

COMMENT ON TABLE property_investment_scores IS 'Stores calculated investment opportunity scores for properties';
COMMENT ON FUNCTION upsert_investment_scores_from_temp() IS 'Upsert property_investment_scores from property_investment_scores_temp table using INSERT...ON CONFLICT pattern. Returns (inserted, updated) counts.';

-- =============================================================================
-- SCORING HELPER FUNCTIONS
-- =============================================================================

-- Function to get market statistics for scoring
CREATE OR REPLACE FUNCTION get_market_stats()
RETURNS TABLE (
    market_id UUID,
    bedrooms NUMERIC,
    avg_revenue NUMERIC,
    max_revenue NUMERIC,
    avg_occupancy NUMERIC,
    avg_adr NUMERIC,
    property_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.market_id,
        p.bedrooms,
        AVG(pp.revenue) as avg_revenue,
        MAX(pp.revenue) as max_revenue,
        AVG(pp.occupancy) as avg_occupancy,
        AVG(pp.adr) as avg_adr,
        COUNT(*) as property_count
    FROM properties p
    JOIN property_performance pp ON pp.property_id = p.id
    WHERE p.bedrooms IS NOT NULL
      AND pp.revenue IS NOT NULL
    GROUP BY p.market_id, p.bedrooms;
END;
$$ LANGUAGE plpgsql;

-- Function to get top investment opportunities
CREATE OR REPLACE FUNCTION get_top_opportunities(limit_count INTEGER DEFAULT 20)
RETURNS TABLE (
    external_id VARCHAR,
    title VARCHAR,
    bedrooms NUMERIC,
    market VARCHAR,
    revenue NUMERIC,
    occupancy NUMERIC,
    adr NUMERIC,
    total_score NUMERIC,
    opportunity_tier VARCHAR,
    revenue_score NUMERIC,
    occupancy_score NUMERIC,
    adr_score NUMERIC,
    review_score NUMERIC,
    amenity_score NUMERIC,
    percentile_rank NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.property_id as external_id,
        p.title,
        p.bedrooms,
        m.name as market,
        pp.revenue,
        pp.occupancy,
        pp.adr,
        pis.total_score,
        pis.opportunity_tier,
        pis.revenue_score,
        pis.occupancy_score,
        pis.adr_score,
        pis.review_score,
        pis.amenity_score,
        pis.percentile_rank
    FROM property_investment_scores pis
    JOIN properties p ON p.id = pis.property_id
    JOIN property_performance pp ON pp.property_id = p.id
    JOIN markets m ON m.id = p.market_id
    WHERE pis.is_top_opportunity = TRUE
    ORDER BY pis.total_score DESC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- Function to get undervalued opportunities
CREATE OR REPLACE FUNCTION get_undervalued_opportunities(limit_count INTEGER DEFAULT 10)
RETURNS TABLE (
    external_id VARCHAR,
    title VARCHAR,
    bedrooms NUMERIC,
    market VARCHAR,
    revenue NUMERIC,
    adr NUMERIC,
    occupancy NUMERIC,
    total_score NUMERIC,
    revenue_score NUMERIC,
    occupancy_score NUMERIC,
    amenity_score NUMERIC,
    review_score NUMERIC,
    quality_avg NUMERIC,
    revenue_performance NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.property_id as external_id,
        p.title,
        p.bedrooms,
        m.name as market,
        pp.revenue,
        pp.adr,
        pp.occupancy,
        pis.total_score,
        pis.revenue_score,
        pis.occupancy_score,
        pis.amenity_score,
        pis.review_score,
        (pis.occupancy_score + pis.amenity_score + pis.review_score) / 3.0 as quality_avg,
        pis.revenue_score as revenue_performance
    FROM property_investment_scores pis
    JOIN properties p ON p.id = pis.property_id
    JOIN property_performance pp ON pp.property_id = p.id
    JOIN markets m ON m.id = p.market_id
    WHERE pis.revenue_score < 50  -- Below average revenue
      AND pis.occupancy_score >= 70  -- But strong occupancy
      AND pis.review_score >= 60  -- And good reviews
    ORDER BY
        (pis.occupancy_score + pis.amenity_score + pis.review_score - pis.revenue_score) DESC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- Add comments for documentation
COMMENT ON FUNCTION get_market_stats() IS 'Returns market statistics grouped by market and bedroom count for scoring calculations';
COMMENT ON FUNCTION get_top_opportunities(limit_count INTEGER) IS 'Returns top investment opportunities sorted by total score';
COMMENT ON FUNCTION get_undervalued_opportunities(limit_count INTEGER) IS 'Returns undervalued properties with strong fundamentals but below-average revenue performance';
