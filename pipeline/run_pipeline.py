"""
Main pipeline script for the Short-Term Rental System.

This script orchestrates the complete data pipeline:
1. Clean raw CSV data
2. Load cleaned data into the database

Usage:
    python pipeline/run_pipeline.py              # Run full pipeline
    python pipeline/run_pipeline.py --clean-only # Run cleaning only
    python pipeline/run_pipeline.py --load-only  # Run loading only
    python pipeline/run_pipeline.py --load-only --limit 10  # Load only 10 properties
"""

import argparse
import logging
import sys
from typing import Optional

from clean_data import main as clean_main
from load_data import DataLoader


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_clean_step() -> bool:
    """
    Run the data cleaning step.

    Returns:
        True if successful, False otherwise.
    """
    logger.info("=" * 60)
    logger.info("STEP 1: Cleaning Data")
    logger.info("=" * 60)

    try:
        df = clean_main()
        if df is not None:
            logger.info("✅ Data cleaning completed successfully")
            logger.info(f"   Total properties cleaned: {len(df)}")
            return True
        else:
            logger.error("❌ Data cleaning returned no data")
            return False
    except Exception as e:
        logger.error(f"❌ Data cleaning failed: {e}")
        return False


def run_load_step(data_path: str = "data/cleaned_combined_properties.csv", limit: Optional[int] = None) -> bool:
    """
    Run the data loading step.

    Args:
        data_path: Path to the cleaned CSV file.
        limit: Optional limit on number of properties to load (for testing).

    Returns:
        True if successful, False otherwise.
    """
    logger.info("=" * 60)
    logger.info("STEP 2: Loading Data to Database")
    logger.info("=" * 60)

    try:
        loader = DataLoader(cleaned_data_path=data_path, limit=limit)
        loader.load_all()
        logger.info("✅ Data loading completed successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Data loading failed: {e}")
        return False


def main():
    """Main entry point for the pipeline."""
    parser = argparse.ArgumentParser(
        description="Run the Short-Term Rental data pipeline"
    )
    parser.add_argument(
        "--clean-only",
        action="store_true",
        help="Run only the data cleaning step"
    )
    parser.add_argument(
        "--load-only",
        action="store_true",
        help="Run only the data loading step"
    )
    parser.add_argument(
        "--data-path",
        default="data/cleaned_combined_properties.csv",
        help="Path to the cleaned CSV file (default: data/cleaned_combined_properties.csv)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of properties to load (for testing, e.g. --limit 10)",
    )

    args = parser.parse_args()

    # Validate arguments
    if args.clean_only and args.load_only:
        logger.error("Cannot specify both --clean-only and --load-only")
        return 1

    success = True

    # Run pipeline based on arguments
    if args.load_only:
        # Load only
        success = run_load_step(args.data_path, args.limit)
    else:
        # Clean (and optionally load)
        clean_success = run_clean_step()
        if not clean_success:
            return 1

        if not args.clean_only:
            # Run load step after successful clean
            load_success = run_load_step(args.data_path, args.limit)
            if not load_success:
                return 1

    # Summary
    logger.info("=" * 60)
    logger.info("Pipeline Summary")
    logger.info("=" * 60)

    if args.clean_only:
        logger.info("✅ Data cleaning completed")
    elif args.load_only:
        logger.info("✅ Data loading completed")
    else:
        logger.info("✅ Full pipeline completed successfully")

    logger.info("=" * 60)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
