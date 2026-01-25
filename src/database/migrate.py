"""
Migration runner for PostgreSQL/Supabase database.

This module handles the execution of SQL migration files, tracking which
migrations have been applied to prevent duplicate execution.
"""

import re
import sys
from pathlib import Path
from typing import List

from src.database.connection import get_db_connection, close_connection


# Migrations directory path
MIGRATIONS_DIR = Path(__file__).parent.parent.parent / "migrations"


def get_migration_files() -> List[tuple]:
    """
    Get all migration files sorted by version number.

    Returns:
        List of tuples containing (version, filename, filepath) sorted by version.
    """
    if not MIGRATIONS_DIR.exists():
        raise FileNotFoundError(f"Migrations directory not found: {MIGRATIONS_DIR}")

    migrations = []
    for file_path in MIGRATIONS_DIR.glob("*.sql"):
        filename = file_path.name
        # Extract version number from filename (e.g., "001_Initial_Schema.sql" -> "001")
        match = re.match(r'^(\d+)_', filename)
        if match:
            version = match.group(1)
            migrations.append((version, filename, file_path))

    # Sort by version number
    migrations.sort(key=lambda x: int(x[0]))
    return migrations


def ensure_schema_version_table(conn) -> None:
    """
    Ensure the schema_version tracking table exists.

    Args:
        conn: Database connection object.
    """
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                id SERIAL PRIMARY KEY,
                version VARCHAR(255) NOT NULL UNIQUE,
                description TEXT,
                success BOOLEAN DEFAULT FALSE,
                executed_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        conn.commit()


def get_applied_migrations(conn) -> set:
    """
    Get the set of migration versions that have already been applied.

    Args:
        conn: Database connection object.

    Returns:
        Set of version strings that have been successfully applied.
    """
    with conn.cursor() as cur:
        # Check if schema_version table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'schema_version'
            );
        """)
        table_exists = cur.fetchone()[0]

        if not table_exists:
            return set()

        # Get applied migrations
        cur.execute("SELECT version FROM schema_version WHERE success = TRUE;")
        applied = {row[0] for row in cur.fetchall()}

    return applied


def execute_migration(conn, version: str, filepath: Path, applied_migrations: set) -> bool:
    """
    Execute a single migration file.

    Args:
        conn: Database connection object.
        version: Migration version identifier.
        filepath: Path to the migration SQL file.
        applied_migrations: Set of already applied migration versions.

    Returns:
        bool: True if migration was successful or already applied, False otherwise.
    """
    # Check if migration is already applied
    if version in applied_migrations:
        print(f"  ℹ️  Migration {version} was already executed successfully before.")
        return True

    print(f"  → Executing migration: {filepath.name}")

    try:
        # Ensure schema_version table exists before executing
        ensure_schema_version_table(conn)

        # Read the migration SQL
        with open(filepath, 'r') as f:
            sql = f.read()

        # Execute the migration
        with conn.cursor() as cur:
            cur.execute(sql)

        # Record the migration in schema_version table
        # Extract description from filename (remove .sql extension)
        description = filepath.stem.replace(f"{version}_", "").replace("_", " ").title()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO schema_version (version, description, success)
                VALUES (%s, %s, TRUE)
                ON CONFLICT (version) DO UPDATE SET success = TRUE;
            """, (version, description))

        # Commit the transaction
        conn.commit()
        print(f"  ✅ Migration {version} executed successfully")
        return True

    except Exception as e:
        # Rollback on error
        conn.rollback()
        print(f"  ❌ Migration {version} failed: {e}")
        return False


def run_migrations(dry_run: bool = False) -> None:
    """
    Run all pending migrations.

    Args:
        dry_run: If True, print what would be done without executing.
    """
    print("=" * 60)
    print("Migration Runner")
    print("=" * 60)

    if dry_run:
        print("🔍 DRY RUN MODE - No changes will be made\n")

    # Get all migration files
    migrations = get_migration_files()

    if not migrations:
        print("⚠️  No migration files found in:", MIGRATIONS_DIR)
        return

    print(f"Found {len(migrations)} migration file(s):\n")
    for version, filename, _ in migrations:
        print(f"  - {filename}")
    print()

    conn = None
    try:
        # Get database connection
        conn = get_db_connection()

        # Ensure schema_version table exists
        ensure_schema_version_table(conn)

        # Get already applied migrations
        applied = get_applied_migrations(conn)

        print(f"\nApplied migrations: {len(applied)}")
        if applied:
            print(f"  {', '.join(sorted(applied))}")
        print()

        # Filter pending migrations
        pending = [(v, f, p) for v, f, p in migrations if v not in applied]

        if not pending:
            print("✅ All migrations are up to date!")
            return

        print(f"Pending migrations: {len(pending)}\n")

        # Execute pending migrations
        if dry_run:
            print("Would execute the following migrations:")
            for version, filename, _ in pending:
                print(f"  - {filename}")
            return

        success_count = 0
        for version, filename, filepath in pending:
            if execute_migration(conn, version, filepath, applied):
                success_count += 1
            else:
                print(f"\n⚠️  Migration {version} failed. Stopping further migrations.")
                break

        print()
        print("=" * 60)
        if success_count == len(pending):
            print(f"✅ All {success_count} migration(s) executed successfully!")
        else:
            print(f"⚠️  {success_count}/{len(pending)} migration(s) executed.")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
    finally:
        close_connection(conn)


def rollback_migration(version: str) -> None:
    """
    Rollback a specific migration.

    Note: This requires that the migration file includes rollback logic
    or that you have a separate rollback file.

    Args:
        version: The migration version to rollback.
    """
    print(f"⚠️  Rollback functionality not implemented for version {version}")
    print("   To rollback, you need to manually execute the appropriate SQL.")


def status() -> None:
    """
    Display migration status.
    """
    print("=" * 60)
    print("Migration Status")
    print("=" * 60)

    try:
        conn = get_db_connection()
        # Ensure schema_version table exists
        ensure_schema_version_table(conn)
        applied = get_applied_migrations(conn)
        all_migrations = get_migration_files()

        print(f"\nTotal migration files: {len(all_migrations)}")
        print(f"Applied migrations: {len(applied)}")
        print(f"Pending migrations: {len(all_migrations) - len(applied)}\n")

        print("Status:")
        for version, filename, _ in all_migrations:
            status_icon = "✅" if version in applied else "⏳"
            print(f"  {status_icon} {filename}")

        print()
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error checking status: {e}")
        sys.exit(1)
    finally:
        close_connection(conn)


def main():
    """Main entry point for the migration runner."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Database migration runner for Supabase/PostgreSQL"
    )
    parser.add_argument(
        "command",
        choices=["run", "status", "dry-run"],
        nargs="?",
        default="run",
        help="Command to execute (default: run)"
    )

    args = parser.parse_args()

    if args.command == "status":
        status()
    elif args.command == "dry-run":
        run_migrations(dry_run=True)
    else:
        run_migrations(dry_run=False)


if __name__ == "__main__":
    main()
