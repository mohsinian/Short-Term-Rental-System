CREATE TABLE IF NOT EXISTS market_benchmarks (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    market_id UUID NOT NULL REFERENCES markets(id) ON DELETE CASCADE,
    bedroom_count INTEGER,

    -- Market averages
    avg_revenue NUMERIC,
    avg_occupancy NUMERIC,
    avg_adr NUMERIC,

    report_date DATE DEFAULT CURRENT_DATE,
    UNIQUE(market_id, bedroom_count, report_date)
);

-- Function to upsert market_benchmarks from temp table
CREATE OR REPLACE FUNCTION upsert_market_benchmarks_from_temp()
RETURNS TABLE(
    inserted INTEGER,
    updated INTEGER
) AS $$
DECLARE
    v_inserted INTEGER := 0;
    v_updated INTEGER := 0;
BEGIN
    -- Update existing market_benchmarks
    UPDATE market_benchmarks m
    SET
        avg_revenue = COALESCE(t.avg_revenue, m.avg_revenue),
        avg_occupancy = COALESCE(t.avg_occupancy, m.avg_occupancy),
        avg_adr = COALESCE(t.avg_adr, m.avg_adr)
    FROM market_benchmarks_temp t
    WHERE m.market_id = t.market_id
    AND m.bedroom_count = t.bedroom_count
    AND m.report_date = t.report_date
    AND (
        m.avg_revenue IS DISTINCT FROM t.avg_revenue
        OR m.avg_occupancy IS DISTINCT FROM t.avg_occupancy
        OR m.avg_adr IS DISTINCT FROM t.avg_adr
    );

    GET DIAGNOSTICS v_updated = ROW_COUNT;

    -- Insert new market_benchmarks
    INSERT INTO market_benchmarks (
        id, market_id, bedroom_count, avg_revenue, avg_occupancy, avg_adr, report_date
    )
    SELECT
        t.id, t.market_id, t.bedroom_count, t.avg_revenue, t.avg_occupancy, t.avg_adr, t.report_date
    FROM market_benchmarks_temp t
    WHERE NOT EXISTS (
        SELECT 1 FROM market_benchmarks m
        WHERE m.market_id = t.market_id
        AND m.bedroom_count = t.bedroom_count
        AND m.report_date = t.report_date
    );

    GET DIAGNOSTICS v_inserted = ROW_COUNT;

    -- Clear temp table
    TRUNCATE TABLE market_benchmarks_temp;

    RETURN QUERY SELECT v_inserted, v_updated;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION upsert_market_benchmarks_from_temp() IS 'Upsert market_benchmarks from market_benchmarks_temp table using INSERT...ON CONFLICT pattern. Returns (inserted, updated) counts.';