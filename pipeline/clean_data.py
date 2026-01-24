import pandas as pd
import numpy as np
import re

# --- Helper Functions ---


def extract_numeric_from_string(val):
    """Extracts the first number found in a string."""
    if pd.isna(val):
        return np.nan
    if isinstance(val, (int, float)):
        return val
    match = re.search(r"([\d\.]+)", str(val))
    return float(match.group(1)) if match else np.nan


def strip_html_tags(text):
    """Removes HTML tags from a string."""
    if pd.isna(text):
        return ""
    return re.sub(r"<br\s*/?>|<[^>]+>", " ", str(text)).strip()


def parse_price_tier(val):
    """Extracts the numeric tier from strings like '5. Luxury'."""
    if pd.isna(val):
        return np.nan
    if isinstance(val, (int, float)):
        return int(val)
    match = re.search(r"(\d)", str(val))
    return int(match.group(1)) if match else np.nan


# --- Core Cleaning Function ---


def clean_market_data(df, market_name):
    """
    Applies cleaning rules to a single market dataframe.
    """
    # 1. Create a copy to avoid SettingWithCopy warnings
    df_clean = df.copy()

    # Add market identifier
    df_clean["market"] = market_name

    # 2. Drop Low Value Columns
    cols_to_drop = [
        "Airbnb Host URL",
        "url",
        "error_reason",
        "Location",
        "Quality Rating Reason",
        "id",  # Dropping scientific notation ID in favor of Property ID
    ]
    df_clean.drop(
        columns=[col for col in cols_to_drop if col in df_clean.columns], inplace=True
    )

    # 3. Deduplicate / Merge Columns

    # Property ID: Ensure it is string
    df_clean["property_id"] = df_clean["Property ID"].astype(str)

    # Listing Name: COALESCE logic
    df_clean["listing_name"] = (
        df_clean["Listing Name"]
        .fillna(df_clean["TITLE"])
        .fillna(df_clean["name"])
        .fillna(df_clean["title"])
    )

    # Bedrooms: Prioritize Uppercase BEDROOMS, fallback to lowercase
    if "BEDROOMS" in df_clean.columns:
        df_clean["bedrooms"] = df_clean["BEDROOMS"]
    elif "bedrooms" in df_clean.columns:
        df_clean["bedrooms"] = df_clean["bedrooms"]
    else:
        df_clean["bedrooms"] = np.nan

    # Lat/Lon: Standardize to lowercase
    if "LATITUDE" in df_clean.columns:
        df_clean["latitude"] = df_clean["LATITUDE"].fillna(
            df_clean.get("latitude", np.nan)
        )
    elif "latitude" in df_clean.columns:
        df_clean["latitude"] = df_clean["latitude"]
    else:
        df_clean["latitude"] = np.nan

    if "LONGITUDE" in df_clean.columns:
        df_clean["longitude"] = df_clean["LONGITUDE"].fillna(
            df_clean.get("longitude", np.nan)
        )
    elif "longitude" in df_clean.columns:
        df_clean["longitude"] = df_clean["longitude"]
    else:
        df_clean["longitude"] = np.nan

    # Reviews: Merge multiple review count columns
    # Priority: total_reviews > review_total_reviews > reviewsCount > Property Reviews (if numeric)
    # Note: 'Property Reviews' might refer to the count or score in messy data, verify context.
    # Based on snippet: 'Property Reviews' was 120 vs 'total_reviews' 26.
    # We prioritize 'total_reviews' as it is explicit.
    df_clean["total_reviews_clean"] = (
        df_clean["total_reviews"]
        .fillna(df_clean["review_total_reviews"])
        .fillna(df_clean["reviewsCount"])
    )

    # Beds: Merge
    if "number_of_beds" in df_clean.columns:
        df_clean["beds"] = df_clean["number_of_beds"].fillna(
            df_clean.get("beds", np.nan)
        )
    elif "beds" in df_clean.columns:
        df_clean["beds"] = df_clean["beds"]
    else:
        df_clean["beds"] = np.nan

    # Baths: Prefer numeric BATHROOMS, otherwise extract number from string 'baths'
    if "BATHROOMS" in df_clean.columns:
        df_clean["bathrooms"] = df_clean["BATHROOMS"].fillna(
            df_clean.get("baths", pd.Series([np.nan] * len(df_clean))).apply(
                extract_numeric_from_string
            )
        )
    elif "baths" in df_clean.columns:
        df_clean["bathrooms"] = df_clean["baths"].apply(extract_numeric_from_string)
    else:
        df_clean["bathrooms"] = np.nan

    # 4. Type Conversions & Specific Formatting

    # Price Tier: Extract integer (e.g., "5. Luxury" -> 5)
    if "PRICE_TIER" in df_clean.columns:
        df_clean["price_tier_num"] = df_clean["PRICE_TIER"].apply(parse_price_tier)
    else:
        df_clean["price_tier_num"] = np.nan

    # Description: Strip HTML
    if "description" in df_clean.columns:
        df_clean["description_clean"] = df_clean["description"].apply(strip_html_tags)
    else:
        df_clean["description_clean"] = ""

    # Amenities: Just ensure it's a clean string for now (parsing to separate table usually happens in load)
    # Handling list-like strings if they exist
    if "amenities" in df_clean.columns:
        df_clean["amenities"] = df_clean["amenities"].astype(str)

    # 5. Data Quality Flag
    # Create a boolean flag for reliable data
    if "Data Quality Category" in df_clean.columns:
        df_clean["is_reliable_data"] = df_clean["Data Quality Category"].isin(
            ["Good Data", "Possibly Good Data"]
        )

    # 6. Handle specific numeric columns that might be read as strings (Revenue, etc)
    # The snippet suggests Revenue is numeric, but we can enforce it.
    money_cols = ["Revenue", "Revenue Potential", "ADR", "Cleaning Fee"]
    for col in money_cols:
        if col in df_clean.columns:
            df_clean[col] = pd.to_numeric(df_clean[col], errors="coerce")

    # 7. Select Final Columns (A subset of the most useful for the DB Schema)
    # We keep the raw columns needed for analysis and our cleaned versions

    # Optional: Drop raw duplicate columns to keep DF clean before export
    # We keep 'Property ID' for reference, but use 'property_id' as key.

    return df_clean


# --- Execution ---


def main():
    file_map = {
        "Blue Ridge": "data/Blue Ridge GA - Market Eval - FINAL - Base_Table.csv",
        "Bradenton": "data/Bradenton FL - Market Eval - FINAL - Base_Table.csv",
        "Indianapolis": "data/Indianapolis IN - FINAL - Base_Table.csv",
    }

    all_dfs = []

    for market, filename in file_map.items():
        print(f"Processing {market} from {filename}...")
        try:
            # Load CSV
            df = pd.read_csv(filename)

            # Clean
            cleaned_df = clean_market_data(df, market)

            all_dfs.append(cleaned_df)
            print(f"  -> Loaded {len(cleaned_df)} properties.")

        except FileNotFoundError:
            print(f"  -> File {filename} not found. Skipping.")

    # Combine all markets
    if all_dfs:
        final_df = pd.concat(all_dfs, ignore_index=True)

        # Final Deduplication: In case a property appears in multiple CSVs (unlikely given file structure, but good practice)
        # We drop duplicates based on property_id, keeping the first occurrence
        final_df.drop_duplicates(subset=["property_id"], keep="first", inplace=True)

        print("\n--- Cleaning Complete ---")
        print(f"Total Properties: {len(final_df)}")
        print(f"Columns: {len(final_df.columns)}")

        # Export to CSV for checking or next step
        output_path = "data/cleaned_combined_properties.csv"
        final_df.to_csv(output_path, index=False)
        print(f"Saved to '{output_path}'")

        return final_df
    else:
        print("No data processed.")
        return None


if __name__ == "__main__":
    df = main()
