# Short-Term-Rental-System

A data pipeline system for managing short-term rental property data with optimized batch loading capabilities.

## Features

- **Data Cleaning**: Automated CSV data cleaning and normalization
- **Database Management**: Supabase/PostgreSQL with migration support and schema versioning
- **Optimized Loading**: High-performance batch loading
- **Property Scoring**: Investment opportunity scoring with 8-component analysis
- **FastAPI Backend**: RESTful API for querying property data, market analysis, and investment scores
- **Streamlit Dashboard**: Interactive web interface for visualizing property data and investment opportunities
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

## Frontend Dashboard

The system includes a Streamlit-based web dashboard for visualizing property data and investment opportunities.

### Running the Frontend

#### Using Docker Compose

**Start all services (pipeline + api + frontend):**
```bash
docker-compose up -d
```

**Start frontend only:**
```bash
docker-compose up -d frontend
```

#### Using Interactive CLI

Run the interactive CLI and select the frontend service from the menu:
```bash
./scripts/cli.sh
```

### Accessing the Dashboard

Once the frontend service is running, access the dashboard at:
- **Dashboard URL**: http://localhost:8501

### Dashboard Features

The Streamlit dashboard provides three main views:

#### 🏠 Properties Tab
- Browse all properties with filtering and sorting
- Filter by market, bedrooms, revenue, occupancy, rating, and more
- Paginated results for easy navigation
- Property cards showing key metrics (bedrooms, bathrooms, revenue, occupancy)

#### 🏆 Top Opportunities Tab
- View top 15 investment opportunities ranked by total score
- Interactive bar chart showing property scores
- Detailed table with property metrics
- Opportunity tier classification (PLATINUM, GOLD, SILVER, BRONZE)

#### 📊 Insights Tab
- **Revenue by Bedroom Count**: Bar chart showing average revenue per bedroom count
- **Opportunity Tiers**: Pie chart showing distribution of investment opportunity tiers
- **Score Distribution**: Histogram showing the distribution of investment scores

### Dashboard Filters

The sidebar provides comprehensive filtering options:
- **Market Selection**: Filter by geographic market
- **Bedrooms**: Minimum and maximum bedroom count
- **Revenue**: Minimum and maximum revenue range
- **Occupancy**: Minimum and maximum occupancy percentage
- **Rating**: Minimum rating threshold
- **Property Status**: Guest favorite and reliable data filters
- **Sorting**: Sort by title, bedrooms, bathrooms, accommodates, or date

### Building the Frontend

**Build frontend service only:**
```bash
./scripts/build.sh frontend
```

**Build all services:**
```bash
./scripts/build.sh all
```

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
├── api/                           # FastAPI backend (Production Ready)
│   ├── __init__.py
│   ├── main.py                    # FastAPI application
│   ├── models.py                  # Pydantic models
│   ├── database.py                 # Database query functions
│   ├── Dockerfile                  # API Docker configuration (Production)
│   ├── requirements.txt            # API-only dependencies
│   └── routes/                    # API route handlers
│       ├── __init__.py
│       ├── health.py               # Health check endpoint
│       ├── markets.py              # Market endpoints
│       ├── properties.py           # Property endpoints
│       ├── investment_scores.py    # Investment score endpoints
│       └── insights.py            # Insights and top performers endpoints
├── frontend/                      # Streamlit Dashboard (Web UI)
│   ├── __init__.py
│   ├── app.py                     # Streamlit application
│   ├── Dockerfile                 # Frontend Docker configuration
│   └── requirements.txt           # Frontend dependencies
├── data/                          # Raw and cleaned CSV files
├── docs/                          # Documentation
│   ├── BATCH_LOADING_OPTIMIZATION.md
│   └── QUICK_START_BATCH_LOADING.md
├── migrations/                     # Database migrations
│   ├── 001_initial_schema.sql
│   └── 002_add_market_uniqueness.sql
├── pipeline/                      # Data processing scripts (Local Only)
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
├── Dockerfile                     # Pipeline Docker configuration (Local Development Only)
├── docker-compose.yml              # Docker Compose configuration
├── .dockerignore                  # Docker build exclusions
├── requirements.txt               # All Python dependencies (API + Pipeline)
└── sample.env                    # Environment variables template
```

## Docker Deployment

### Architecture Overview

The project uses a multi-service Docker setup for optimized deployment:

- **API Service** ([`api/Dockerfile`](api/Dockerfile:1)): Production-ready FastAPI backend
  - Uses [`api/requirements.txt`](api/requirements.txt:1) with minimal dependencies
  - Optimized for cloud deployment
  - No pipeline dependencies (pandas, numpy) for smaller image size
  - Deployed to cloud infrastructure

- **Frontend Service** ([`frontend/Dockerfile`](frontend/Dockerfile:1)): Streamlit dashboard
  - Uses [`frontend/requirements.txt`](frontend/requirements.txt:1) with Streamlit and visualization libraries
  - Provides interactive web interface for property data and investment insights
  - Communicates with API service for data
  - Can be deployed alongside API

- **Pipeline Service** ([`Dockerfile`](Dockerfile:1)): Local development only
  - Uses [`requirements.txt`](requirements.txt:1) with all dependencies
  - Includes pipeline dependencies (pandas, numpy)
  - Used locally for data processing and ETL
  - NOT deployed to cloud

### Production Deployment (API Only)

For cloud deployment, only the API service is deployed:

```bash
# Build API image
docker build -f api/Dockerfile -t short-term-rental-api:latest .

# Run API container
docker run -d \
  --name short-term-rental-api \
  -p 8000:8000 \
  --env-file .env \
  --restart unless-stopped \
  short-term-rental-api:latest
```

### Local Development

For local development with both services:

```bash
# Build all services
./scripts/build.sh all

# Start all services
./scripts/run.sh all detached

# Or use docker-compose directly
docker-compose up -d
```

### Key Differences

| Feature | API Service | Frontend Service | Pipeline Service |
|---------|-------------|------------------|------------------|
| Deployment | Cloud & Local | Cloud & Local | Local Only |
| Dependencies | API-only (fastapi, uvicorn, pydantic, psycopg2) | Streamlit + visualization (streamlit, plotly, pandas, requests) | All (API + pandas, numpy) |
| Dockerfile | [`api/Dockerfile`](api/Dockerfile:1) | [`frontend/Dockerfile`](frontend/Dockerfile:1) | [`Dockerfile`](Dockerfile:1) |
| Requirements | [`api/requirements.txt`](api/requirements.txt:1) | [`frontend/requirements.txt`](frontend/requirements.txt:1) | [`requirements.txt`](requirements.txt:1) |
| Image Size | Smaller (~100MB) | Medium (~200MB) | Larger (~500MB) |
| Use Case | Production API | Web Dashboard | Data processing & ETL |

### Health Checks

The API service includes health checks:

```bash
curl http://localhost:8000/api/v1/health
```

The frontend service also includes health checks:

```bash
curl http://localhost:8501/_stcore/health
```

Health check configuration in [`docker-compose.yml`](docker-compose.yml:1):
- Interval: 30 seconds
- Timeout: 10 seconds
- Retries: 3
- Start period: 40 seconds

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