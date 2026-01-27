# Property Investment Scoring System

## Overview

The Property Investment Scoring System evaluates short-term rental properties to identify top investment opportunities. It uses a multi-component scoring algorithm that analyzes financial performance, guest satisfaction, amenities, and market factors.

## Scoring Components

The scoring system evaluates properties across 8 weighted components:

| Component | Weight | Description |
|------------|---------|-------------|
| Revenue Performance | 25% | Revenue vs market average for same bedroom count |
| Occupancy Consistency | 15% | How well the property maintains bookings |
| ADR Positioning | 15% | Average Daily Rate optimization |
| Review Score | 15% | Review volume and ratings combined |
| Amenity Value | 10% | High-value amenities that correlate with revenue |
| Host Status | 5% | Superhost and guest favorite indicators |
| Seasonal Stability | 10% | Consistency across seasons |
| Market Strength | 5% | Overall market performance indicators |

## Component Details

### 1. Revenue Performance (25%)

**Scoring Logic:**
- At market average = 50 points
- Top performer (2x average) = 100 points
- Below average scaled down from 50

**Formula:**
```
ratio = property_revenue / market_avg_revenue

if ratio >= 2.0:
    score = 100.0
elif ratio >= 1.0:
    score = 50.0 + (ratio - 1.0) * 50.0
else:
    score = ratio * 50.0
```

### 2. Occupancy Consistency (15%)

**Scoring Logic:**
- 80%+ occupancy = 100 points (exceptional)
- 70%+ = 90 points (excellent)
- 60%+ = 75 points (good)
- 50%+ = 60 points (average)
- Below 50% scaled down

**Formula:**
```
if occupancy >= 0.80:
    score = 100.0
elif occupancy >= 0.70:
    score = 90.0 + (occupancy - 0.70) * 100.0
elif occupancy >= 0.60:
    score = 75.0 + (occupancy - 0.60) * 150.0
elif occupancy >= 0.50:
    score = 60.0 + (occupancy - 0.50) * 150.0
else:
    score = occupancy * 120.0
```

### 3. ADR Positioning (15%)

**Scoring Logic:**
- High ADR with good occupancy = optimal pricing
- High ADR with low occupancy = potentially overpriced
- Low ADR with high occupancy = potential upside opportunity

**Formula:**
```
adr_ratio = property_adr / market_avg_adr

# Base score from ADR ratio
if adr_ratio >= 1.5:
    base_score = 100.0
elif adr_ratio >= 1.0:
    base_score = 70.0 + (adr_ratio - 1.0) * 60.0
else:
    base_score = adr_ratio * 70.0

# Adjust based on occupancy
if adr_ratio >= 1.0 and occupancy >= 0.60:
    # Bonus for maintaining high rates with good occupancy
    base_score = min(100.0, base_score * (1 + (occupancy - 0.60) * 0.25))
elif adr_ratio < 0.8 and occupancy >= 0.70:
    # Opportunity flag: underpriced but high demand
    base_score = min(100.0, base_score * 1.15)
```

### 4. Review Score (15%)

**Components:**
- Rating quality (60% weight)
- Review velocity (40% weight)

**Rating Scoring:**
```
if rating >= 4.9:
    rating_score = 100.0
elif rating >= 4.7:
    rating_score = 90.0
elif rating >= 4.5:
    rating_score = 75.0
elif rating >= 4.0:
    rating_score = 50.0
else:
    rating_score = rating * 12.5
```

**Review Velocity Scoring:**
```
if avg_reviews_per_month >= 10:
    velocity_score = 100.0
elif avg_reviews_per_month >= 5:
    velocity_score = 80.0 + (avg_reviews_per_month - 5) * 4.0
elif avg_reviews_per_month >= 2:
    velocity_score = 50.0 + (avg_reviews_per_month - 2) * 10.0
else:
    velocity_score = avg_reviews_per_month * 25.0
```

**Total Review Score:**
```
total_score = rating_score * 0.6 + velocity_score * 0.4
```

### 5. Amenity Value (10%)

**Tiered Amenity System:**

| Tier | Points | Amenities |
|-------|---------|------------|
| Tier 1 | 20 pts | Pool, Hot Tub, Jacuzzi, Sauna |
| Tier 2 | 15 pts | Game Room, Arcade, Pool Table, Theater |
| Tier 3 | 10 pts | Fire Pit, Grill, BBQ, EV Charger |
| Tier 4 | 8 pts | Gym, Exercise, View, Waterfront, Beach |
| Tier 5 | 5 pts | Crib, Pack n Play, High Chair, Playground |

**Formula:**
```
total_points = sum of tier points for amenities present
max_possible = 20 + 15 + 10 + 8 + 5 = 58

score = min(100.0, (total_points / max_possible) * 150.0 + 30.0)
```

### 6. Host Status (5%)

**Scoring Logic:**
- Superhost: +35 points
- Guest Favorite: +35 points
- Neither: 30 points (base)

**Formula:**
```
score = 30.0
if is_superhost:
    score += 35.0
if is_guest_favorite:
    score += 35.0
score = min(100.0, score)
```

### 7. Seasonal Stability (10%)

**Components:**
- Consistency (50%): Active months ratio
- Distribution (50%): High season review ratio

**Consistency Scoring:**
```
active_ratio = (total_months - missing_months) / total_months
consistency_score = active_ratio * 100.0
```

**Distribution Scoring:**
```
high_season_ratio = high_season_reviews / total_reviews

if 0.20 <= high_season_ratio <= 0.45:
    distribution_score = 100.0  # Well-distributed
elif high_season_ratio > 0.45:
    distribution_score = 100.0 - (high_season_ratio - 0.45) * 150.0  # Too dependent on high season
else:
    distribution_score = high_season_ratio * 500.0  # Underperforming in high season
```

**Total Seasonal Score:**
```
score = consistency_score * 0.5 + max(0.0, distribution_score) * 0.5
```

### 8. Market Strength (5%)

**Components:**
- Market occupancy health (40%)
- Market revenue health (40%)
- Market maturity (20%)

**Occupancy Health:**
```
if market_avg_occupancy >= 0.70:
    occ_score = 100.0
elif market_avg_occupancy >= 0.60:
    occ_score = 80.0
elif market_avg_occupancy >= 0.50:
    occ_score = 60.0
else:
    occ_score = market_avg_occupancy * 120.0
```

**Revenue Health:**
```
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
```

**Maturity:**
```
if property_count >= 50:
    maturity_score = 100.0
elif property_count >= 20:
    maturity_score = 70.0
elif property_count >= 10:
    maturity_score = 50.0
else:
    maturity_score = property_count * 5.0
```

**Total Market Score:**
```
score = (occ_score * 0.4 + rev_score * 0.4 + maturity_score * 0.2) / components
```

## Opportunity Tiers

Properties are assigned to investment opportunity tiers based on total score and percentile rank:

| Tier | Criteria | Description |
|-------|-----------|-------------|
| PLATINUM | Top 5% OR score ≥ 85 | Exceptional investment opportunities |
| GOLD | Top 15% OR score ≥ 75 | Strong investment opportunities |
| SILVER | Top 35% OR score ≥ 60 | Good investment opportunities |
| BRONZE | Everything else | Standard properties |

**Top Opportunity Flag:**
- Properties marked as `is_top_opportunity` if they are in PLATINUM or GOLD tier

## Usage

### Running Scoring

**Via CLI:**
```bash
# Interactive menu option 4: Run property scoring only
./scripts/cli.sh

# Interactive menu option 7: Run full pipeline with scoring
./scripts/cli.sh
```

**Via Pipeline Script:**
```bash
# Score only (requires data to be loaded)
./scripts/pipeline.sh score

# Score with limit for testing
./scripts/pipeline.sh score --limit 10

# Run full pipeline with scoring (clean + load + score)
./scripts/pipeline.sh run --score
```

**Via Command Line (direct Python):**
```bash
# Score only (requires data to be loaded)
python pipeline/run_pipeline.py --score-only

# Score with limit for testing
python pipeline/run_pipeline.py --score-only --limit 10

# Run full pipeline with scoring
python pipeline/run_pipeline.py --score

# Full pipeline with scoring and limit
python pipeline/run_pipeline.py --score --limit 50
```

### Querying Scores

**Get Top Opportunities:**
```python
from pipeline.score_properties import get_top_opportunities

# Get top 20 opportunities
top_ops = get_top_opportunities(limit=20)

for op in top_ops:
    print(f"{op['external_id']}: {op['title']}")
    print(f"  Score: {op['total_score']} | Tier: {op['opportunity_tier']}")
```

**Get Undervalued Opportunities:**
```python
from pipeline.score_properties import get_undervalued_opportunities

# Find undervalued properties
undervalued = get_undervalued_opportunities(limit=10)

for op in undervalued:
    print(f"{op['external_id']}: {op['title']}")
    print(f"  Quality: {op['quality_avg']:.1f} vs Revenue: {op['revenue_performance']}")
```

## Database Schema

### property_investment_scores Table

| Column | Type | Description |
|---------|--------|-------------|
| id | UUID | Primary key |
| property_id | UUID | Foreign key to properties |
| revenue_score | NUMERIC | Revenue performance score (0-100) |
| occupancy_score | NUMERIC | Occupancy consistency score (0-100) |
| adr_score | NUMERIC | ADR positioning score (0-100) |
| review_score | NUMERIC | Review score (0-100) |
| amenity_score | NUMERIC | Amenity value score (0-100) |
| host_score | NUMERIC | Host status score (0-100) |
| seasonal_score | NUMERIC | Seasonal stability score (0-100) |
| market_score | NUMERIC | Market strength score (0-100) |
| total_score | NUMERIC | Weighted composite score (0-100) |
| percentile_rank | NUMERIC | Percentile rank within market (0-100) |
| is_top_opportunity | BOOLEAN | Flag for top opportunities |
| opportunity_tier | VARCHAR(20) | Investment tier (PLATINUM/GOLD/SILVER/BRONZE) |
| scoring_version | VARCHAR(20) | Scoring algorithm version |
| calculated_at | TIMESTAMPTZ | Calculation timestamp |

## Customization

### Adjusting Weights

You can customize the scoring weights by modifying the `ScoringWeights` dataclass:

```python
from pipeline.score_properties import InvestmentScorer, ScoringWeights

# Custom weights
custom_weights = ScoringWeights(
    revenue=0.30,      # Increase revenue importance
    occupancy=0.20,    # Increase occupancy importance
    adr=0.10,          # Decrease ADR importance
    review=0.15,
    amenity=0.10,
    host=0.05,
    seasonal=0.05,
    market=0.05
)

# Use custom weights
scorer = InvestmentScorer(weights=custom_weights)
scorer.run()
```

### Adding Custom Amenities

To add or modify high-value amenities, edit the `HIGH_VALUE_AMENITIES` dictionary in `pipeline/score_properties.py`:

```python
HIGH_VALUE_AMENITIES = {
    'tier_1': {
        'amenities': ['pool', 'hot tub', 'hot_tub', 'jacuzzi', 'sauna'],
        'weight': 20
    },
    # Add your custom tiers here
    'tier_custom': {
        'amenities': ['your', 'custom', 'amenities'],
        'weight': 25
    }
}
```

## Troubleshooting

### No Properties Scored

**Problem:** "Found 0 properties to score"

**Solutions:**
1. Ensure data has been loaded into the database
2. Check that `is_reliable_data` flag is TRUE for properties
3. Verify property_performance data exists for properties

### Low Scores Across Board

**Problem:** All properties have low scores

**Solutions:**
1. Check market benchmarks are calculated correctly
2. Verify performance data is accurate
3. Review amenity parsing (may need adjustment)
4. Consider adjusting weights for your market

### Scoring Takes Too Long

**Problem:** Scoring process is slow

**Solutions:**
1. Use `--limit` flag to test with subset
2. Add indexes to database tables
3. Consider batch processing for large datasets

## Best Practices

1. **Run After Data Loading**: Always run scoring after loading fresh data
2. **Regular Updates**: Re-score periodically as performance data changes
3. **Review Outliers**: Investigate properties with extreme scores
4. **Market Context**: Consider tier thresholds for different markets
5. **Customize Weights**: Adjust weights based on investment strategy

## References

- Migration: `migrations/007_create_table_property_investment_scores.sql`
- Scoring Module: `pipeline/score_properties.py`
- Pipeline Integration: `pipeline/run_pipeline.py`
