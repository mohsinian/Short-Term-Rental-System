-- CTE Approach
WITH market_bedroom_averages AS (
    -- Step 1: Calculate average metrics per market and bedroom count
    SELECT
        p.market_id,
        p.bedrooms,
        AVG(pp.revenue) AS avg_revenue,
        AVG(pp.occupancy) AS avg_occupancy,
        AVG(pp.adr) AS avg_adr,
        COUNT(*) AS property_count
    FROM properties p
    INNER JOIN property_performance pp ON pp.property_id = p.id
    WHERE p.bedrooms IS NOT NULL
      AND pp.revenue IS NOT NULL
    GROUP BY p.market_id, p.bedrooms
),

property_rankings AS (
    -- Step 2: Rank properties by revenue within each market/bedroom category
    SELECT
        p.id AS property_id,
        p.property_id AS external_property_id,
        p.title,
        p.market_id,
        p.bedrooms,
        pp.revenue,
        pp.occupancy,
        pp.adr,
        ROW_NUMBER() OVER (
            PARTITION BY p.market_id, p.bedrooms 
            ORDER BY pp.revenue DESC NULLS LAST
        ) AS revenue_rank
    FROM properties p
    INNER JOIN property_performance pp ON pp.property_id = p.id
    WHERE p.bedrooms IS NOT NULL
      AND pp.revenue IS NOT NULL
),

top_properties AS (
    -- Step 3: Filter to top 3 per market/bedroom
    SELECT *
    FROM property_rankings
    WHERE revenue_rank <= 3
)

-- Final join: Combine top properties with market averages
SELECT
    m.name AS market_name,
    tp.bedrooms AS bedroom_count,
    CONCAT(tp.bedrooms, 'BR') AS bedroom_category,
    tp.revenue_rank,
    tp.external_property_id,
    tp.title AS property_title,

    -- Property Performance
    ROUND(tp.revenue::numeric, 2) AS property_revenue,
    ROUND(tp.occupancy::numeric, 4) AS property_occupancy,
    ROUND(tp.adr::numeric, 2) AS property_adr,

    -- Market Averages
    ROUND(mba.avg_revenue::numeric, 2) AS market_avg_revenue,
    ROUND(mba.avg_occupancy::numeric, 4) AS market_avg_occupancy,
    ROUND(mba.avg_adr::numeric, 2) AS market_avg_adr,

    -- Revenue Gap Analysis
    ROUND((tp.revenue - mba.avg_revenue)::numeric, 2) AS revenue_gap,
    ROUND(((tp.revenue - mba.avg_revenue) / NULLIF(mba.avg_revenue, 0) * 100)::numeric, 2) AS revenue_gap_pct,

    -- Context
    mba.property_count AS properties_in_category

FROM top_properties tp
INNER JOIN markets m ON m.id = tp.market_id
INNER JOIN market_bedroom_averages mba
    ON mba.market_id = tp.market_id
    AND mba.bedrooms = tp.bedrooms
ORDER BY
    m.name,
    tp.bedrooms,
    tp.revenue_rank;


-- Window Function Approach
SELECT
    m.name AS market_name,
    base.bedrooms AS bedroom_count,
    CONCAT(base.bedrooms, 'BR') AS bedroom_category,
    base.revenue_rank,
    base.external_property_id,
    base.property_title,

    -- Property Performance
    ROUND(base.revenue::numeric, 2) AS property_revenue,
    ROUND(base.occupancy::numeric, 4) AS property_occupancy,
    ROUND(base.adr::numeric, 2) AS property_adr,

    -- Market Averages (calculated via window functions)
    ROUND(base.avg_revenue::numeric, 2) AS market_avg_revenue,
    ROUND(base.avg_occupancy::numeric, 4) AS market_avg_occupancy,
    ROUND(base.avg_adr::numeric, 2) AS market_avg_adr,

    -- Revenue Gap Analysis
    ROUND((base.revenue - base.avg_revenue)::numeric, 2) AS revenue_gap,
    ROUND(((base.revenue - base.avg_revenue) / NULLIF(base.avg_revenue, 0) * 100)::numeric, 2) AS revenue_gap_pct,

    -- Context
    base.property_count AS properties_in_category

FROM (
    SELECT
        p.id AS property_id,
        p.property_id AS external_property_id,
        p.title AS property_title,
        p.market_id,
        p.bedrooms,
        pp.revenue,
        pp.occupancy,
        pp.adr,

        -- Window function for ranking
        ROW_NUMBER() OVER (
            PARTITION BY p.market_id, p.bedrooms
            ORDER BY pp.revenue DESC NULLS LAST
        ) AS revenue_rank,

        -- Window functions for market averages per bedroom category
        AVG(pp.revenue) OVER (
            PARTITION BY p.market_id, p.bedrooms
        ) AS avg_revenue,

        AVG(pp.occupancy) OVER (
            PARTITION BY p.market_id, p.bedrooms
        ) AS avg_occupancy,

        AVG(pp.adr) OVER (
            PARTITION BY p.market_id, p.bedrooms
        ) AS avg_adr,

        COUNT(*) OVER (
            PARTITION BY p.market_id, p.bedrooms
        ) AS property_count

    FROM properties p
    INNER JOIN property_performance pp ON pp.property_id = p.id
    WHERE p.bedrooms IS NOT NULL
      AND pp.revenue IS NOT NULL
) base
INNER JOIN markets m ON m.id = base.market_id
WHERE base.revenue_rank <= 3
ORDER BY
    m.name,
    base.bedrooms,
    base.revenue_rank;
