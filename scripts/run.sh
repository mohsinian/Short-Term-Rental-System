#!/bin/bash

# Run script for Short-Term Rental System

echo "========================================="
echo "Docker Run Script"
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

# Parse command arguments
SERVICE=${1:-"all"}
MODE=${2:-"up"}

case $SERVICE in
    "pipeline"|"api"|"all")
        if [ "$SERVICE" = "all" ]; then
            echo "🚀 Starting all Docker services (pipeline + api)..."
            if [ "$MODE" = "up" ]; then
                docker-compose up
            else
                docker-compose up -d
                echo ""
                echo "✅ Services started in detached mode!"
                echo ""
                echo "API Service: http://localhost:8000"
                echo "API Docs: http://localhost:8000/docs"
                echo ""
                echo "To view logs: docker-compose logs -f"
                echo "To stop services: docker-compose down"
            fi
        else
            echo "🚀 Starting Docker service: $SERVICE..."
            if [ "$MODE" = "up" ]; then
                docker-compose up $SERVICE
            else
                docker-compose up -d $SERVICE
                echo ""
                echo "✅ Service $SERVICE started in detached mode!"
                if [ "$SERVICE" = "api" ]; then
                    echo ""
                    echo "API Service: http://localhost:8000"
                    echo "API Docs: http://localhost:8000/docs"
                fi
                echo ""
                echo "To view logs: docker-compose logs -f $SERVICE"
                echo "To stop service: docker-compose stop $SERVICE"
            fi
        fi
        ;;
    *)
        echo "❌ Unknown service: $SERVICE"
        echo ""
        echo "Usage: $0 [service] [mode]"
        echo ""
        echo "Services:"
        echo "  pipeline - Start pipeline service only"
        echo "  api      - Start API service only"
        echo "  all      - Start all services (default)"
        echo ""
        echo "Modes:"
        echo "  up       - Start in foreground (default)"
        echo "  detached - Start in detached mode (-d)"
        echo ""
        echo "Examples:"
        echo "  $0                    # Start all services in foreground"
        echo "  $0 api                # Start API service in foreground"
        echo "  $0 api detached       # Start API service in background"
        echo "  $0 all detached       # Start all services in background"
        echo ""
        exit 1
        ;;
esac
