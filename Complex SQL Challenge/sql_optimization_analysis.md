# SQL Optimization Analysis: CTE vs Window Function Approaches

## Overview

This document analyzes two SQL query approaches for identifying top-performing rental properties within each market and bedroom category, comparing them against market averages.

**Business Goal:** Find the top 3 properties by revenue for each market/bedroom combination and calculate their performance gap versus market averages.

---

## Query Approaches

### 1. CTE (Common Table Expression) Approach

The CTE approach breaks down the problem into three logical steps:

```sql
WITH market_bedroom_averages AS (
    -- Step 1: Calculate average metrics per market and bedroom count
    SELECT market_id, bedrooms, AVG(revenue), AVG(occupancy), AVG(adr), COUNT(*)
    FROM properties p
    INNER JOIN property_performance pp ON pp.property_id = p.id
    WHERE p.bedrooms IS NOT NULL AND pp.revenue IS NOT NULL
    GROUP BY p.market_id, p.bedrooms
),
property_rankings AS (
    -- Step 2: Rank properties by revenue within each market/bedroom category
    SELECT ..., ROW_NUMBER() OVER (PARTITION BY market_id, bedrooms ORDER BY revenue DESC)
    FROM properties p
    INNER JOIN property_performance pp ON pp.property_id = p.id
),
top_properties AS (
    -- Step 3: Filter to top 3 per market/bedroom
    SELECT * FROM property_rankings WHERE revenue_rank <= 3
)
-- Final: Join top properties with market averages
SELECT ... FROM top_properties tp
INNER JOIN markets m ON m.id = tp.market_id
INNER JOIN market_bedroom_averages mba ON mba.market_id = tp.market_id AND mba.bedrooms = tp.bedrooms
```

**Characteristics:**
- Separates concerns into distinct CTEs
- Scans `properties` and `property_performance` tables **twice** (once for averages, once for rankings)
- Explicit, step-by-step logic

---

### 2. Window Function Approach

The Window Function approach calculates everything in a single pass:

```sql
SELECT ... FROM (
    SELECT
        p.*, pp.*,
        ROW_NUMBER() OVER (PARTITION BY market_id, bedrooms ORDER BY revenue DESC) AS revenue_rank,
        AVG(revenue) OVER (PARTITION BY market_id, bedrooms) AS avg_revenue,
        AVG(occupancy) OVER (PARTITION BY market_id, bedrooms) AS avg_occupancy,
        AVG(adr) OVER (PARTITION BY market_id, bedrooms) AS avg_adr,
        COUNT(*) OVER (PARTITION BY market_id, bedrooms) AS property_count
    FROM properties p
    INNER JOIN property_performance pp ON pp.property_id = p.id
    WHERE p.bedrooms IS NOT NULL AND pp.revenue IS NOT NULL
) base
INNER JOIN markets m ON m.id = base.market_id
WHERE base.revenue_rank <= 3
```

**Characteristics:**
- Single scan of `properties` and `property_performance` tables
- Computes ranking and averages simultaneously using window functions
- More compact query structure

---

## EXPLAIN ANALYZE Results

### CTE Approach Execution Plan

```
Incremental Sort  (cost=754.59..829.60 rows=61 width=890) (actual time=10.291..10.373 rows=76 loops=1)
  Sort Key: m.name, p.bedrooms, (row_number() OVER (?))
  Presorted Key: m.name
  Full-sort Groups: 2  Sort Method: quicksort  Average Memory: 33kB  Peak Memory: 33kB
  ->  Nested Loop  (cost=739.76..827.70 rows=61 width=890) (actual time=9.722..10.258 rows=76 loops=1)
        Join Filter: (m.id = p.market_id)
        Rows Removed by Join Filter: 152
        ->  Index Scan using idx_markets_name_state_unique on markets m  (cost=0.13..3.52 rows=6 width=532)
        ->  Materialize  (cost=739.63..816.70 rows=61 width=237) (actual time=3.066..3.327 rows=76 loops=3)
              ->  Merge Join  (cost=739.63..816.40 rows=61 width=237) (actual time=9.193..9.917 rows=76 loops=1)
                    Merge Cond: ((p.market_id = mba.market_id) AND (p.bedrooms = mba.bedrooms))
                    ->  WindowAgg  (cost=409.37..454.91 rows=2025 width=133) (actual time=5.909..6.594 rows=76 loops=1)
                          Run Condition: (row_number() OVER (?) <= 3)
                          ->  Sort  (cost=409.35..414.41 rows=2025 width=109) (actual time=5.896..6.160 rows=2025 loops=1)
                                Sort Key: p.market_id, p.bedrooms, pp.revenue DESC NULLS LAST
                                Sort Method: quicksort  Memory: 308kB
                                ->  Hash Join  (cost=80.56..298.14 rows=2025 width=109)
                                      ->  Seq Scan on properties p  (rows=2025)
                                      ->  Hash  (cost=55.25..55.25)
                                            ->  Seq Scan on property_performance pp  (rows=2025)
                    ->  Sort  (cost=330.25..330.34 rows=33 width=125) (actual time=3.277..3.281 rows=29 loops=1)
                          Sort Key: mba.market_id, mba.bedrooms
                          Sort Method: quicksort  Memory: 27kB
                          ->  Subquery Scan on mba  (cost=328.51..329.42 rows=33 width=125)
                                ->  HashAggregate  (cost=328.51..329.09 rows=33 width=125)
                                      Group Key: p_1.market_id, p_1.bedrooms
                                      ->  Hash Join  (cost=80.56..298.14 rows=2025 width=44)
                                            ->  Seq Scan on properties p_1  (rows=2025)  -- SECOND SCAN
                                            ->  Seq Scan on property_performance pp_1  (rows=2025)  -- SECOND SCAN

Planning Time: 1.938 ms
Execution Time: 10.713 ms
```

**Key Observations:**
- **Execution Time: 10.713 ms**
- Planning Time: 1.938 ms
- Uses **Incremental Sort** with presorted key optimization
- **Two separate scans** of `properties` and `property_performance` tables
- Uses Index Scan on markets table
- Merge Join for combining rankings with averages

---

### Window Function Approach Execution Plan

```
Sort  (cost=718.08..723.15 rows=2025 width=890) (actual time=10.476..10.484 rows=76 loops=1)
  Sort Key: m.name, p.bedrooms, (row_number() OVER (?))
  Sort Method: quicksort  Memory: 38kB
  ->  Hash Join  (cost=413.36..606.87 rows=2025 width=890) (actual time=6.818..10.259 rows=76 loops=1)
        Hash Cond: (p.market_id = m.id)
        ->  WindowAgg  (cost=412.22..505.54 rows=2025 width=237) (actual time=6.734..10.033 rows=76 loops=1)
              Filter: ((row_number() OVER (?)) <= 3)
              Rows Removed by Filter: 1949
              ->  WindowAgg  (cost=409.37..454.91 rows=2025 width=117) (actual time=6.664..7.830 rows=2025 loops=1)
                    Run Condition: (row_number() OVER (?) <= 3)
                    ->  Sort  (cost=409.35..414.41 rows=2025 width=109) (actual time=6.651..6.836 rows=2025 loops=1)
                          Sort Key: p.market_id, p.bedrooms, pp.revenue DESC NULLS LAST
                          Sort Method: quicksort  Memory: 308kB
                          ->  Hash Join  (cost=80.56..298.14 rows=2025 width=109) (actual time=0.959..2.599 rows=2025 loops=1)
                                Hash Cond: (p.id = pp.property_id)
                                ->  Seq Scan on properties p  (rows=2025)  -- SINGLE SCAN
                                ->  Hash  (cost=55.25..55.25)
                                      ->  Seq Scan on property_performance pp  (rows=2025)  -- SINGLE SCAN
        ->  Hash  (cost=1.06..1.06 rows=6 width=532) (actual time=0.028..0.028 rows=3 loops=1)
              ->  Seq Scan on markets m  (rows=3)

Planning Time: 1.679 ms
Execution Time: 10.726 ms
```

**Key Observations:**
- **Execution Time: 10.726 ms**
- Planning Time: 1.679 ms
- **Single scan** of `properties` and `property_performance` tables
- Two WindowAgg operations (one for ranking, one for averages)
- Hash Join for markets table

---

## Performance Comparison

| Metric | CTE Approach | Window Function Approach |
|--------|--------------|--------------------------|
| **Execution Time** | 10.713 ms | 10.726 ms |
| **Planning Time** | 1.938 ms | 1.679 ms |
| **Total Time** | 12.651 ms | 12.405 ms |
| **Table Scans** | 2x (properties, property_performance) | 1x (properties, property_performance) |
| **Memory (Sort)** | 308kB + 27kB + 33kB | 308kB + 38kB |
| **Estimated Cost** | 754.59..829.60 | 718.08..723.15 |

### Performance Analysis

1. **Current Dataset (2,025 rows):** Both approaches perform nearly identically (~10.7 ms)

2. **Scalability Considerations:**
   - **CTE Approach:** Scans base tables twice, which becomes more expensive as data grows
   - **Window Function Approach:** Single scan makes it more scalable for larger datasets

3. **Estimated Cost:** Window Function approach has a lower estimated cost (718 vs 754), indicating the optimizer considers it more efficient

---

## Readability Comparison

### CTE Approach ✅ More Readable

**Pros:**
- Clear separation of concerns (averages → rankings → filtering → final join)
- Each CTE has a single responsibility
- Easier to debug individual steps
- Self-documenting with named CTEs
- Easier for team members to understand and modify

**Cons:**
- More verbose
- Requires understanding of how CTEs chain together

### Window Function Approach

**Pros:**
- More compact code
- Single logical unit
- No need to trace through multiple CTEs

**Cons:**
- Dense subquery with multiple window functions
- Harder to debug individual calculations
- Less intuitive for developers unfamiliar with window functions

---

## Maintainability Comparison

| Factor | CTE Approach | Window Function Approach |
|--------|--------------|--------------------------|
| **Adding new metrics** | Add to specific CTE | Modify complex subquery |
| **Changing filter logic** | Modify `top_properties` CTE | Modify WHERE clause |
| **Debugging** | Test each CTE independently | Must trace through entire query |
| **Code reviews** | Easier to review step-by-step | Requires careful attention |
| **Onboarding new developers** | Self-explanatory structure | Steeper learning curve |

---

## Recommendation

### 🏆 Recommended: **CTE Approach**

**Primary Reasons:**

1. **Readability (High Priority):** The CTE approach clearly separates:
   - Market average calculations
   - Property ranking logic
   - Top-N filtering
   - Final result assembly
   
   This makes code reviews, debugging, and knowledge transfer significantly easier.

2. **Maintainability:** When business requirements change (e.g., "show top 5 instead of top 3" or "add new metrics"), modifications are isolated to specific CTEs without risk of breaking other parts.

3. **Performance Trade-off is Minimal:** 
   - At current scale (2,025 rows), the difference is **0.013 ms** (negligible)
   - The theoretical advantage of single-scan in the Window approach only matters at much larger scales
   - Modern PostgreSQL optimizers may even inline CTEs when beneficial

4. **Team Collaboration:** The explicit, step-by-step nature of CTEs makes it easier for:
   - New team members to understand the logic
   - Code reviewers to verify correctness
   - Future developers to extend functionality

### When to Choose Window Function Approach

Consider the Window Function approach if:
- Dataset grows to **millions of rows** where double-scanning becomes costly
- Query is a one-time analysis (not maintained long-term)
- Team is highly experienced with window functions
- Memory constraints require minimizing intermediate result sets

---

## Conclusion

Both queries produce identical results and perform similarly on the current dataset. The **CTE approach is recommended** for production use due to its superior readability and maintainability, which reduces long-term development costs and bugs. The minor theoretical performance advantage of the Window Function approach does not justify the increased complexity for this use case.

If performance becomes a concern at scale, consider:
1. Adding appropriate indexes on `(market_id, bedrooms)` and `(property_id)`
2. Materializing the market averages if they're queried frequently
3. Re-evaluating the Window Function approach with actual performance metrics on larger data
