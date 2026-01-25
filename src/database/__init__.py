"""
Database module for Short-Term Rental System.

This module provides database connection and migration functionality
for PostgreSQL/Supabase.
"""

from .connection import get_db_connection, close_connection, test_connection
from .migrate import run_migrations, status

__all__ = [
    "get_db_connection",
    "close_connection",
    "test_connection",
    "run_migrations",
    "status",
]
