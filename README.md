# Short-Term-Rental-System

A data pipeline system for managing short-term rental property data with optimized batch loading capabilities.

[![Watch the demo video](https://img.youtube.com/vi/k94K8_oZp7g/0.jpg)](https://youtu.be/k94K8_oZp7g)

## Prerequisites

- Docker and Docker Compose
- Supabase project with database credentials
- Python 3.12+ (if running locally)
- In project root, create a folder naming it “data” where you will put all your CSVs, proper naming format should be placeName_stateName.csv (e.g: Blue_Ridge_GA.csv or Indianapolis_IN.csv)

## Setup

### 1. Clone the repository

### 2. Configure Environment Variables

Copy `sample.env` to `.env` and configure your credentials:

```bash
cp sample.env .env
```

Edit `.env` with your Supabase credentials:

```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SECRET_KEY=your-service-role-key
SUPABASE_DB_CONNECTION_STRING=postgresql://postgres.[Project-Id]:[YOUR-PASSWORD]@aws-1-ap-south-1.pooler.supabase.com:5432/postgres
```

### 3. Run Database Migrations

```bash
./scripts/migrate.sh run
```

### 4. Build Docker Images

```bash
./scripts/build.sh all
```

## Configuration Options

| Variable | Required | Description |
|----------|----------|-------------|
| `SUPABASE_URL` | Yes | Your Supabase project URL |
| `SUPABASE_SECRET_KEY` | Yes | Service role key for admin operations |
| `SUPABASE_DB_CONNECTION_STRING` | Optional* | PostgreSQL connection string for fastest loading |

*Optional but highly recommended for maximum performance

## Running Services

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

### Using Docker Compose

**Start all services (pipeline + api + frontend):**
```bash
docker-compose up -d
```

**Start specific services:**
```bash
docker-compose up -d api
docker-compose up -d frontend
```

### Using Scripts

**Start API service:**
```bash
./scripts/run.sh api detached
```

**Start all services:**
```bash
./scripts/run.sh all detached
```

## Running the Data Pipeline

### Standard Mode (Row-by-Row)
```bash
# Run full pipeline (clean + load)
./scripts/pipeline.sh run

# Run only data loading
./scripts/pipeline.sh load
```

### Batch Mode (Recommended - 100-1000x Faster!)
```bash
# Run full pipeline with batch loading
./scripts/pipeline.sh batch

# Run only data loading with batch mode
./scripts/pipeline.sh batch-load

# Test with limited records
./scripts/pipeline.sh batch-load --limit 50
```

### Property Scoring
```bash
# Run scoring only (requires data to be loaded)
./scripts/pipeline.sh score

# Score with limit for testing
./scripts/pipeline.sh score --limit 10

# Run full pipeline with scoring (clean + load + score)
./scripts/pipeline.sh run --score
```

## Accessing Services

Once services are running:

- **API Base URL**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs (Swagger UI)
- **Dashboard URL**: http://localhost:8501

### Health Checks

**API Health Check:**
```bash
curl http://localhost:8000/api/v1/health
```

**Frontend Health Check:**
```bash
curl http://localhost:8501/_stcore/health
```

## Documentation

- [Interactive CLI Guide](docs/CLI_GUIDE.md) - Complete guide for using the interactive CLI tool
- [Quick Start Guide](docs/QUICK_START_BATCH_LOADING.md) - Quick reference for batch loading
