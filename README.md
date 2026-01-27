# Short-Term-Rental-System

A data pipeline system for managing short-term rental property data with optimized batch loading capabilities.

## Features

- **Data Cleaning**: Automated CSV data cleaning and normalization
- **Database Management**: Supabase/PostgreSQL with migration support and schema versioning
- **Optimized Loading**: High-performance batch loading
- **Property Scoring**: Investment opportunity scoring with 8-component analysis
- **FastAPI Backend**: RESTful API for querying property data, market analysis, and investment scores
- **Docker Support**: Containerized environment for easy deployment

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Supabase project with database credentials
- Python 3.12+ (if running locally)

### Setup

1. Clone the repository
2. Copy `sample.env` to `.env` and configure your credentials:
   ```bash
   cp sample.env .env
   ```
3. Edit `.env` with your Supabase credentials:
   ```bash
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_SECRET_KEY=your-service-role-key
   SUPABASE_DB_CONNECTION_STRING=postgresql://postgres.xxxxx:password@aws-0-us-east-1.pooler.supabase.com:6543/postgres
   ```

### Interactive CLI (Recommended)

The easiest way to use this system is through the interactive CLI tool:

```bash
./scripts/cli.sh
```

This will launch an interactive menu where you can:
- 🗄️ Run database migrations (run, status, dry-run, test connection)
- 📊 Run the data pipeline (full, clean only, load only, batch mode)
- 🌐 Manage API service (start, stop, restart, logs, health check, open docs)
- 🏗️ Build Docker images
- 📈 Check system status
- 🐳 Manage Docker containers

The CLI provides a user-friendly interface with prompts for options like limits and batch sizes.

## API Integration

The system includes a FastAPI backend that provides RESTful endpoints for querying property data, market analysis, and investment scores.

### Health Check

Check if the API is running:

```bash
curl http://localhost:8000/api/v1/health
```

Response:
```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2024-01-27T22:00:00.000Z",
  "version": "1.0.0"
}
```

### Running the API

#### Using Scripts

**Start API service only:**
```bash
./scripts/run.sh api detached
```

**Start all services (pipeline + api):**
```bash
./scripts/run.sh all detached
```

#### Using Docker Compose

**Start API in background:**
```bash
docker-compose up -d api
```

**Start all services in background:**
```bash
docker-compose up -d
```

#### Using Interactive CLI

Run the interactive CLI and select "🌐 API Service" from the menu:
```bash
./scripts/cli.sh
```

From the API Service menu, you can:
- Start/Stop/Restart API service
- View API logs
- Check API health
- Open API documentation in browser

### API Endpoints

Once the API is running, access it at:
- **API Base URL**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs (Swagger UI)
- **Alternative Docs**: http://localhost:8000/redoc (ReDoc)

Available endpoints include:
- `/api/v1/health` - Health check
- `/api/v1/markets` - Market data endpoints
- `/api/v1/properties` - Property data endpoints
- `/api/v1/investment-scores` - Investment score endpoints

### Building the API

**Build API service only:**
```bash
./scripts/build.sh api
```

**Build all services:**
```bash
./scripts/build.sh all
```

### Running the Pipeline

#### Standard Mode (Row-by-Row)
```bash
# Run full pipeline (clean + load)
./scripts/pipeline.sh run

# Run only data loading
./scripts/pipeline.sh load
```

#### Batch Mode (Recommended - 100-1000x Faster!)
```bash
# Run full pipeline with batch loading
./scripts/pipeline.sh batch

# Run only data loading with batch mode
./scripts/pipeline.sh batch-load

# Test with limited records
./scripts/pipeline.sh batch-load --limit 50
```

#### Property Scoring
```bash
# Run scoring only (requires data to be loaded)
./scripts/pipeline.sh score

# Score with limit for testing
./scripts/pipeline.sh score --limit 10

# Run full pipeline with scoring (clean + load + score)
./scripts/pipeline.sh run --score
```

## Documentation
- [Interactive CLI Guide](docs/CLI_GUIDE.md) - Complete guide for using the interactive CLI tool
- [Quick Start Guide](docs/QUICK_START_BATCH_LOADING.md) - Quick reference for batch loading

## Project Structure

```
.
├── api/                           # FastAPI backend
│   ├── __init__.py
│   ├── main.py                    # FastAPI application
│   ├── models.py                  # Pydantic models
│   ├── database.py                 # Database query functions
│   ├── Dockerfile                  # API Docker configuration
│   └── routes/                    # API route handlers
│       ├── __init__.py
│       ├── health.py               # Health check endpoint
│       ├── markets.py              # Market endpoints
│       ├── properties.py           # Property endpoints
│       └── investment_scores.py    # Investment score endpoints
├── data/                          # Raw and cleaned CSV files
├── docs/                          # Documentation
│   ├── BATCH_LOADING_OPTIMIZATION.md
│   └── QUICK_START_BATCH_LOADING.md
├── migrations/                     # Database migrations
│   ├── 001_initial_schema.sql
│   └── 002_add_market_uniqueness.sql
├── pipeline/                      # Data processing scripts
│   ├── batch_load_data.py          # Optimized batch loader (NEW!)
│   ├── clean_data.py               # Data cleaning
│   ├── load_data.py               # Original row-by-row loader
│   └── run_pipeline.py            # Pipeline orchestrator
├── scripts/                       # Shell scripts
│   ├── build.sh                  # Build Docker images
│   ├── cli.sh                    # Interactive CLI tool
│   ├── migrate.sh                # Database migrations
│   ├── pipeline.sh               # Pipeline runner
│   └── run.sh                   # Run Docker services
├── src/                          # Source code
│   └── database/                 # Database utilities
├── Dockerfile                     # Pipeline Docker configuration
├── docker-compose.yml              # Docker Compose configuration
├── requirements.txt               # Python dependencies
└── sample.env                    # Environment variables template
```

## Database Schema

The system uses a normalized schema with the following tables:

- **markets**: Geographic markets
- **hosts**: Property managers/hosts
- **properties**: Property details and attributes
- **property_amenities**: Amenity data (JSONB)
- **property_performance**: Financial and review metrics
- **property_investment_scores**: Calculated investment opportunity scores

## Development

### Building the Docker Image
```bash
./scripts/build.sh
```

### Running Migrations
```bash
./scripts/migrate.sh run
```

### Running Tests
```bash
# Test with limited data
./scripts/pipeline.sh batch-load --limit 10
```

## Property Scoring

The system includes an investment scoring feature that evaluates properties based on 8 components:

### Scoring Components

1. **Revenue Performance (25%)** - Revenue vs market average for same bedroom count
2. **Occupancy Consistency (15%)** - How well the property maintains bookings
3. **ADR Positioning (15%)** - Average Daily Rate optimization
4. **Review Score (15%)** - Review volume and ratings combined
5. **Amenity Value (10%)** - High-value amenities that correlate with revenue
6. **Host Status (5%)** - Superhost and guest favorite indicators
7. **Seasonal Stability (10%)** - Consistency across seasons
8. **Market Strength (5%)** - Overall market performance indicators

### Opportunity Tiers

- **PLATINUM**: Top 5% or score >= 85
- **GOLD**: Top 15% or score >= 75
- **SILVER**: Top 35% or score >= 60
- **BRONZE**: Everything else

### High-Value Amenities

The scoring system prioritizes amenities with proven revenue correlation:
- Tier 1 (20 pts): Pool, Hot Tub, Jacuzzi, Sauna
- Tier 2 (15 pts): Game Room, Arcade, Pool Table, Theater
- Tier 3 (10 pts): Fire Pit, Grill, BBQ, EV Charger
- Tier 4 (8 pts): Gym, Exercise, View, Waterfront, Beach
- Tier 5 (5 pts): Crib, Pack n Play, High Chair, Playground

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SUPABASE_URL` | Yes | Your Supabase project URL |
| `SUPABASE_SECRET_KEY` | Yes | Service role key for admin operations |
| `SUPABASE_DB_CONNECTION_STRING` | Optional* | PostgreSQL connection string for fastest loading |

*Optional but highly recommended for maximum performance

## Troubleshooting

### Batch Loading Falls Back to API

If you see "Falling back to Supabase batch insert API", it means `SUPABASE_DB_CONNECTION_STRING` is not configured. The batch loader will still work, just using the Supabase API instead of COPY command (still 10-100x faster than original).

### Connection Timeout

Reduce batch size:
```bash
python pipeline/run_pipeline.py --batch --batch-size 100
```

### Out of Memory

Reduce batch size or limit records:
```bash
python pipeline/run_pipeline.py --batch --batch-size 50 --limit 100
```