"""
Data ingestion module for loading cleaned property data into database.

This module reads the cleaned CSV file and populates the database tables
in the correct order respecting foreign key dependencies using supabase-py.
"""

import json
import logging
from typing import Dict, Optional, Union
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from supabase import Client

from src.database.supabase_client import get_supabase_client


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DataLoader:
    """
    Handles loading cleaned property data into database using supabase-py.
    """

    def __init__(
        self,
        cleaned_data_path: str = "data/cleaned_combined_properties.csv",
        limit: Optional[int] = None,
    ):
        """
        Initialize data loader.

        Args:
            cleaned_data_path: Path to the cleaned CSV file.
            limit: Optional limit on number of properties to load (for testing).
        """
        load_dotenv()
        self.cleaned_data_path = cleaned_data_path
        self.limit = limit
        self.client: Optional[Client] = None
        self.market_id_map: Dict[str, str] = {}  # Maps market name to UUID
        self.host_id_map: Dict[str, str] = {}  # Maps airbnb_host_id to UUID
        self.property_id_map: Dict[str, str] = {}  # Maps property_id to UUID

    def connect(self) -> None:
        """Establish Supabase client connection."""
        try:
            self.client = get_supabase_client()
            logger.info("Supabase client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            raise

    def disconnect(self) -> None:
        """Close Supabase client connection (no-op for supabase-py)."""
        # Supabase client doesn't require explicit closing
        logger.info("Supabase client session ended")

    def _parse_amenities(self, amenities_str: Union[str, float, None]) -> dict:
        """
        Parse amenities string into a JSONB-compatible dictionary.

        Args:
            amenities_str: String containing amenities data.

        Returns:
            Dictionary with amenities data.
        """
        if pd.isna(amenities_str) or amenities_str == "":
            return {}

        amenities_str = str(amenities_str).strip()

        # Try to parse as JSON first
        try:
            return json.loads(amenities_str)  # type: ignore
        except (json.JSONDecodeError, TypeError):
            pass

        # Try to parse as comma-separated list
        if "," in amenities_str:
            items = [item.strip() for item in amenities_str.split(",")]
            return {"list": items}

        # Return as single item
        return {"value": amenities_str}

    def _extract_host_id_from_url(self, url: Optional[str]) -> Optional[str]:
        """
        Extract Airbnb host ID from URL.

        Args:
            url: Airbnb host URL.

        Returns:
            Host ID string or None.
        """
        if pd.isna(url) or url == "":
            return None

        # Try to extract ID from URL patterns like:
        # https://www.airbnb.com/users/show/123456789
        # https://www.airbnb.com/u/123456789
        import re

        match = re.search(r"/users/show/(\d+)|/u/(\d+)", str(url) if url else "")
        if match:
            return match.group(1) or match.group(2)
        return None

    def _get_or_create_market(
        self, market_name: str, state_name: Optional[str] = None
    ) -> str:
        """
        Get existing market ID or create a new one using upsert logic.
        This ensures uniqueness on (name, state_name) combination.

        Args:
            market_name: Name of the market.
            state_name: Optional state name.

        Returns:
            Market UUID.
        """
        # Create a composite key for caching
        cache_key = f"{market_name}|{state_name or 'NULL'}"
        if cache_key in self.market_id_map:
            return self.market_id_map[cache_key]

        try:
            # Try to find existing market by both name and state_name
            query = self.client.table("markets").select("id").eq("name", market_name)
            if state_name:
                query = query.eq("state_name", state_name)
            else:
                query = query.is_("state_name", "null")
            
            response = query.execute()

            if response.data:
                market_id = response.data[0]["id"]
                logger.debug(f"Found existing market: {market_name} (state: {state_name})")
            else:
                # Use upsert to create new market or update if exists
                market_data = {"name": market_name}
                if state_name:
                    market_data["state_name"] = state_name

                # upsert will insert if not exists, or update if exists based on unique constraint
                response = self.client.table("markets").upsert(market_data).execute()
                market_id = response.data[0]["id"]
                logger.info(f"Upserted market: {market_name} (state: {state_name})")

            self.market_id_map[cache_key] = market_id
            return market_id

        except Exception as e:
            logger.error(f"Error getting/creating market {market_name} (state: {state_name}): {e}")
            raise

    def _get_or_create_host(
        self,
        airbnb_host_id: Optional[str],
        airbnb_host_url: Optional[str],
        is_super_host: Optional[bool] = None,
    ) -> Optional[str]:
        """
        Get existing host ID or create a new one.

        Args:
            airbnb_host_id: Airbnb host ID.
            airbnb_host_url: Airbnb host URL.
            is_super_host: Whether the host is a superhost.

        Returns:
            Host UUID or None if no host information provided.
        """
        # Try to extract host ID from URL if not provided
        if pd.isna(airbnb_host_id) or airbnb_host_id == "":
            if not pd.isna(airbnb_host_url) and airbnb_host_url != "":
                airbnb_host_id = self._extract_host_id_from_url(airbnb_host_url)  # type: ignore
            if not airbnb_host_id:
                return None

        airbnb_host_id = str(airbnb_host_id)

        if airbnb_host_id in self.host_id_map:
            return self.host_id_map[airbnb_host_id]

        try:
            # Try to find existing host
            response = (
                self.client.table("hosts")
                .select("id")
                .eq("airbnb_host_id", airbnb_host_id)
                .execute()
            )

            if response.data:
                host_id = response.data[0]["id"]
                logger.debug(f"Found existing host: {airbnb_host_id}")
            else:
                # Create new host
                host_data = {"airbnb_host_id": airbnb_host_id}
                if airbnb_host_url:
                    host_data["airbnb_host_url"] = airbnb_host_url
                if is_super_host is not None:
                    host_data["is_super_host"] = is_super_host

                response = self.client.table("hosts").insert(host_data).execute()
                host_id = response.data[0]["id"]
                logger.info(f"Created new host: {airbnb_host_id}")

            self.host_id_map[airbnb_host_id] = host_id
            return host_id

        except Exception as e:
            logger.error(f"Error getting/creating host {airbnb_host_id}: {e}")
            raise

    def _load_markets(self, df: pd.DataFrame) -> None:
        """
        Load unique markets from the dataframe.

        Args:
            df: Cleaned property dataframe.
        """
        if "market" not in df.columns:
            logger.warning("No 'market' column found in dataframe")
            return

        unique_markets = df["market"].unique()
        logger.info(f"Found {len(unique_markets)} unique markets")

        for market_name in unique_markets:
            # Extract state from market name (e.g., "Blue_Ridge_GA" -> "GA")
            parts = market_name.split("_")
            state_name = parts[-1] if len(parts) > 1 and len(parts[-1]) == 2 else None
            # Remove state from market name if it was extracted
            clean_market_name = " ".join(parts[:-1]) if state_name else market_name

            self._get_or_create_market(clean_market_name, state_name)

        logger.info(f"Loaded {len(self.market_id_map)} markets")

    def _load_hosts(self, df: pd.DataFrame) -> None:
        """
        Load unique hosts from the dataframe.

        Args:
            df: Cleaned property dataframe.
        """
        host_columns = ["Property Manager/ Host ID"]
        available_host_cols = [col for col in host_columns if col in df.columns]

        if not available_host_cols:
            logger.warning("No host columns found in dataframe")
            return

        logger.info("Loading hosts...")

        # Get unique host IDs with their associated data
        # We need to get the first occurrence of each host to get their URL and superhost status
        unique_hosts = df.drop_duplicates(subset=["Property Manager/ Host ID"], keep="first")

        for _, row in unique_hosts.iterrows():
            host_id = row.get("Property Manager/ Host ID")
            host_url = row.get("Host URL")
            is_super_host = row.get("Super Host")

            self._get_or_create_host(host_id, host_url, is_super_host)

        logger.info(f"Loaded {len(self.host_id_map)} hosts")

    def _load_properties(self, df: pd.DataFrame) -> None:
        """
        Load properties from the dataframe.

        Args:
            df: Cleaned property dataframe.
        """
        logger.info(f"Loading {len(df)} properties...")

        # Column mapping from CSV to database schema
        # Key = database column name, Value = CSV column name
        column_mapping = {
            "property_id": "property_id",
            "listing_name": "listing_name",
            "description": "description_clean",  # Maps CSV 'description_clean' to DB 'description'
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

        inserted_count = 0
        updated_count = 0

        for _, row in df.iterrows():
            try:
                # Get market ID
                market_name = row.get("market")
                if market_name:
                    # Extract state from market name (e.g., "Blue_Ridge_GA" -> "GA")
                    parts = market_name.split("_")
                    state_name = parts[-1] if len(parts) > 1 and len(parts[-1]) == 2 else None
                    # Remove state from market name if it was extracted
                    clean_market_name = " ".join(parts[:-1]) if state_name else market_name
                    market_id = self._get_or_create_market(clean_market_name, state_name)
                else:
                    market_id = None

                # Get host ID
                host_id = self._get_or_create_host(
                    row.get("Property Manager/ Host ID"),
                    row.get("Host URL"),
                    row.get("Super Host"),
                )

                # Build property data
                property_data = {
                    "market_id": market_id,
                    "host_id": host_id,
                }

                # Map columns
                for db_col, csv_col in column_mapping.items():
                    if csv_col in df.columns:
                        val = row[csv_col]
                        if not pd.isna(val):
                            property_data[db_col] = val

                # Handle boolean conversions
                for bool_col in [
                    "instant_book",
                    "is_guest_favorite",
                    "is_reliable_data",
                ]:
                    if bool_col in property_data:
                        val = property_data[bool_col]
                        if isinstance(val, str):
                            property_data[bool_col] = val.lower() in (
                                "true",
                                "yes",
                                "1",
                                "t",
                            )  # type: ignore
                        elif pd.isna(val):
                            property_data[bool_col] = None  # type: ignore

                # Check if property exists
                response = (
                    self.client.table("properties")
                    .select("id")
                    .eq("property_id", property_data["property_id"])
                    .execute()
                )

                if response.data:
                    # Update existing property
                    property_uuid = response.data[0]["id"]
                    update_cols = [k for k in property_data.keys() if k != "property_id"]
                    update_data = {k: property_data[k] for k in update_cols}

                    self.client.table("properties").update(update_data).eq(
                        "id", property_uuid
                    ).execute()

                    self.property_id_map[str(property_data["property_id"])] = (
                        property_uuid
                    )
                    updated_count += 1
                else:
                    # Insert new property
                    response = (
                        self.client.table("properties").insert(property_data).execute()
                    )
                    property_uuid = response.data[0]["id"]
                    self.property_id_map[str(property_data["property_id"])] = (
                        property_uuid
                    )
                    inserted_count += 1

            except Exception as e:
                logger.error(
                    f"Error loading property {row.get('property_id', 'unknown')}: {e}"
                )
                continue

        logger.info(
            f"Properties loaded: {inserted_count} inserted, {updated_count} updated"
        )

    def _load_amenities(self, df: pd.DataFrame) -> None:
        """
        Load property amenities from the dataframe.

        Args:
            df: Cleaned property dataframe.
        """
        if "amenities" not in df.columns:
            logger.warning("No 'amenities' column found in dataframe")
            return

        logger.info("Loading property amenities...")

        inserted_count = 0
        updated_count = 0

        for _, row in df.iterrows():
            property_id = row.get("property_id")
            if property_id not in self.property_id_map:
                continue

            property_uuid = self.property_id_map[property_id]
            amenities_data = self._parse_amenities(row.get("amenities", ""))

            if not amenities_data:
                continue

            try:
                # Check if amenities exist
                response = (
                    self.client.table("property_amenities")
                    .select("id")
                    .eq("property_id", property_uuid)
                    .execute()
                )

                if response.data:
                    # Update existing amenities
                    self.client.table("property_amenities").update(
                        {"amenities": amenities_data}
                    ).eq("property_id", property_uuid).execute()
                    updated_count += 1
                else:
                    # Insert new amenities
                    self.client.table("property_amenities").insert(
                        {"property_id": property_uuid, "amenities": amenities_data}
                    ).execute()
                    inserted_count += 1

            except Exception as e:
                logger.error(f"Error loading amenities for property {property_id}: {e}")
                continue

        logger.info(
            f"Amenities loaded: {inserted_count} inserted, {updated_count} updated"
        )

    def _load_performance(self, df: pd.DataFrame) -> None:
        """
        Load property performance data from the dataframe.

        Args:
            df: Cleaned property dataframe.
        """
        logger.info("Loading property performance data...")

        # Column mapping for performance data
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

        inserted_count = 0
        updated_count = 0

        for _, row in df.iterrows():
            property_id = row.get("property_id")
            if property_id not in self.property_id_map:
                continue

            property_uuid = self.property_id_map[property_id]

            # Build performance data
            performance_data = {}
            for db_col, csv_col in column_mapping.items():
                if csv_col in df.columns:
                    val = row[csv_col]
                    if not pd.isna(val):
                        performance_data[db_col] = val

            if not performance_data:
                continue

            try:
                # Check if performance data exists
                response = (
                    self.client.table("property_performance")
                    .select("id")
                    .eq("property_id", property_uuid)
                    .execute()
                )

                if response.data:
                    # Update existing performance data
                    self.client.table("property_performance").update(
                        performance_data
                    ).eq("property_id", property_uuid).execute()
                    updated_count += 1
                else:
                    # Insert new performance data
                    self.client.table("property_performance").insert(
                        {"property_id": property_uuid, **performance_data}
                    ).execute()
                    inserted_count += 1

            except Exception as e:
                logger.error(
                    f"Error loading performance for property {property_id}: {e}"
                )
                continue

        logger.info(
            f"Performance data loaded: {inserted_count} inserted, {updated_count} updated"
        )

    def load_all(self) -> None:
        """
        Load all data from the cleaned CSV file into the database.

        This method loads data in the correct order respecting foreign key dependencies:
        1. Markets
        2. Hosts
        3. Properties
        4. Property Amenities
        5. Property Performance
        """
        # Check if cleaned data file exists
        if not Path(self.cleaned_data_path).exists():
            logger.error(f"Cleaned data file not found: {self.cleaned_data_path}")
            raise FileNotFoundError(
                f"Cleaned data file not found: {self.cleaned_data_path}"
            )

        logger.info(f"Loading data from {self.cleaned_data_path}")

        # Load cleaned data
        df = pd.read_csv(self.cleaned_data_path)

        # Apply limit if specified (for testing)
        if self.limit:
            df = df.head(self.limit)
            logger.info(f"Limited to {self.limit} rows for testing")

        logger.info(f"Loaded {len(df)} rows from cleaned data")

        # Connect to Supabase
        self.connect()

        try:
            # Load data in dependency order
            self._load_markets(df)
            self._load_hosts(df)
            self._load_properties(df)
            self._load_amenities(df)
            self._load_performance(df)

            logger.info("All data loaded successfully!")

        except Exception as e:
            logger.error(f"Error during data loading: {e}")
            raise
        finally:
            self.disconnect()


def main():
    """Main entry point for data loading."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Load cleaned property data into the database"
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

    args = parser.parse_args()

    try:
        loader = DataLoader(cleaned_data_path=args.data_path, limit=args.limit)
        loader.load_all()
    except Exception as e:
        logger.error(f"Data loading failed: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
