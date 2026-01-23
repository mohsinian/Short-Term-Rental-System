import os
import sys
from supabase import create_client, Client
from dotenv import load_dotenv

def test_connection():
    # 1. Load Environment Variables
    load_dotenv()
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SECRET_KEY")

    if not url or not key:
        print("❌ Error: Missing SUPABASE_URL or SUPABASE_SERVICE_KEY in .env")
        sys.exit(1)

    print(f"Connecting to: {url}...")

    # 2. Initialize Client
    try:
        supabase: Client = create_client(url, key)

        # 3. Simple API Call for testing
        res = supabase.table('tahsin').select("*").limit(1).execute() 

        print("✅ SUCCESS: Supabase client initialized and connected.")
        return True

    except Exception as e:
        print(f"❌ CONNECTION FAILED: {e}")
        return False

if __name__ == "__main__":
    test_connection()