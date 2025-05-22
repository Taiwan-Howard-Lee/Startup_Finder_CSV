#!/usr/bin/env python3
"""
Append Intermediate Results to CSV

This script appends intermediate results to an existing CSV file
instead of creating separate files for each stage of processing.
"""

import os
import sys
import csv
import time
import json
import logging
import argparse
from typing import List, Dict, Any, Optional

# Import setup_env to ensure API keys are available
import sys
import os

# Add the root directory to the path to import setup_env
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import setup_env

# Set up logging
# Get the root directory path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
log_dir = os.path.join(root_dir, "output/logs")
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(log_dir, f"append_results_{time.strftime('%Y%m%d')}.log"))
    ]
)
logger = logging.getLogger(__name__)

def find_latest_intermediate_file(base_dir: str = None) -> Optional[str]:
    """
    Find the latest intermediate result file.

    Args:
        base_dir: Directory to search for intermediate files

    Returns:
        Path to the latest intermediate file or None if not found
    """
    # Use the root directory to construct the absolute path
    if base_dir is None:
        base_dir = os.path.join(root_dir, "output/intermediate")
    try:
        if not os.path.exists(base_dir):
            return None

        # Get all CSV files
        csv_files = [os.path.join(base_dir, f) for f in os.listdir(base_dir) if f.endswith(".csv")]

        if not csv_files:
            return None

        # Sort by modification time (newest first)
        csv_files.sort(key=os.path.getmtime, reverse=True)

        return csv_files[0]
    except Exception as e:
        logger.error(f"Error finding latest intermediate file: {e}")
        return None

def append_to_csv(source_file: str, target_file: str, add_source_column: bool = True) -> bool:
    """
    Append data from source CSV to target CSV.

    Args:
        source_file: Path to source CSV file
        target_file: Path to target CSV file
        add_source_column: Whether to add a source column

    Returns:
        True if successful, False otherwise
    """
    try:
        # Read source file
        with open(source_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            source_rows = list(reader)

            if not source_rows:
                logger.warning(f"No data found in {source_file}")
                return False

            source_fieldnames = reader.fieldnames

        # Read target file
        with open(target_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            target_rows = list(reader)
            target_fieldnames = list(reader.fieldnames)

        # Check if we need to add a source column
        source_column = "Source File"
        if add_source_column and source_column not in target_fieldnames:
            target_fieldnames.append(source_column)

        # Add any missing fields from source to target
        for field in source_fieldnames:
            if field not in target_fieldnames:
                target_fieldnames.append(field)

        # Get existing company names to avoid duplicates
        existing_companies = set()
        name_column = "Company Name"

        if name_column in target_fieldnames:
            for row in target_rows:
                company_name = row.get(name_column, "").strip()
                if company_name:
                    existing_companies.add(company_name.lower())

        # Prepare rows to append
        rows_to_append = []
        for row in source_rows:
            # Check if this company already exists
            company_name = row.get(name_column, "").strip()
            if company_name and company_name.lower() in existing_companies:
                logger.info(f"Skipping duplicate company: {company_name}")
                continue

            # Add to existing companies set
            if company_name:
                existing_companies.add(company_name.lower())

            # Create a new row with all target fields
            new_row = {field: "" for field in target_fieldnames}

            # Copy data from source row
            for field in source_fieldnames:
                if field in row:
                    new_row[field] = row[field]

            # Add source information
            if add_source_column and source_column in target_fieldnames:
                new_row[source_column] = os.path.basename(source_file)

            rows_to_append.append(new_row)

        # Append to target file
        with open(target_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=target_fieldnames)
            writer.writeheader()

            # Write existing rows
            for row in target_rows:
                # Ensure row has all fields
                for field in target_fieldnames:
                    if field not in row:
                        row[field] = ""
                writer.writerow(row)

            # Write new rows
            for row in rows_to_append:
                writer.writerow(row)

        logger.info(f"Appended {len(rows_to_append)} rows from {source_file} to {target_file}")
        return True

    except Exception as e:
        logger.error(f"Error appending to CSV: {e}")
        return False

def main():
    """Main function to run the script."""
    parser = argparse.ArgumentParser(description="Append intermediate results to an existing CSV file")
    parser.add_argument("--source", "-s", type=str, help="Source CSV file (intermediate results)")
    parser.add_argument("--target", "-t", type=str, required=True, help="Target CSV file to append to")
    parser.add_argument("--latest", "-l", action="store_true", help="Use the latest intermediate file")
    parser.add_argument("--no-source-column", action="store_true", help="Don't add a source column")

    args = parser.parse_args()

    # Determine source file
    source_file = args.source

    if not source_file and args.latest:
        source_file = find_latest_intermediate_file()
        if source_file:
            logger.info(f"Using latest intermediate file: {source_file}")
        else:
            logger.error("No intermediate files found")
            return 1

    if not source_file:
        logger.error("No source file specified. Use --source or --latest")
        return 1

    if not os.path.exists(source_file):
        logger.error(f"Source file not found: {source_file}")
        return 1

    # Check target file
    if not os.path.exists(args.target):
        logger.error(f"Target file not found: {args.target}")
        return 1

    # Run the append operation
    print(f"\n=== APPENDING INTERMEDIATE RESULTS ===")
    print(f"Source file: {source_file}")
    print(f"Target file: {args.target}")
    print(f"Add source column: {not args.no_source_column}")
    print("\nProcessing...")

    success = append_to_csv(source_file, args.target, not args.no_source_column)

    if success:
        print(f"\nAppend operation complete!")
        print(f"Data from {source_file} has been appended to {args.target}")
        return 0
    else:
        print(f"\nAppend operation failed. See logs for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
