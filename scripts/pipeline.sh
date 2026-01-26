#!/bin/bash

# Pipeline script for Short-Term Rental System
# This script runs the data cleaning and loading pipeline

echo "========================================="
echo "Data Pipeline Runner"
echo "========================================="
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "   Please create a .env file based on sample.env"
    echo "   Make sure to include SUPABASE_URL and SUPABASE_DB_PASSWORD"
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running!"
    echo "   Please start Docker and try again."
    exit 1
fi

# Build the Docker image if needed
echo "🔨 Ensuring Docker image is up to date..."
docker-compose build > /dev/null 2>&1

# Parse command arguments
COMMAND=${1:-"run"}

case $COMMAND in
    "run")
        echo "🚀 Running full pipeline (clean + load)..."
        docker-compose run --rm pipeline python pipeline/run_pipeline.py ${@:2}
        ;;
    "clean")
        echo "🧹 Running data cleaning step only..."
        docker-compose run --rm pipeline python pipeline/run_pipeline.py --clean-only
        ;;
    "load")
        echo "📥 Running data loading step only..."
        docker-compose run --rm pipeline python pipeline/run_pipeline.py --load-only ${@:2}
        ;;
    "clean-only")
        echo "🧹 Running data cleaning step only..."
        docker-compose run --rm pipeline python pipeline/run_pipeline.py --clean-only
        ;;
    "load-only")
        echo "📥 Running data loading step only..."
        docker-compose run --rm pipeline python pipeline/run_pipeline.py --load-only ${@:2}
        ;;
    "batch")
        echo "⚡ Running full pipeline with batch loading (fast)..."
        docker-compose run --rm pipeline python pipeline/run_pipeline.py --batch ${@:2}
        ;;
    "batch-load")
        echo "⚡ Running data loading with batch mode (fast)..."
        docker-compose run --rm pipeline python pipeline/run_pipeline.py --load-only --batch ${@:2}
        ;;
    *)
        echo "❌ Unknown command: $COMMAND"
        echo ""
        echo "Usage: $0 [command] [args...]"
        echo ""
        echo "Commands:"
        echo "  run [args]        - Run full pipeline (clean + load) (default)"
        echo "  clean [args]      - Run data cleaning step only"
        echo "  load [args]       - Run data loading step only"
        echo "  batch [args]      - Run full pipeline with batch loading (10-100x faster)"
        echo "  batch-load [args] - Run data loading with batch mode only"
        echo ""
        echo "Examples:"
        echo "  $0 run --limit 5              # Run full pipeline with 5 properties"
        echo "  $0 load --limit 10           # Load only 10 properties (standard mode)"
        echo "  $0 batch                      # Run full pipeline with batch loading (fast)"
        echo "  $0 batch-load --limit 100     # Load 100 properties with batch mode"
        echo "  $0 batch --batch-size 1000    # Run with custom batch size"
        echo "  $0 batch --no-copy           # Use Supabase API instead of COPY command"
        echo ""
        exit 1
        ;;
esac

echo ""
echo "Done!"
