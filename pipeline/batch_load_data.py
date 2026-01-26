"""
Optimized batch data loading module for high-performance data ingestion.

This module provides multiple loading strategies for efficiently loading
large datasets into Supabase/PostgreSQL, significantly reducing the time
compared to row-by-row operations.

Strategies:
1. PostgreSQL COPY with Temp Tables: Fastest - COPY to temp tables + INSERT...ON CONFLICT upsert
2. Supabase Batch Insert: Fast - Batch inserts via Supabase API
3. Parallel Processing: Optimized - Concurrent batch operations

Performance Improvements:
- COPY with temp tables: 100-1000x faster than individual inserts, with proper upsert support
- Batch inserts: 10-100x faster than individual inserts
- Parallel processing: 2-4x faster for independent operations

Temp Table Approach:
For hosts, properties, property_performance, and property_amenities:
1. COPY data into temp tables (fast bulk load)
2. Call upsert functions to move data from temp to main tables with INSERT...ON CONFLICT
3. This provides both speed and proper duplicate handling with updates

For markets:
- Direct upsert via Supabase API (markets are relatively static and few in number)
"""

import io
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

import pandas as pd
import psycopg2
from psycopg2.extras import execute_batch
from dotenv import load_dotenv
from supabase import Client

from src.database.supabase_client import get_supabase_client


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class BatchDataLoader:
    """
    High-performance batch data loader with temp table upsert strategy.

    Uses PostgreSQL COPY command to load data into temp tables, then
    INSERT...ON CONFLICT to move data to main tables with proper upsert logic.
    This provides the speed of bulk loading with the flexibility of upserts.
    """

    def __init__(
        self,
        cleaned_data_path: str = "data/cleaned_combined_properties.csv",
        limit: Optional[int] = None,
        batch_size: int = 500,
        use_copy_command: bool = True,
        max_workers: int = 4,
    ):
        """
        Initialize batch data loader.

        Args:
            cleaned_data_path: Path to the cleaned CSV file.
            limit: Optional limit on number of properties to load (for testing).
            batch_size: Number of records per batch for batch insert strategy.
            use_copy_command: Whether to use PostgreSQL COPY with temp tables (requires DB connection).
            max_workers: Number of parallel workers for concurrent operations.
        """
        load_dotenv()
        self.cleaned_data_path = cleaned_data_path
        self.limit = limit
        self.batch_size = batch_size
        self.use_copy_command = use_copy_command
        self.max_workers = max_workers
        self.client: Optional[Client] = None
        self.pg_conn: Optional[psycopg2.extensions.connection] = None

        # ID maps for foreign key resolution
        self.market_id_map: Dict[str, str] = {}
        self.host_id_map: Dict[str, str] = {}
        self.property_id_map: Dict[str, str] = {}

    def connect_supabase(self) -> None:
        """Establish Supabase client connection."""
        try:
            self.client = get_supabase_client()
            logger.info("Supabase client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            raise

    def connect_postgres(self) -> None:
        """
        Establish direct PostgreSQL connection for COPY command.

        Uses SUPABASE_DB_CONNECTION_STRING environment variable.
        Format: postgresql://postgres.[project-id]:[password]@aws-0-us-east-1.pooler.supabase.com:6543/postgres
        """
        try:
            conn_string = os.environ.get("SUPABASE_DB_CONNECTION_STRING")

            if not conn_string:
                raise ValueError(
                    "SUPABASE_DB_CONNECTION_STRING environment variable is required for COPY command. "
                    "You can find this in Supabase dashboard under Project Settings > Database > Connection Info."
                )

            self.pg_conn = psycopg2.connect(conn_string, connect_timeout=30)
            self.pg_conn.autocommit = False
            logger.info("PostgreSQL connection established for COPY command")

        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            logger.warning("Falling back to Supabase batch insert API")
            self.use_copy_command = False

    def disconnect(self) -> None:
        """Close all database connections."""
        if self.pg_conn:
            self.pg_conn.close()
            logger.info("PostgreSQL connection closed")
        # Supabase client doesn't require explicit closing
        logger.info("Database connections closed")

    def _parse_amenities(self, amenities_str) -> dict:
        """Parse amenities string into a JSONB-compatible dictionary."""
        if pd.isna(amenities_str) or amenities_str == "":
            return {}

        amenities_str = str(amenities_str).strip()

        try:
            return json.loads(amenities_str)
        except (json.JSONDecodeError, TypeError):
            pass

        if "," in amenities_str:
            items = [item.strip() for item in amenities_str.split(",")]
            return {"list": items}

        return {"value": amenities_str}

    def _extract_host_id_from_url(self, url: Optional[str]) -> Optional[str]:
        """Extract Airbnb host ID from URL."""
        if pd.isna(url) or url == "":
            return None

        import re

        match = re.search(r"/users/show/(\d+)|/u/(\d+)", str(url) if url else "")
        if match:
            return match.group(1) or match.group(2)
        return None

    # ============================================================================
    # MARKETS - Batch Loading
    # ============================================================================

    def _prepare_market_data(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Prepare market data for batch insertion."""
        if "market" not in df.columns:
            return []

        unique_markets = df["market"].unique()
        market_data = []

        for market_name in unique_markets:
            parts = market_name.split("_")
            state_name = parts[-1] if len(parts) > 1 and len(parts[-1]) == 2 else None
            clean_market_name = " ".join(parts[:-1]) if state_name else market_name

            market_data.append(
                {
                    "name": clean_market_name,
                    "state_name": state_name,
                }
            )

        return market_data

    def _load_markets_batch(self, market_data: List[Dict[str, Any]]) -> None:
        """Load markets using Supabase batch insert API."""
        if not market_data:
            return

        logger.info(f"Loading {len(market_data)} markets using batch insert...")

        try:
            # Use upsert to handle duplicates
            response = self.client.table("markets").upsert(market_data).execute()

            # Build ID map
            for market in response.data:
                cache_key = f"{market['name']}|{market['state_name'] or 'NULL'}"
                self.market_id_map[cache_key] = market["id"]

            logger.info(f"✅ Loaded {len(response.data)} markets")

        except Exception as e:
            logger.error(f"Error loading markets in batch: {e}")
            raise

    def _load_markets_copy(self, market_data: List[Dict[str, Any]]) -> None:
        """Load markets using PostgreSQL COPY command."""
        if not market_data:
            return

        logger.info(f"Loading {len(market_data)} markets using COPY command...")

        # DEBUG: Log all markets being loaded
        logger.debug(
            f"DEBUG: Markets to load: {[(m['name'], m['state_name']) for m in market_data]}"
        )

        try:
            cursor = self.pg_conn.cursor()

            # Check existing markets to identify duplicates
            existing_markets = set()
            cursor.execute("SELECT name, state_name FROM markets")
            for name, state_name in cursor.fetchall():
                key = f"{name}|{state_name or 'NULL'}"
                existing_markets.add(key)

            # Filter out duplicates
            filtered_market_data = []
            duplicates = []
            for market in market_data:
                key = f"{market['name']}|{market['state_name'] or 'NULL'}"
                if key in existing_markets:
                    duplicates.append((market["name"], market["state_name"]))
                else:
                    filtered_market_data.append(market)

            if duplicates:
                logger.warning(f"Skipping {len(duplicates)} duplicate markets")

            if not filtered_market_data:
                logger.info("All markets already exist, skipping COPY operation")
                # Build ID map from existing markets
                for market in market_data:
                    key = f"{market['name']}|{market['state_name'] or 'NULL'}"
                    cursor.execute(
                        "SELECT id FROM markets WHERE name = %s AND (state_name = %s OR (state_name IS NULL AND %s IS NULL))",
                        (market["name"], market["state_name"], market["state_name"]),
                    )
                    result = cursor.fetchone()
                    if result:
                        self.market_id_map[key] = result[0]
                cursor.close()
                return

            logger.info(
                f"Loading {len(filtered_market_data)} new markets (skipped {len(duplicates)} duplicates)"
            )

            # Create CSV-like data in memory
            csv_buffer = io.StringIO()
            for market in filtered_market_data:
                # Format: name,state_name
                name = (
                    market["name"]
                    .replace("\\", "\\\\")
                    .replace("\n", "\\n")
                    .replace("\t", "\\t")
                )
                state_name = market["state_name"] or "\\N"  # \N represents NULL in COPY
                csv_buffer.write(f"{name}\t{state_name}\n")

            csv_buffer.seek(0)

            # Execute COPY command
            cursor.copy_expert(
                "COPY markets (name, state_name) FROM STDIN WITH (FORMAT text, NULL '\\N', DELIMITER E'\\t')",
                csv_buffer,
            )

            self.pg_conn.commit()

            # Fetch inserted data to build ID map
            cursor.execute("SELECT id, name, state_name FROM markets")
            for row in cursor.fetchall():
                market_id, name, state_name = row
                cache_key = f"{name}|{state_name or 'NULL'}"
                self.market_id_map[cache_key] = market_id

            cursor.close()
            logger.info(f"✅ Loaded {len(filtered_market_data)} markets via COPY")

        except Exception as e:
            self.pg_conn.rollback()
            logger.error(f"Error loading markets via COPY: {e}")
            raise

    # ============================================================================
    # HOSTS - Batch Loading
    # ============================================================================

    def _prepare_host_data(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Prepare host data for batch insertion."""
        host_columns = ["Property Manager/ Host ID", "Host URL", "Super Host"]
        available_host_cols = [col for col in host_columns if col in df.columns]

        if not available_host_cols:
            return []

        unique_hosts = df.drop_duplicates(
            subset=["Property Manager/ Host ID"], keep="first"
        )
        host_data = []

        for _, row in unique_hosts.iterrows():
            host_id = row.get("Property Manager/ Host ID")
            if pd.isna(host_id) or host_id == "":
                continue

            host_url = row.get("Host URL")
            if pd.isna(host_url) or host_url == "":
                # Try to extract from URL
                extracted_id = self._extract_host_id_from_url(host_url)
                if not extracted_id:
                    continue
                host_id = extracted_id

            host_data.append(
                {
                    "airbnb_host_id": str(host_id),
                    "airbnb_host_url": row.get("Host URL")
                    if not pd.isna(row.get("Host URL"))
                    else None,
                    "is_super_host": row.get("Super Host")
                    if not pd.isna(row.get("Super Host"))
                    else None,
                }
            )

        return host_data

    def _load_hosts_batch(self, host_data: List[Dict[str, Any]]) -> None:
        """Load hosts using Supabase batch insert API."""
        if not host_data:
            return

        logger.info(f"Loading {len(host_data)} hosts using batch insert...")

        try:
            # Insert in batches
            for i in range(0, len(host_data), self.batch_size):
                batch = host_data[i : i + self.batch_size]
                response = self.client.table("hosts").insert(batch).execute()

                # Build ID map
                for host in response.data:
                    self.host_id_map[host["airbnb_host_id"]] = host["id"]

            logger.info(f"✅ Loaded {len(host_data)} hosts")

        except Exception as e:
            logger.error(f"Error loading hosts in batch: {e}")
            raise

    def _load_hosts_copy(self, host_data: List[Dict[str, Any]]) -> None:
        """Load hosts using PostgreSQL COPY command with temp table upsert."""
        if not host_data:
            return

        logger.info(f"Loading {len(host_data)} hosts using COPY with temp table upsert...")

        try:
            cursor = self.pg_conn.cursor()

            # Create temp table if it doesn't exist
            cursor.execute("""
                CREATE TEMP TABLE IF NOT EXISTS hosts_temp (
                    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
                    airbnb_host_id VARCHAR(255) UNIQUE,
                    airbnb_host_url TEXT,
                    is_super_host BOOLEAN DEFAULT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)

            # Clear temp table
            cursor.execute("TRUNCATE TABLE hosts_temp")

            # Create CSV-like data in memory
            csv_buffer = io.StringIO()
            for host in host_data:
                # Format: airbnb_host_id,airbnb_host_url,is_super_host
                airbnb_host_id = (
                    host["airbnb_host_id"]
                    .replace("\\", "\\\\")
                    .replace("\n", "\\n")
                    .replace("\t", "\\t")
                )
                airbnb_host_url = host.get("airbnb_host_url") or "\\N"
                is_super_host = host.get("is_super_host")
                if is_super_host is None:
                    is_super_host = "\\N"
                else:
                    is_super_host = "t" if is_super_host else "f"
                csv_buffer.write(
                    f"{airbnb_host_id}\t{airbnb_host_url}\t{is_super_host}\n"
                )

            csv_buffer.seek(0)

            # Execute COPY command to temp table
            cursor.copy_expert(
                "COPY hosts_temp (airbnb_host_id, airbnb_host_url, is_super_host) FROM STDIN WITH (FORMAT text, NULL '\\N', DELIMITER E'\\t')",
                csv_buffer,
            )

            # Call upsert function to move data from temp to main table
            cursor.execute("SELECT * FROM upsert_hosts_from_temp()")
            inserted, updated = cursor.fetchone()

            logger.info(f"  Hosts upserted: {inserted} inserted, {updated} updated")

            self.pg_conn.commit()

            # Fetch all hosts to build ID map (including existing ones)
            cursor.execute("SELECT id, airbnb_host_id FROM hosts")
            for row in cursor.fetchall():
                host_id, airbnb_host_id = row
                self.host_id_map[airbnb_host_id] = host_id

            cursor.close()
            logger.info(f"✅ Loaded {len(host_data)} hosts via COPY with upsert")

        except Exception as e:
            self.pg_conn.rollback()
            logger.error(f"Error loading hosts via COPY: {e}")
            raise

    # ============================================================================
    # PROPERTIES - Batch Loading
    # ============================================================================

    def _prepare_property_data(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Prepare property data for batch insertion."""
        column_mapping = {
            "property_id": "property_id",
            "listing_name": "listing_name",
            "description": "description_clean",
            "latitude": "latitude",
            "longitude": "longitude",
            "zipcode": "Zip Code",
            "city_name": "City",
            "bedrooms": "bedrooms",
            "bathrooms": "bathrooms",
            "accommodates": "Accommodates",
            "property_type": "Property Type",
            "room_type": "Room Type",
            "beds": "beds",
            "price_tier": "price_tier_num",
            "instant_book": "Instant Book",
            "min_stay": "Min Stay",
            "is_guest_favorite": "Guest Favorite",
            "is_reliable_data": "is_reliable_data",
            "airbnb_listing_url": "Airbnb URL",
            "vrbo_listing_url": "VRBO URL",
            "title": "TITLE",
        }

        property_data = []

        for _, row in df.iterrows():
            # Get market ID
            market_name = row.get("market")
            if market_name:
                parts = market_name.split("_")
                state_name = (
                    parts[-1] if len(parts) > 1 and len(parts[-1]) == 2 else None
                )
                clean_market_name = " ".join(parts[:-1]) if state_name else market_name
                cache_key = f"{clean_market_name}|{state_name or 'NULL'}"
                market_id = self.market_id_map.get(cache_key)
            else:
                market_id = None

            # Get host ID
            host_id_raw = row.get("Property Manager/ Host ID")
            if pd.isna(host_id_raw) or host_id_raw == "":
                host_id = None
            else:
                host_id = self.host_id_map.get(str(host_id_raw))

            # Build property data
            prop_data = {
                "market_id": market_id,
                "host_id": host_id,
            }

            # Map columns
            for db_col, csv_col in column_mapping.items():
                if csv_col in df.columns:
                    val = row[csv_col]
                    if not pd.isna(val):
                        prop_data[db_col] = val

            # Handle boolean conversions
            for bool_col in ["instant_book", "is_guest_favorite", "is_reliable_data"]:
                if bool_col in prop_data:
                    val = prop_data[bool_col]
                    if isinstance(val, str):
                        prop_data[bool_col] = val.lower() in ("true", "yes", "1", "t")
                    elif pd.isna(val):
                        prop_data[bool_col] = None

            property_data.append(prop_data)

        return property_data

    def _load_properties_batch(self, property_data: List[Dict[str, Any]]) -> None:
        """Load properties using Supabase batch insert API with upsert."""
        if not property_data:
            return

        logger.info(f"Loading {len(property_data)} properties using batch insert...")

        inserted_count = 0
        updated_count = 0

        try:
            # Process in batches
            for i in range(0, len(property_data), self.batch_size):
                batch = property_data[i : i + self.batch_size]

                # Use upsert to handle duplicates
                response = (
                    self.client.table("properties")
                    .upsert(batch, on_conflict="property_id", ignore_duplicates=False)
                    .execute()
                )

                # Build ID map
                for prop in response.data:
                    self.property_id_map[str(prop["property_id"])] = prop["id"]

                logger.info(
                    f"  Processed batch {i // self.batch_size + 1}: {len(response.data)} records"
                )

            logger.info(f"✅ Loaded {len(property_data)} properties")

        except Exception as e:
            logger.error(f"Error loading properties in batch: {e}")
            raise

    def _load_properties_copy(self, property_data: List[Dict[str, Any]]) -> None:
        """Load properties using PostgreSQL COPY command with temp table upsert."""
        if not property_data:
            return

        logger.info(f"Loading {len(property_data)} properties using COPY with temp table upsert...")

        try:
            cursor = self.pg_conn.cursor()

            # Create temp table if it doesn't exist
            cursor.execute("""
                CREATE TEMP TABLE IF NOT EXISTS properties_temp (
                    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
                    market_id UUID,
                    host_id UUID,
                    property_id VARCHAR(255) NOT NULL UNIQUE,
                    airbnb_listing_url TEXT,
                    vrbo_listing_url TEXT,
                    title VARCHAR(500),
                    listing_name VARCHAR(500),
                    description TEXT,
                    latitude DOUBLE PRECISION,
                    longitude DOUBLE PRECISION,
                    zipcode VARCHAR(20),
                    city_name VARCHAR(100),
                    bedrooms NUMERIC,
                    bathrooms NUMERIC,
                    accommodates INTEGER,
                    property_type VARCHAR(100),
                    room_type VARCHAR(100),
                    beds INTEGER,
                    price_tier INTEGER,
                    instant_book BOOLEAN,
                    min_stay INTEGER,
                    is_guest_favorite BOOLEAN DEFAULT FALSE,
                    is_reliable_data BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)

            # Clear temp table
            cursor.execute("TRUNCATE TABLE properties_temp")

            # Create CSV-like data in memory
            csv_buffer = io.StringIO()
            columns = [
                "market_id",
                "host_id",
                "property_id",
                "listing_name",
                "description",
                "latitude",
                "longitude",
                "zipcode",
                "city_name",
                "bedrooms",
                "bathrooms",
                "accommodates",
                "property_type",
                "room_type",
                "beds",
                "price_tier",
                "instant_book",
                "min_stay",
                "is_guest_favorite",
                "is_reliable_data",
                "airbnb_listing_url",
                "vrbo_listing_url",
                "title",
            ]

            # Columns that should be integers (not floats) based on schema
            integer_columns = {"accommodates", "beds", "price_tier", "min_stay"}

            for prop in property_data:
                values = []
                for col in columns:
                    val = prop.get(col)
                    if val is None or pd.isna(val):
                        values.append("\\N")
                    elif isinstance(val, bool):
                        values.append("t" if val else "f")
                    elif isinstance(val, (int, float)):
                        # Convert to integer for integer columns
                        if col in integer_columns and isinstance(val, float):
                            values.append(str(int(val)))
                        else:
                            values.append(str(val))
                    else:
                        # Escape special characters
                        str_val = (
                            str(val)
                            .replace("\\", "\\\\")
                            .replace("\n", "\\n")
                            .replace("\t", "\\t")
                        )
                        values.append(str_val)
                csv_buffer.write("\t".join(values) + "\n")

            csv_buffer.seek(0)

            # Execute COPY command to temp table
            cursor.copy_expert(
                f"COPY properties_temp ({', '.join(columns)}) FROM STDIN WITH (FORMAT text, NULL '\\N', DELIMITER E'\\t')",
                csv_buffer,
            )

            # Call upsert function to move data from temp to main table
            cursor.execute("SELECT * FROM upsert_properties_from_temp()")
            inserted, updated = cursor.fetchone()

            logger.info(f"  Properties upserted: {inserted} inserted, {updated} updated")

            self.pg_conn.commit()

            # Fetch all properties to build ID map (including existing ones)
            cursor.execute("SELECT id, property_id FROM properties")
            for row in cursor.fetchall():
                prop_id, property_id = row
                self.property_id_map[str(property_id)] = prop_id

            cursor.close()
            logger.info(f"✅ Loaded {len(property_data)} properties via COPY with upsert")

        except Exception as e:
            self.pg_conn.rollback()
            logger.error(f"Error loading properties via COPY: {e}")
            raise

    # ============================================================================
    # AMENITIES - Batch Loading
    # ============================================================================

    def _prepare_amenity_data(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Prepare amenity data for batch insertion."""
        if "amenities" not in df.columns:
            return []

        amenity_data = []

        for _, row in df.iterrows():
            property_id = row.get("property_id")
            if property_id not in self.property_id_map:
                continue

            property_uuid = self.property_id_map[property_id]
            amenities_dict = self._parse_amenities(row.get("amenities", ""))

            if not amenities_dict:
                continue

            amenity_data.append(
                {
                    "property_id": property_uuid,
                    "amenities": json.dumps(amenities_dict),
                }
            )

        return amenity_data

    def _load_amenities_batch(self, amenity_data: List[Dict[str, Any]]) -> None:
        """Load amenities using Supabase batch insert API."""
        if not amenity_data:
            return

        logger.info(
            f"Loading {len(amenity_data)} amenity records using batch insert..."
        )

        try:
            # Process in batches
            for i in range(0, len(amenity_data), self.batch_size):
                batch = amenity_data[i : i + self.batch_size]

                # Use upsert
                self.client.table("property_amenities").upsert(
                    batch, on_conflict="property_id", ignore_duplicates=False
                ).execute()

                logger.info(
                    f"  Processed batch {i // self.batch_size + 1}: {len(batch)} records"
                )

            logger.info(f"✅ Loaded {len(amenity_data)} amenity records")

        except Exception as e:
            logger.error(f"Error loading amenities in batch: {e}")
            raise

    def _load_amenities_copy(self, amenity_data: List[Dict[str, Any]]) -> None:
        """Load amenities using PostgreSQL COPY command with temp table upsert."""
        if not amenity_data:
            return

        logger.info(
            f"Loading {len(amenity_data)} amenity records using COPY with temp table upsert..."
        )

        # Create a separate connection for this thread to avoid conflicts
        conn_string = os.environ.get("SUPABASE_DB_CONNECTION_STRING")
        if not conn_string:
            logger.error("SUPABASE_DB_CONNECTION_STRING not found")
            raise ValueError("SUPABASE_DB_CONNECTION_STRING environment variable is required")

        try:
            # Create separate connection for parallel execution
            pg_conn = psycopg2.connect(conn_string, connect_timeout=30)
            pg_conn.autocommit = False
            cursor = pg_conn.cursor()

            # Create temp table if it doesn't exist
            cursor.execute("""
                CREATE TEMP TABLE IF NOT EXISTS property_amenities_temp (
                    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
                    property_id UUID NOT NULL UNIQUE,
                    amenities JSONB NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)

            # Clear temp table
            cursor.execute("TRUNCATE TABLE property_amenities_temp")

            # Create CSV-like data in memory
            csv_buffer = io.StringIO()
            for amenity in amenity_data:
                property_id = amenity["property_id"]
                amenities_json = (
                    amenity["amenities"]
                    .replace("\\", "\\\\")
                    .replace("\n", "\\n")
                    .replace("\t", "\\t")
                )
                csv_buffer.write(f"{property_id}\t{amenities_json}\n")

            csv_buffer.seek(0)

            # Execute COPY command to temp table
            cursor.copy_expert(
                "COPY property_amenities_temp (property_id, amenities) FROM STDIN WITH (FORMAT text, NULL '\\N', DELIMITER E'\\t')",
                csv_buffer,
            )

            # Call upsert function to move data from temp to main table
            cursor.execute("SELECT * FROM upsert_property_amenities_from_temp()")
            inserted, updated = cursor.fetchone()

            logger.info(f"  Amenities upserted: {inserted} inserted, {updated} updated")

            pg_conn.commit()
            cursor.close()
            pg_conn.close()
            logger.info(f"✅ Loaded {len(amenity_data)} amenity records via COPY with upsert")

        except Exception as e:
            if 'pg_conn' in locals():
                pg_conn.rollback()
                pg_conn.close()
            logger.error(f"Error loading amenities via COPY: {e}")
            raise

    # ============================================================================
    # PERFORMANCE - Batch Loading
    # ============================================================================

    def _prepare_performance_data(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Prepare performance data for batch insertion."""
        column_mapping = {
            "revenue": "Revenue",
            "revenue_potential": "Revenue Potential",
            "adr": "ADR",
            "cleaning_fee": "Cleaning Fee",
            "occupancy": "Occupancy",
            "available_nights": "Available Nights",
            "total_reviews": "total_reviews_clean",
            "rating": "Rating",
            "property_reviews_count": "Property Reviews",
            "high_season_reviews": "High Season Reviews",
            "high_season_label": "High Season Label",
        }

        performance_data = []

        for _, row in df.iterrows():
            property_id = row.get("property_id")
            if property_id not in self.property_id_map:
                continue

            property_uuid = self.property_id_map[property_id]

            perf_data = {"property_id": property_uuid}

            for db_col, csv_col in column_mapping.items():
                if csv_col in df.columns:
                    val = row[csv_col]
                    if not pd.isna(val):
                        perf_data[db_col] = val

            if not perf_data or len(perf_data) == 1:  # Only has property_id
                continue

            performance_data.append(perf_data)

        return performance_data

    def _load_performance_batch(self, performance_data: List[Dict[str, Any]]) -> None:
        """Load performance data using Supabase batch insert API."""
        if not performance_data:
            return

        logger.info(
            f"Loading {len(performance_data)} performance records using batch insert..."
        )

        try:
            # Process in batches
            for i in range(0, len(performance_data), self.batch_size):
                batch = performance_data[i : i + self.batch_size]

                # Use upsert
                self.client.table("property_performance").upsert(
                    batch, on_conflict="property_id", ignore_duplicates=False
                ).execute()

                logger.info(
                    f"  Processed batch {i // self.batch_size + 1}: {len(batch)} records"
                )

            logger.info(f"✅ Loaded {len(performance_data)} performance records")

        except Exception as e:
            logger.error(f"Error loading performance in batch: {e}")
            raise

    def _load_performance_copy(self, performance_data: List[Dict[str, Any]]) -> None:
        """Load performance data using PostgreSQL COPY command with temp table upsert."""
        if not performance_data:
            return

        logger.info(
            f"Loading {len(performance_data)} performance records using COPY with temp table upsert..."
        )

        # Create a separate connection for this thread to avoid conflicts
        conn_string = os.environ.get("SUPABASE_DB_CONNECTION_STRING")
        if not conn_string:
            logger.error("SUPABASE_DB_CONNECTION_STRING not found")
            raise ValueError("SUPABASE_DB_CONNECTION_STRING environment variable is required")

        try:
            # Create separate connection for parallel execution
            pg_conn = psycopg2.connect(conn_string, connect_timeout=30)
            pg_conn.autocommit = False
            cursor = pg_conn.cursor()

            # Create temp table if it doesn't exist
            cursor.execute("""
                CREATE TEMP TABLE IF NOT EXISTS property_performance_temp (
                    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
                    property_id UUID NOT NULL,
                    revenue NUMERIC,
                    revenue_potential NUMERIC,
                    adr NUMERIC,
                    cleaning_fee NUMERIC,
                    occupancy NUMERIC,
                    available_nights INTEGER,
                    total_reviews INTEGER,
                    rating NUMERIC,
                    property_reviews_count INTEGER,
                    high_season_reviews INTEGER,
                    high_season_label VARCHAR(50),
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)

            # Clear temp table
            cursor.execute("TRUNCATE TABLE property_performance_temp")

            # Create CSV-like data in memory
            columns = [
                "property_id",
                "revenue",
                "revenue_potential",
                "adr",
                "cleaning_fee",
                "occupancy",
                "available_nights",
                "total_reviews",
                "rating",
                "property_reviews_count",
                "high_season_reviews",
                "high_season_label",
            ]

            # Columns that should be integers (not floats) based on schema
            integer_columns = {"available_nights", "total_reviews", "property_reviews_count", "high_season_reviews"}

            csv_buffer = io.StringIO()
            for perf in performance_data:
                values = []
                for col in columns:
                    val = perf.get(col)
                    if val is None or pd.isna(val):
                        values.append("\\N")
                    elif isinstance(val, bool):
                        values.append("t" if val else "f")
                    elif isinstance(val, (int, float)):
                        # Convert to integer for integer columns
                        if col in integer_columns and isinstance(val, float):
                            values.append(str(int(val)))
                        else:
                            values.append(str(val))
                    else:
                        str_val = (
                            str(val)
                            .replace("\\", "\\\\")
                            .replace("\n", "\\n")
                            .replace("\t", "\\t")
                        )
                        values.append(str_val)
                csv_buffer.write("\t".join(values) + "\n")

            csv_buffer.seek(0)

            # Execute COPY command to temp table
            cursor.copy_expert(
                f"COPY property_performance_temp ({', '.join(columns)}) FROM STDIN WITH (FORMAT text, NULL '\\N', DELIMITER E'\\t')",
                csv_buffer,
            )

            # Call upsert function to move data from temp to main table
            cursor.execute("SELECT * FROM upsert_property_performance_from_temp()")
            inserted, updated = cursor.fetchone()

            logger.info(f"  Performance records upserted: {inserted} inserted, {updated} updated")

            pg_conn.commit()
            cursor.close()
            pg_conn.close()
            logger.info(
                f"✅ Loaded {len(performance_data)} performance records via COPY with upsert"
            )

        except Exception as e:
            if 'pg_conn' in locals():
                pg_conn.rollback()
                pg_conn.close()
            logger.error(f"Error loading performance via COPY: {e}")
            raise

    # ============================================================================
    # MAIN LOADING ORCHESTRATION
    # ============================================================================

    def load_all(self) -> None:
        """
        Load all data from the cleaned CSV file into the database.

        Uses the most efficient loading strategy available:
        1. PostgreSQL COPY with temp tables (if DB credentials available):
           - COPY data into temp tables (fast bulk load)
           - INSERT...ON CONFLICT to upsert from temp to main tables
           - Provides both speed and proper duplicate handling
        2. Supabase batch insert API (fallback)
        """
        # Check if cleaned data file exists
        if not Path(self.cleaned_data_path).exists():
            logger.error(f"Cleaned data file not found: {self.cleaned_data_path}")
            raise FileNotFoundError(
                f"Cleaned data file not found: {self.cleaned_data_path}"
            )

        logger.info(f"Loading data from {self.cleaned_data_path}")
        logger.info(
            f"Strategy: {'PostgreSQL COPY with Temp Tables (upsert enabled)' if self.use_copy_command else 'Supabase Batch Insert'}"
        )
        logger.info(f"Batch size: {self.batch_size}")

        # Load cleaned data
        df = pd.read_csv(self.cleaned_data_path)

        # Apply limit if specified (for testing)
        if self.limit:
            df = df.head(self.limit)
            logger.info(f"Limited to {self.limit} rows for testing")

        logger.info(f"Loaded {len(df)} rows from cleaned data")

        # Connect to databases
        self.connect_supabase()
        if self.use_copy_command:
            self.connect_postgres()

        try:
            # Prepare data for all tables
            logger.info("=" * 60)
            logger.info("STEP 1: Preparing data")
            logger.info("=" * 60)

            market_data = self._prepare_market_data(df)
            host_data = self._prepare_host_data(df)

            # Load markets and hosts first (they don't depend on other tables)
            logger.info("=" * 60)
            logger.info("STEP 2: Loading reference data (markets, hosts)")
            logger.info("=" * 60)

            if self.use_copy_command:
                self._load_markets_copy(market_data)
                self._load_hosts_copy(host_data)
            else:
                self._load_markets_batch(market_data)
                self._load_hosts_batch(host_data)

            # Prepare and load properties
            logger.info("=" * 60)
            logger.info("STEP 3: Loading properties")
            logger.info("=" * 60)

            property_data = self._prepare_property_data(df)
            if self.use_copy_command:
                self._load_properties_copy(property_data)
            else:
                self._load_properties_batch(property_data)

            # Load amenities and performance (can be done in parallel)
            logger.info("=" * 60)
            logger.info("STEP 4: Loading amenities and performance data")
            logger.info("=" * 60)

            amenity_data = self._prepare_amenity_data(df)
            performance_data = self._prepare_performance_data(df)

            # Load in parallel using ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = []

                if amenity_data:
                    if self.use_copy_command:
                        futures.append(
                            executor.submit(self._load_amenities_copy, amenity_data)
                        )
                    else:
                        futures.append(
                            executor.submit(self._load_amenities_batch, amenity_data)
                        )

                if performance_data:
                    if self.use_copy_command:
                        futures.append(
                            executor.submit(
                                self._load_performance_copy, performance_data
                            )
                        )
                    else:
                        futures.append(
                            executor.submit(
                                self._load_performance_batch, performance_data
                            )
                        )

                # Wait for all tasks to complete
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        logger.error(f"Error in parallel loading: {e}")
                        raise

            logger.info("=" * 60)
            logger.info("✅ All data loaded successfully!")
            logger.info("=" * 60)
            logger.info(f"Summary:")
            logger.info(f"  - Markets: {len(self.market_id_map)}")
            logger.info(f"  - Hosts: {len(self.host_id_map)}")
            logger.info(f"  - Properties: {len(self.property_id_map)}")
            logger.info(f"  - Amenities: {len(amenity_data)}")
            logger.info(f"  - Performance: {len(performance_data)}")

        except Exception as e:
            logger.error(f"Error during data loading: {e}")
            raise
        finally:
            self.disconnect()


def main():
    """Main entry point for batch data loading."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Load cleaned property data into the database using batch operations"
    )
    parser.add_argument(
        "--data-path",
        default="data/cleaned_combined_properties.csv",
        help="Path to the cleaned CSV file (default: data/cleaned_combined_properties.csv)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of properties to load (for testing, e.g., --limit 10)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Number of records per batch (default: 500)",
    )
    parser.add_argument(
        "--no-copy",
        action="store_true",
        help="Disable PostgreSQL COPY command, use Supabase batch insert instead",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of parallel workers (default: 4)",
    )

    args = parser.parse_args()

    try:
        loader = BatchDataLoader(
            cleaned_data_path=args.data_path,
            limit=args.limit,
            batch_size=args.batch_size,
            use_copy_command=not args.no_copy,
            max_workers=args.workers,
        )
        loader.load_all()
    except Exception as e:
        logger.error(f"Data loading failed: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
