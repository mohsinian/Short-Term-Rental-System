"""
Database module for Short-Term Rental System.

This module provides database connection and migration functionality
for PostgreSQL/Supabase using both psycopg2 and supabase-py.
"""

# Import supabase-py client (required for data loading)
from .supabase_client import get_supabase_client, test_connection as test_supabase_connection

# Import psycopg2 connection (for migrations) - optional
try:
    from .connection import get_db_connection, close_connection, test_connection as test_pg_connection
    _psycopg2_available = True
except ImportError:
    _psycopg2_available = False
    get_db_connection = None
    close_connection = None
    test_pg_connection = None

# Import migrations (requires psycopg2)
try:
    from .migrate import run_migrations, status
    _migrations_available = True
except ImportError:
    _migrations_available = False
    run_migrations = None
    status = None

__all__ = [
    # supabase-py client (for data loading)
    "get_supabase_client",
    "test_supabase_connection",
]

# Add psycopg2 functions if available
if _psycopg2_available:
    __all__.extend([
        "get_db_connection",
        "close_connection",
        "test_pg_connection",
    ])

# Add migration functions if available
if _migrations_available:
    __all__.extend([
        "run_migrations",
        "status",
    ])
