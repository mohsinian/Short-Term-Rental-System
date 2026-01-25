#!/bin/bash

# Migration script for Short-Term Rental System
# This script runs database migrations against Supabase

echo "========================================="
echo "Database Migration Runner"
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
        echo "🚀 Running migrations..."
        docker-compose run --rm pipeline python -m src.database.migrate run
        ;;
    "status")
        echo "📊 Checking migration status..."
        docker-compose run --rm pipeline python -m src.database.migrate status
        ;;
    "dry-run")
        echo "🔍 Dry run - showing what would be executed..."
        docker-compose run --rm pipeline python -m src.database.migrate dry-run
        ;;
    "test")
        echo "🔌 Testing database connection..."
        docker-compose run --rm pipeline python -c "from src.database import test_connection; test_connection()"
        ;;
    *)
        echo "❌ Unknown command: $COMMAND"
        echo ""
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  run      - Run pending migrations (default)"
        echo "  status   - Show migration status"
        echo "  dry-run  - Show what would be executed without running"
        echo "  test     - Test database connection"
        echo ""
        exit 1
        ;;
esac

echo ""
echo "Done!"
