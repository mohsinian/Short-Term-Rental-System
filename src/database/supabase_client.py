"""
Supabase client module using supabase-py library.

This module provides a factory for creating Supabase client instances
for database operations using the supabase-py library.
"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv


def get_supabase_client() -> Client:
    """
    Create and return a Supabase client instance.

    Uses environment variables for configuration:
    - SUPABASE_URL: Your Supabase project URL
    - SUPABASE_SECRET_KEY: Your Supabase service role key (for admin operations)

    Returns:
        Client: A supabase-py Client instance.

    Raises:
        ValueError: If required environment variables are not set.
        Exception: If client initialization fails.
    """
    load_dotenv()

    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SECRET_KEY")

    if not supabase_url:
        raise ValueError(
            "SUPABASE_URL environment variable is not set. "
            "Please check your .env file."
        )

    if not supabase_key:
        raise ValueError(
            "SUPABASE_SECRET_KEY environment variable is not set. "
            "Please add it to your .env file. "
            "You can find this in Supabase dashboard under Project Settings > API."
        )

    try:
        client: Client = create_client(supabase_url, supabase_key)
        return client
    except Exception as e:
        raise Exception(f"Failed to initialize Supabase client: {e}")


def test_connection() -> bool:
    """
    Test the Supabase connection.

    Returns:
        bool: True if connection is successful, False otherwise.
    """
    try:
        client = get_supabase_client()
        # Simple query to test connection - check if we can query the schema_version table
        response = client.table("schema_version").select("*").limit(1).execute()
        print("✅ Supabase connection successful!")
        return True
    except Exception as e:
        print(f"❌ Supabase connection failed: {e}")
        return False
