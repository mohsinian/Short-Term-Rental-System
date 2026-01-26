# Quick Start: Batch Loading

This is a quick reference guide for using the optimized batch loading feature.

## Fastest Way to Load Data

```bash
# Run full pipeline with batch loading (recommended)
./scripts/pipeline.sh batch
```

That's it! The batch loader will automatically:
1. Use PostgreSQL COPY command if `SUPABASE_DB_CONNECTION_STRING` is configured
2. Fall back to Supabase batch insert API if not
3. Load data in parallel for maximum performance

## Common Commands

### Test with Small Dataset

```bash
# Load only 50 properties (great for testing)
./scripts/pipeline.sh batch-load --limit 50
```

### Load Only (Skip Cleaning)

```bash
# If you already have cleaned data, just load it
./scripts/pipeline.sh batch-load
```

### Custom Batch Size

```bash
# Use larger batches for faster loading (if you have enough memory)
python pipeline/run_pipeline.py --batch --batch-size 1000
```

### Use Supabase API (No DB Connection String)

```bash
# If you don't have SUPABASE_DB_CONNECTION_STRING configured
python pipeline/run_pipeline.py --batch --no-copy
```

## Configuration

### Step 1: Check Your .env File

Make sure you have at least:
```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SECRET_KEY=your-service-role-key
```

### Step 2: (Highly Recommmended) Add Database Connection for Maximum Speed

Get your connection string from Supabase Dashboard:
1. Copy the **Connection string** (Session pooler or Transaction pooler)
2. Add to `.env`:
```bash
SUPABASE_DB_CONNECTION_STRING=postgresql://postgres.xxxxx:password@aws-0-us-east-1.pooler.supabase.com:6543/postgres
```


## Troubleshooting

### "Falling back to Supabase batch insert API"

This is normal if you don't have `SUPABASE_DB_CONNECTION_STRING` configured. It's still 10-100x faster than the original loader.

### Connection Timeout

If you get timeout errors, try:
```bash
# Reduce batch size
python pipeline/run_pipeline.py --batch --batch-size 100
```

### Out of Memory

Reduce batch size or limit records:
```bash
python pipeline/run_pipeline.py --batch --batch-size 50 --limit 100
```
