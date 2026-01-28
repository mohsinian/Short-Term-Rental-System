#!/bin/bash

# Build script for Short-Term Rental System

echo "========================================="
echo "Docker Build Script"
echo "========================================="
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running!"
    echo "   Please start Docker and try again."
    exit 1
fi

# Parse command arguments
SERVICE=${1:-"all"}

case $SERVICE in
    "pipeline"|"api"|"frontend"|"all")
        if [ "$SERVICE" = "all" ]; then
            echo "🔨 Building all Docker images (pipeline + api + frontend)..."
            docker-compose build
        else
            echo "🔨 Building Docker image for service: $SERVICE..."
            docker-compose build $SERVICE
        fi
        echo ""
        echo "✅ Build complete!"
        ;;
    *)
        echo "❌ Unknown service: $SERVICE"
        echo ""
        echo "Usage: $0 [service]"
        echo ""
        echo "Services:"
        echo "  pipeline  - Build pipeline service only"
        echo "  api       - Build API service only"
        echo "  frontend  - Build frontend service only"
        echo "  all       - Build all services (default)"
        echo ""
        exit 1
        ;;
esac
