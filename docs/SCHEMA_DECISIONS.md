# Database Schema Decisions

## Overview

The schema is designed around **investment analysis** as the primary use case—enabling fast querying of property performance metrics and investment scores across multiple short-term rental markets.

---

## Core Design Principles

### 1. Normalized Reference Data, Denormalized Analytics

**Markets & Hosts** are normalized into separate tables to:
- Avoid data duplication (market names, host details)
- Enable referential integrity via foreign keys
- Support future expansion (e.g., market-level settings, host portfolios)

**Materialized Views** (`mv_properties_with_scores`, `mv_property_analysis`, `mv_top_performers`) denormalize data for read-heavy analytics:
- Pre-joined property + performance + scores in one query
- Market comparison percentages pre-calculated
- Refreshed on-demand, not real-time (acceptable for investment analysis)

### 2. Separation of Concerns by Update Frequency

| Table | Update Frequency | Rationale |
|-------|------------------|-----------|
| `properties` | Rare (listing changes) | Core property attributes rarely change |
| `property_performance` | Weekly/Monthly | Revenue, occupancy fluctuate with market |
| `property_investment_scores` | On-demand | Recalculated when scoring algorithm runs |
| `property_amenities` | Rare | Amenities parsed once during ingestion |
| `property_reviews` | Monthly | Review metrics aggregated periodically |

This separation allows **targeted updates** without locking related data.

### 3. UUID Primary Keys

All tables use `UUID` primary keys instead of auto-increment integers:
- **Supabase-native**: Works seamlessly with Supabase's architecture
- **Distributed-safe**: No conflicts when merging data from multiple sources
- **API-friendly**: Safe to expose in URLs without leaking sequence information

---

## Key Schema Decisions

### Properties Table: The Central Entity

```
properties → property_performance (1:1)
           → property_amenities (1:1)
           → property_reviews (1:1)
           → property_investment_scores (1:1)
           → market (N:1)
           → host (N:1)
```

**Why 1:1 relationships instead of embedding in properties?**
- **Selective loading**: API can fetch only what's needed (property list vs. full detail)
- **Independent updates**: Refresh performance data without touching property core
- **Schema evolution**: Add new metrics without altering the main table

### Market Benchmarks: Time-Series Ready

`market_benchmarks` stores aggregated metrics by `(market_id, bedroom_count, report_date)`:
- Enables **historical trend analysis** (how did 3BR properties perform last quarter?)
- Supports **bedroom-specific comparisons** (crucial for STR investment decisions)
- Composite unique constraint prevents duplicate entries

### Investment Scores: Versioned & Auditable

`property_investment_scores` includes:
- `scoring_version`: Track which algorithm version produced the score
- `calculated_at`: When the score was computed
- `percentile_rank` & `opportunity_tier`: Pre-computed for fast filtering

**Why not calculate on-the-fly?**
- Scoring involves complex weighted formulas across 8 dimensions
- Pre-computed scores enable instant filtering by tier/rank
- Versioning allows A/B testing of scoring algorithms

---

## Performance Optimizations

### Temp Tables for Bulk Operations

The schema includes temp table patterns (`hosts_temp`, `properties_temp`, etc.) with corresponding `upsert_*_from_temp()` functions:
- **Batch loading**: COPY command fills temp table → single upsert merges to main
- **99% faster** than row-by-row inserts (see `PERFORMANCE_OPTIMIZATION.md`)

### Strategic Indexing

```sql
-- Fast lookups by business identifiers
CREATE INDEX ON properties(property_id);
CREATE INDEX ON properties(market_id);

-- Score-based filtering (the most common query pattern)
CREATE INDEX ON property_investment_scores(total_score DESC);
CREATE INDEX ON property_investment_scores(opportunity_tier);
CREATE INDEX ON property_investment_scores(is_top_opportunity);
```

### Materialized Views with UNIQUE Indexes

All materialized views have `UNIQUE INDEX ON (id)` to enable `REFRESH MATERIALIZED VIEW CONCURRENTLY`—avoiding table locks during refresh.

---

## Trade-offs Accepted

| Decision | Trade-off | Justification |
|----------|-----------|---------------|
| 1:1 tables over embedded JSON | More JOINs | Queryable, indexable, type-safe |
| Materialized views | Stale data possible | Acceptable for daily investment reports |
| No soft deletes | Data loss on delete | Properties are archived externally; DB is for active listings |
| Single `amenities` JSONB column | Less queryable | Amenities vary wildly; structured parsing not worth the complexity |

---

## Schema Evolution Path

The schema is designed for these future extensions:
1. **Multi-source ingestion**: `property_id` is source-agnostic (Airbnb, VRBO, direct)
2. **User portfolios**: Add `user_properties` junction table
3. **Price predictions**: Add `property_price_history` time-series table
4. **Real-time alerts**: Trigger-based notifications on score changes
