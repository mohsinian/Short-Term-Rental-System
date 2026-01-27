# Interactive CLI Guide

The Short-Term Rental System includes an interactive CLI tool that makes it easy to manage database migrations, run data pipelines, and monitor system status without remembering complex commands.

## Quick Start

To launch the interactive CLI, simply run:

```bash
./cli.sh
```

This will automatically:
1. Check if Docker is running
2. Ensure the Docker image is up to date
3. Launch the interactive menu

## Main Menu Options

### 1. 🗄️ Database Migrations

Access database migration tools with the following options:

- **Run pending migrations** - Apply all pending database migrations
- **Check migration status** - View current migration state and pending changes
- **Dry run** - Preview what migrations would be executed without running them
- **Test database connection** - Verify your Supabase connection is working

**Use cases:**
- First-time setup: Run "Run pending migrations" to set up your database
- After updates: Check status to see if new migrations are available
- Troubleshooting: Test connection if you're having database issues

### 2. 📊 Data Pipeline

Run the data cleaning and loading pipeline with flexible options:

#### Option 1: Run Full Pipeline (Clean + Load)
- Runs both data cleaning and data loading steps
- Optional: Enter a limit to process only a specific number of properties
- **Example:** Enter `10` to process only the first 10 properties

#### Option 2: Run Data Cleaning Step Only
- Cleans and normalizes CSV data
- Optional: Enter a limit to clean only specific properties
- **Use case:** When you want to prepare data but not load it yet

#### Option 3: Run Data Loading Step Only
- Loads already cleaned data into the database
- Optional: Enter a limit to load only specific properties
- **Use case:** When data is already cleaned and you just need to load it

#### Option 4: Run Full Pipeline with Batch Loading (Fast!)
- Uses optimized batch loading (10-1000x faster than standard mode)
- Optional: Enter a limit and custom batch size
- **Recommended for production use**

#### Option 5: Run Data Loading with Batch Mode Only
- Load-only version of batch mode
- Optional: Enter a limit and custom batch size
- **Use case:** When data is cleaned and you want fast loading

#### Option 6: Run with Custom Options
- Enter any custom pipeline options directly
- **Example:** `--batch --limit 100 --batch-size 500 --no-copy`

### 3. 🏗️ Build Docker Image

Rebuild the Docker image with the latest code changes. This is useful when:
- You've modified Python code
- You've updated dependencies in `requirements.txt`
- You want to ensure you're running the latest version

### 4. 📈 System Status

View current system information including:
- Docker status (running or stopped)
- `.env` file status
- Available Docker images
- Running containers with their status and ports

**Use case:** Quick health check before running operations

### 5. 🐳 Container Management

Manage Docker containers with these options:

- **Start containers** - Start all services using `docker-compose up -d`
- **Stop containers** - Stop all services using `docker-compose down`
- **View logs** - Follow container logs in real-time (press Ctrl+C to exit)
- **Remove all containers and volumes** - Complete cleanup (requires confirmation)

**Warning:** The remove option will delete all data in volumes. Use with caution!

## Common Workflows

### First-Time Setup

1. Run `./cli.sh`
2. Select option 1 (Database Migrations)
3. Choose "Run pending migrations"
4. Select option 2 (Data Pipeline)
5. Choose "Run full pipeline with batch loading"
6. Enter limit (e.g., 10 for testing)

### Testing with Small Dataset

1. Run `./cli.sh`
2. Select option 2 (Data Pipeline)
3. Choose "Run full pipeline with batch loading"
4. Enter limit: `10`
5. Review results, then increase limit as needed

### Production Deployment

1. Run `./cli.sh`
2. Select option 3 (Build Docker Image) to ensure latest code
3. Select option 1 (Database Migrations) → "Run pending migrations"
4. Select option 2 (Data Pipeline) → "Run full pipeline with batch loading"
5. Leave limit empty to process all properties

### Troubleshooting Connection Issues

1. Run `./cli.sh`
2. Select option 4 (System Status) to check Docker
3. Select option 1 (Database Migrations) → "Test database connection"
4. Review error messages and check your `.env` configuration

## Tips

- **Always test with small limits first** before processing all data
- **Use batch mode** for large datasets (it's significantly faster)
- **Check system status** before running operations to ensure Docker is ready
- **View logs** if operations fail to see detailed error messages
- **Use dry run** for migrations to preview changes before applying them

## Keyboard Shortcuts

- **Enter** - Confirm selection or submit empty value
- **Ctrl+C** - Exit from logs view
- **0** - Return to main menu from sub-menus

## Exiting

To exit the CLI, select option 0 (Exit) from the main menu, or press Ctrl+C at any time to terminate the script.

## Alternative: Direct Script Usage

While the interactive CLI is recommended, you can also use scripts directly:

```bash
# Migrations
./scripts/migrate.sh run
./scripts/migrate.sh status

# Pipeline
./scripts/pipeline.sh batch --limit 10
./scripts/pipeline.sh run

# Build
./scripts/build.sh
```

See the main [README.md](../README.md) for more details on direct script usage.
