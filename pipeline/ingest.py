"""
Test script for Supabase connection using supabase-py.

This script tests the connection to Supabase using the supabase-py library.
"""

import sys
from src.database.supabase_client import test_connection


def main():
    """Main entry point for testing Supabase connection."""
    print("Testing Supabase connection using supabase-py...")
    print("=" * 60)

    success = test_connection()

    if success:
        print("=" * 60)
        print("✅ Connection test passed!")
        return 0
    else:
        print("=" * 60)
        print("❌ Connection test failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
