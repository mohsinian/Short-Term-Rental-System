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
from batch_load_data import BatchDataLoader


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


def run_load_step(data_path: str = "data/cleaned_combined_properties.csv", limit: Optional[int] = None, use_batch: bool = False, batch_size: int = 500, use_copy: bool = True, workers: int = 4) -> bool:
    """
    Run the data loading step.

    Args:
        data_path: Path to the cleaned CSV file.
        limit: Optional limit on number of properties to load (for testing).
        use_batch: Whether to use batch loading (much faster).
        batch_size: Number of records per batch for batch loading.
        use_copy: Whether to use PostgreSQL COPY command (requires DB credentials).
        workers: Number of parallel workers for batch loading.

    Returns:
        True if successful, False otherwise.
    """
    logger.info("=" * 60)
    logger.info("STEP 2: Loading Data to Database")
    logger.info("=" * 60)
    
    if use_batch:
        logger.info("🚀 Using BATCH loading mode (10-100x faster)")
        logger.info(f"   Strategy: {'PostgreSQL COPY' if use_copy else 'Supabase Batch Insert'}")
        logger.info(f"   Batch size: {batch_size}")
        logger.info(f"   Parallel workers: {workers}")
    else:
        logger.info("📝 Using STANDARD loading mode (row-by-row)")

    try:
        if use_batch:
            loader = BatchDataLoader(
                cleaned_data_path=data_path,
                limit=limit,
                batch_size=batch_size,
                use_copy_command=use_copy,
                max_workers=workers,
            )
        else:
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
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Use batch loading mode (10-100x faster than standard mode)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Number of records per batch for batch loading (default: 500)",
    )
    parser.add_argument(
        "--no-copy",
        action="store_true",
        help="Disable PostgreSQL COPY command, use Supabase batch insert instead (only with --batch)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of parallel workers for batch loading (default: 4)",
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
        success = run_load_step(
            args.data_path,
            args.limit,
            use_batch=args.batch,
            batch_size=args.batch_size,
            use_copy=not args.no_copy,
            workers=args.workers,
        )
    else:
        # Clean (and optionally load)
        clean_success = run_clean_step()
        if not clean_success:
            return 1

        if not args.clean_only:
            # Run load step after successful clean
            load_success = run_load_step(
                args.data_path,
                args.limit,
                use_batch=args.batch,
                batch_size=args.batch_size,
                use_copy=not args.no_copy,
                workers=args.workers,
            )
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
