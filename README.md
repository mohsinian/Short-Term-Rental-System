# Short-Term-Rental-System

A data pipeline system for managing short-term rental property data with optimized batch loading capabilities.

## Features

- **Data Cleaning**: Automated CSV data cleaning and normalization
- **Database Management**: Supabase/PostgreSQL with migration support and schema versioning
- **Optimized Loading**: High-performance batch loading
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

## Documentation
- [Quick Start Guide](docs/QUICK_START_BATCH_LOADING.md) - Quick reference for batch loading

## Project Structure

```
.
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
│   ├── build.sh
│   ├── migrate.sh
│   ├── pipeline.sh                # Pipeline runner
│   └── run.sh
├── src/                          # Source code
│   └── database/                 # Database utilities
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── sample.env
```

## Database Schema

The system uses a normalized schema with the following tables:

- **markets**: Geographic markets
- **hosts**: Property managers/hosts
- **properties**: Property details and attributes
- **property_amenities**: Amenity data (JSONB)
- **property_performance**: Financial and review metrics

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