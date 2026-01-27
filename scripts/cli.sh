#!/bin/bash

# Interactive CLI for Short-Term Rental System
# This script provides an interactive menu for managing the application

set -e

# Check if terminal supports colors
if [ -t 1 ] && command -v tput >/dev/null 2>&1; then
    # Use tput for portable terminal formatting
    RED=$(tput setaf 1)
    GREEN=$(tput setaf 2)
    YELLOW=$(tput setaf 3)
    BLUE=$(tput setaf 4)
    CYAN=$(tput setaf 6)
    BOLD=$(tput bold)
    NC=$(tput sgr0)
else
    # Fallback to plain text
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    CYAN=''
    BOLD=''
    NC=''
fi

# Determine which docker compose command to use
if command -v docker-compose >/dev/null 2>&1; then
    DOCKER_COMPOSE="docker-compose"
elif docker compose version >/dev/null 2>&1; then
    DOCKER_COMPOSE="docker compose"
else
    print_error "Neither docker-compose nor docker compose is available!"
    exit 1
fi

# Function to print colored text
print_header() {
    printf "${CYAN}${BOLD}%s${NC}\n" "$1"
}

print_success() {
    printf "${GREEN}✓ %s${NC}\n" "$1"
}

print_error() {
    printf "${RED}✗ %s${NC}\n" "$1"
}

print_info() {
    printf "${BLUE}ℹ %s${NC}\n" "$1"
}

print_warning() {
    printf "${YELLOW}⚠ %s${NC}\n" "$1"
}

# Function to check prerequisites
check_prerequisites() {
    # Check if .env file exists
    if [ ! -f .env ]; then
        print_error ".env file not found!"
        echo ""
        print_info "Please create a .env file based on sample.env"
        print_info "Make sure to include SUPABASE_URL and SUPABASE_DB_PASSWORD"
        echo ""
        return 1
    fi

    # Check if Docker is running
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running!"
        echo ""
        print_info "Please start Docker and try again."
        echo ""
        return 1
    fi

    return 0
}

# Function to build Docker image
build_docker() {
    echo ""
    print_header "Building Docker image..."
    echo ""
    if $DOCKER_COMPOSE build; then
        print_success "Docker image built successfully!"
    else
        print_error "Failed to build Docker image"
        return 1
    fi
    echo ""
}

# Function to run migrations
run_migrations() {
    echo ""
    print_header "Database Migrations"
    echo ""
    echo "Select migration operation:"
    echo "  1) Run pending migrations"
    echo "  2) Check migration status"
    echo "  3) Dry run (show what would be executed)"
    echo "  4) Test database connection"
    echo "  0) Back to main menu"
    echo ""
    read -p "Enter your choice [0-4]: " migrate_choice

    case $migrate_choice in
        1)
            echo ""
            print_info "Running pending migrations..."
            $DOCKER_COMPOSE run --rm pipeline python -m src.database.migrate run
            ;;
        2)
            echo ""
            print_info "Checking migration status..."
            $DOCKER_COMPOSE run --rm pipeline python -m src.database.migrate status
            ;;
        3)
            echo ""
            print_info "Dry run - showing what would be executed..."
            $DOCKER_COMPOSE run --rm pipeline python -m src.database.migrate dry-run
            ;;
        4)
            echo ""
            print_info "Testing database connection..."
            $DOCKER_COMPOSE run --rm pipeline python -c "from src.database import test_connection; test_connection()"
            ;;
        0)
            return
            ;;
        *)
            print_error "Invalid choice!"
            ;;
    esac
    echo ""
}

# Function to run pipeline
run_pipeline() {
    echo ""
    print_header "Data Pipeline"
    echo ""
    echo "Select pipeline operation:"
    echo "  1) Run full pipeline (clean + load)"
    echo "  2) Run data cleaning step only"
    echo "  3) Run data loading step only"
    echo "  4) Run property scoring only"
    echo "  5) Run full pipeline with batch loading (fast)"
    echo "  6) Run data loading with batch mode only"
    echo "  7) Run full pipeline with scoring (clean + load + score)"
    echo "  8) Run with custom options"
    echo "  0) Back to main menu"
    echo ""
    read -p "Enter your choice [0-8]: " pipeline_choice

    case $pipeline_choice in
        1)
            echo ""
            read -p "Enter limit (number of properties, or leave empty for all): " limit
            if [ -z "$limit" ]; then
                print_info "Running full pipeline (all properties)..."
                $DOCKER_COMPOSE run --rm pipeline python pipeline/run_pipeline.py
            else
                print_info "Running full pipeline (limit: $limit properties)..."
                $DOCKER_COMPOSE run --rm pipeline python pipeline/run_pipeline.py --limit "$limit"
            fi
            ;;
        2)
            echo ""
            read -p "Enter limit (number of properties, or leave empty for all): " limit
            if [ -z "$limit" ]; then
                print_info "Running data cleaning step only..."
                $DOCKER_COMPOSE run --rm pipeline python pipeline/run_pipeline.py --clean-only
            else
                print_info "Running data cleaning step only (limit: $limit properties)..."
                $DOCKER_COMPOSE run --rm pipeline python pipeline/run_pipeline.py --clean-only --limit "$limit"
            fi
            ;;
        3)
            echo ""
            read -p "Enter limit (number of properties, or leave empty for all): " limit
            if [ -z "$limit" ]; then
                print_info "Running data loading step only..."
                $DOCKER_COMPOSE run --rm pipeline python pipeline/run_pipeline.py --load-only
            else
                print_info "Running data loading step only (limit: $limit properties)..."
                $DOCKER_COMPOSE run --rm pipeline python pipeline/run_pipeline.py --load-only --limit "$limit"
            fi
            ;;
        4)
            echo ""
            read -p "Enter limit (number of properties, or leave empty for all): " limit
            read -p "Enter batch size (default: 500, press Enter for default): " batch_size
            if [ -z "$limit" ]; then
                if [ -z "$batch_size" ]; then
                    print_info "Running full pipeline with batch loading..."
                    $DOCKER_COMPOSE run --rm pipeline python pipeline/run_pipeline.py --batch
                else
                    print_info "Running full pipeline with batch loading (batch size: $batch_size)..."
                    $DOCKER_COMPOSE run --rm pipeline python pipeline/run_pipeline.py --batch --batch-size "$batch_size"
                fi
            else
                if [ -z "$batch_size" ]; then
                    print_info "Running full pipeline with batch loading (limit: $limit properties)..."
                    $DOCKER_COMPOSE run --rm pipeline python pipeline/run_pipeline.py --batch --limit "$limit"
                else
                    print_info "Running full pipeline with batch loading (limit: $limit, batch size: $batch_size)..."
                    $DOCKER_COMPOSE run --rm pipeline python pipeline/run_pipeline.py --batch --limit "$limit" --batch-size "$batch_size"
                fi
            fi
            ;;
        5)
            echo ""
            read -p "Enter limit (number of properties, or leave empty for all): " limit
            read -p "Enter batch size (default: 500, press Enter for default): " batch_size
            if [ -z "$limit" ]; then
                if [ -z "$batch_size" ]; then
                    print_info "Running data loading with batch mode only..."
                    $DOCKER_COMPOSE run --rm pipeline python pipeline/run_pipeline.py --load-only --batch
                else
                    print_info "Running data loading with batch mode only (batch size: $batch_size)..."
                    $DOCKER_COMPOSE run --rm pipeline python pipeline/run_pipeline.py --load-only --batch --batch-size "$batch_size"
                fi
            else
                if [ -z "$batch_size" ]; then
                    print_info "Running data loading with batch mode only (limit: $limit properties)..."
                    $DOCKER_COMPOSE run --rm pipeline python pipeline/run_pipeline.py --load-only --batch --limit "$limit"
                else
                    print_info "Running data loading with batch mode only (limit: $limit, batch size: $batch_size)..."
                    $DOCKER_COMPOSE run --rm pipeline python pipeline/run_pipeline.py --load-only --batch --limit "$limit" --batch-size "$batch_size"
                fi
            fi
            ;;
        6)
            echo ""
            print_info "Enter custom pipeline options..."
            read -p "Options (e.g., --batch --limit 100 --batch-size 500): " custom_options
            print_info "Running pipeline with custom options: $custom_options"
            $DOCKER_COMPOSE run --rm pipeline python pipeline/run_pipeline.py $custom_options
            ;;
        0)
            return
            ;;
        *)
            print_error "Invalid choice!"
            ;;
    esac
    echo ""
}

# Function to show system status
show_status() {
    echo ""
    print_header "System Status"
    echo ""
    
    # Check Docker
    if docker info > /dev/null 2>&1; then
        print_success "Docker is running"
    else
        print_error "Docker is not running"
    fi
    
    # Check .env file
    if [ -f .env ]; then
        print_success ".env file exists"
    else
        print_error ".env file not found"
    fi
    
    # Check Docker images
    echo ""
    print_info "Docker images:"
    docker images | grep -E "REPOSITORY|short-term-rental" || echo "  No images found"
    
    # Check running containers
    echo ""
    print_info "Running containers:"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "NAMES|short-term-rental" || echo "  No containers running"
    
    echo ""
}

# Function to manage Docker containers
manage_containers() {
    echo ""
    print_header "Container Management"
    echo ""
    echo "Select operation:"
    echo "  1) Start containers (docker-compose up)"
    echo "  2) Stop containers (docker-compose down)"
    echo "  3) View logs"
    echo "  4) Remove all containers and volumes"
    echo "  0) Back to main menu"
    echo ""
    read -p "Enter your choice [0-4]: " container_choice

    case $container_choice in
        1)
            echo ""
            print_info "Starting containers..."
            $DOCKER_COMPOSE up -d
            print_success "Containers started!"
            ;;
        2)
            echo ""
            print_info "Stopping containers..."
            $DOCKER_COMPOSE down
            print_success "Containers stopped!"
            ;;
        3)
            echo ""
            print_info "Showing logs (press Ctrl+C to exit)..."
            $DOCKER_COMPOSE logs -f
            ;;
        4)
            echo ""
            print_warning "This will remove all containers and volumes!"
            read -p "Are you sure? (yes/no): " confirm
            if [ "$confirm" = "yes" ]; then
                print_info "Removing containers and volumes..."
                $DOCKER_COMPOSE down -v
                print_success "Containers and volumes removed!"
            else
                print_info "Operation cancelled."
                fi
            ;;
        4)
            echo ""
            read -p "Enter limit (number of properties, or leave empty for all): " limit
            if [ -z "$limit" ]; then
                print_info "Running property scoring only..."
                $DOCKER_COMPOSE run --rm pipeline python pipeline/run_pipeline.py --score-only
            else
                print_info "Running property scoring only (limit: $limit properties)..."
                $DOCKER_COMPOSE run --rm pipeline python pipeline/run_pipeline.py --score-only --limit "$limit"
            fi
            ;;
        5)
            echo ""
            read -p "Enter limit (number of properties, or leave empty for all): " limit
            read -p "Enter batch size (default: 500, press Enter for default): " batch_size
            if [ -z "$limit" ]; then
                if [ -z "$batch_size" ]; then
                    print_info "Running full pipeline with batch loading..."
                    $DOCKER_COMPOSE run --rm pipeline python pipeline/run_pipeline.py --batch
                else
                    print_info "Running full pipeline with batch loading (batch size: $batch_size)..."
                    $DOCKER_COMPOSE run --rm pipeline python pipeline/run_pipeline.py --batch --batch-size "$batch_size"
                fi
            else
                if [ -z "$batch_size" ]; then
                    print_info "Running full pipeline with batch loading (limit: $limit properties)..."
                    $DOCKER_COMPOSE run --rm pipeline python pipeline/run_pipeline.py --batch --limit "$limit"
                else
                    print_info "Running full pipeline with batch loading (limit: $limit, batch size: $batch_size)..."
                    $DOCKER_COMPOSE run --rm pipeline python pipeline/run_pipeline.py --batch --limit "$limit" --batch-size "$batch_size"
                fi
            fi
            ;;
        6)
            echo ""
            read -p "Enter limit (number of properties, or leave empty for all): " limit
            read -p "Enter batch size (default: 500, press Enter for default): " batch_size
            if [ -z "$limit" ]; then
                if [ -z "$batch_size" ]; then
                    print_info "Running data loading with batch mode only..."
                    $DOCKER_COMPOSE run --rm pipeline python pipeline/run_pipeline.py --load-only --batch
                else
                    print_info "Running data loading with batch mode only (batch size: $batch_size)..."
                    $DOCKER_COMPOSE run --rm pipeline python pipeline/run_pipeline.py --load-only --batch --batch-size "$batch_size"
                fi
            else
                if [ -z "$batch_size" ]; then
                    print_info "Running data loading with batch mode only (limit: $limit properties)..."
                    $DOCKER_COMPOSE run --rm pipeline python pipeline/run_pipeline.py --load-only --batch --limit "$limit"
                else
                    print_info "Running data loading with batch mode only (limit: $limit, batch size: $batch_size)..."
                    $DOCKER_COMPOSE run --rm pipeline python pipeline/run_pipeline.py --load-only --batch --limit "$limit" --batch-size "$batch_size"
                fi
            fi
            ;;
        7)
            echo ""
            read -p "Enter limit (number of properties, or leave empty for all): " limit
            if [ -z "$limit" ]; then
                print_info "Running full pipeline with scoring..."
                $DOCKER_COMPOSE run --rm pipeline python pipeline/run_pipeline.py --score
            else
                print_info "Running full pipeline with scoring (limit: $limit properties)..."
                $DOCKER_COMPOSE run --rm pipeline python pipeline/run_pipeline.py --score --limit "$limit"
            fi
            ;;
        8)
            echo ""
            print_info "Enter custom pipeline options..."
            read -p "Options (e.g., --batch --limit 100 --batch-size 500 --score): " custom_options
            print_info "Running pipeline with custom options: $custom_options"
            $DOCKER_COMPOSE run --rm pipeline python pipeline/run_pipeline.py $custom_options
            ;;
        0)
            return
            ;;
        *)
            print_error "Invalid choice!"
            ;;
    esac
    echo ""
}

# Main menu
main_menu() {
    while true; do
        clear
        echo ""
        printf "${CYAN}${BOLD}╔════════════════════════════════════════════════════════════╗${NC}\n"
        printf "${CYAN}${BOLD}║   Short-Term Rental System - Interactive CLI              ║${NC}\n"
        printf "${CYAN}${BOLD}╚════════════════════════════════════════════════════════════╝${NC}\n"
        echo ""
        printf "  ${BOLD}Main Menu${NC}\n"
        echo ""
        echo "  1) 🗄️  Database Migrations"
        echo "  2) 📊 Data Pipeline"
        echo "  3) 🏗️  Build Docker Image"
        echo "  4) 📈 System Status"
        echo "  5) 🐳 Container Management"
        echo "  0) Exit"
        echo ""
        read -p "Enter your choice [0-5]: " choice

        case $choice in
            1)
                check_prerequisites && run_migrations
                ;;
            2)
                check_prerequisites && run_pipeline
                ;;
            3)
                build_docker
                ;;
            4)
                show_status
                ;;
            5)
                manage_containers
                ;;
            0)
                echo ""
                print_success "Goodbye! 👋"
                echo ""
                exit 0
                ;;
            *)
                print_error "Invalid choice! Please try again."
                ;;
        esac

        if [ $? -eq 0 ]; then
            echo ""
            read -p "Press Enter to continue..."
        fi
    done
}

# Start the CLI
main_menu
