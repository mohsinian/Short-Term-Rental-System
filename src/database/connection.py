"""
Database connection module for PostgreSQL/Supabase.

This module provides a connection factory for PostgreSQL database operations,
particularly for running migrations.
"""

import os
import re
from typing import Optional
import psycopg2
from psycopg2.extensions import connection
from dotenv import load_dotenv


def get_db_connection() -> connection:
    """
    Create and return a PostgreSQL database connection.

    Supports multiple connection methods:
    1. Full connection string via SUPABASE_DB_CONNECTION_STRING (recommended)
    2. Supabase URL + DB password (builds connection string automatically)

    Returns:
        connection: A psycopg2 database connection object.

    Raises:
        ValueError: If required environment variables are not set.
        Exception: If connection to the database fails.
    """
    load_dotenv()

    # Method 1: Use full connection string if provided (most reliable)
    connection_string = os.environ.get("SUPABASE_DB_CONNECTION_STRING")
    if connection_string:
        try:
            conn = psycopg2.connect(connection_string)
            conn.autocommit = False
            return conn
        except Exception as e:
            raise Exception(f"Failed to connect using connection string: {e}")

    # Method 2: Build connection string from Supabase URL and password
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_password = os.environ.get("SUPABASE_DB_PASSWORD")

    if not supabase_url:
        raise ValueError(
            "SUPABASE_URL environment variable is not set. Please check your .env file."
        )

    # Parse Supabase connection URL
    # Expected format: https://<project_id>.supabase.co
    # We need to extract the project_id to build the PostgreSQL connection string
    match = re.match(r"https://([^.]+)\.supabase\.co", supabase_url)
    if not match:
        raise ValueError(
            f"Invalid SUPABASE_URL format: {supabase_url}. "
            "Expected format: https://<project_id>.supabase.co"
        )

    project_id = match.group(1)

    # Build PostgreSQL connection string
    # Format: postgresql://postgres.[project_id]:[password]@aws-0-us-east-1.pooler.supabase.com:6543/postgres
    # Note: The password can be obtained from Supabase dashboard under Project Settings > Database
    if not supabase_password:
        raise ValueError(
            "SUPABASE_DB_PASSWORD environment variable is not set. "
            "Please add it to your .env file. "
            "You can find this in Supabase dashboard under Project Settings > Database > Connection String."
        )

    db_url = (
        f"postgresql://postgres.{project_id}:{supabase_password}"
        f"@aws-0-us-east-1.pooler.supabase.com:6543/postgres"
    )

    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = False
        return conn
    except Exception as e:
        raise Exception(f"Failed to connect to database: {e}")


def close_connection(conn: Optional[connection]) -> None:
    """
    Safely close a database connection.

    Args:
        conn: The database connection to close. Can be None.
    """
    if conn is not None:
        try:
            conn.close()
        except Exception as e:
            print(f"Warning: Error closing connection: {e}")


def test_connection() -> bool:
    """
    Test the database connection.

    Returns:
        bool: True if connection is successful, False otherwise.
    """
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT version();")
            version = cur.fetchone()
            print("✅ Database connection successful!")
            if version and version[0]:
                print(f"   PostgreSQL version: {version[0][:50]}...")
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False
