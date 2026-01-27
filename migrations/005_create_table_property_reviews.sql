CREATE TABLE IF NOT EXISTS property_reviews (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,

    -- Review time series data
    total_months INTEGER,
    missing_months INTEGER,
    avg_reviews_per_month NUMERIC,

    -- Guest demographics
    review_pct_stayed_with_kids NUMERIC,
    review_pct_group_trip NUMERIC,
    review_pct_stayed_with_a_pet NUMERIC,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(property_id)
);

-- Function to upsert property_reviews from temp table
CREATE OR REPLACE FUNCTION upsert_property_reviews_from_temp()
RETURNS TABLE(
    inserted INTEGER,
    updated INTEGER
) AS $$
DECLARE
    v_inserted INTEGER := 0;
    v_updated INTEGER := 0;
BEGIN
    -- Update existing property_reviews
    UPDATE property_reviews p
    SET
        total_months = COALESCE(t.total_months, p.total_months),
        missing_months = COALESCE(t.missing_months, p.missing_months),
        avg_reviews_per_month = COALESCE(t.avg_reviews_per_month, p.avg_reviews_per_month),
        review_pct_stayed_with_kids = COALESCE(t.review_pct_stayed_with_kids, p.review_pct_stayed_with_kids),
        review_pct_group_trip = COALESCE(t.review_pct_group_trip, p.review_pct_group_trip),
        review_pct_stayed_with_a_pet = COALESCE(t.review_pct_stayed_with_a_pet, p.review_pct_stayed_with_a_pet)
    FROM property_reviews_temp t
    WHERE p.property_id = t.property_id
    AND (
        p.total_months IS DISTINCT FROM t.total_months
        OR p.missing_months IS DISTINCT FROM t.missing_months
        OR p.avg_reviews_per_month IS DISTINCT FROM t.avg_reviews_per_month
        OR p.review_pct_stayed_with_kids IS DISTINCT FROM t.review_pct_stayed_with_kids
        OR p.review_pct_group_trip IS DISTINCT FROM t.review_pct_group_trip
        OR p.review_pct_stayed_with_a_pet IS DISTINCT FROM t.review_pct_stayed_with_a_pet
    );

    GET DIAGNOSTICS v_updated = ROW_COUNT;

    -- Insert new property_reviews
    INSERT INTO property_reviews (
        id, property_id, total_months, missing_months, avg_reviews_per_month,
        review_pct_stayed_with_kids, review_pct_group_trip, review_pct_stayed_with_a_pet, created_at
    )
    SELECT
        t.id, t.property_id, t.total_months, t.missing_months, t.avg_reviews_per_month,
        t.review_pct_stayed_with_kids, t.review_pct_group_trip, t.review_pct_stayed_with_a_pet, t.created_at
    FROM property_reviews_temp t
    WHERE NOT EXISTS (
        SELECT 1 FROM property_reviews p WHERE p.property_id = t.property_id
    );

    GET DIAGNOSTICS v_inserted = ROW_COUNT;

    -- Clear temp table
    TRUNCATE TABLE property_reviews_temp;

    RETURN QUERY SELECT v_inserted, v_updated;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION upsert_property_reviews_from_temp() IS 'Upsert property_reviews from property_reviews_temp table using INSERT...ON CONFLICT pattern. Returns (inserted, updated) counts.';