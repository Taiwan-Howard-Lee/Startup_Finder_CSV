#!/usr/bin/env python3
"""
Deduplicate Startups

This script cleans and deduplicates startup names in a CSV file using LLM-based processing.
"""

import os
import sys
import time
import argparse
import logging
from typing import Optional

# Import setup_env to ensure API keys are available
import sys
import os

# Add the root directory to the path to import setup_env
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import setup_env

# Import the startup name cleaner
from .startup_name_cleaner import clean_and_deduplicate_startups

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
        logging.FileHandler(os.path.join(log_dir, f"deduplication_{time.strftime('%Y%m%d')}.log"))
    ]
)
logger = logging.getLogger(__name__)

def find_latest_csv() -> Optional[str]:
    """
    Find the latest CSV file in the output/data directory.

    Returns:
        Path to the latest CSV file or None if not found
    """
    try:
        data_dir = os.path.join(root_dir, "output/data")
        if not os.path.exists(data_dir):
            return None

        # Get all CSV files
        csv_files = [os.path.join(data_dir, f) for f in os.listdir(data_dir) if f.endswith(".csv")]

        if not csv_files:
            return None

        # Sort by modification time (newest first)
        csv_files.sort(key=os.path.getmtime, reverse=True)

        return csv_files[0]
    except Exception as e:
        logger.error(f"Error finding latest CSV file: {e}")
        return None

def main():
    """Main function to run the deduplication."""
    parser = argparse.ArgumentParser(description="Clean and deduplicate startup names in a CSV file")
    parser.add_argument("--input-file", "-i", type=str, help="Path to input CSV file")
    parser.add_argument("--output-file", "-o", type=str, help="Path to output CSV file")
    parser.add_argument("--query", "-q", type=str, default="", help="Original search query for context")
    parser.add_argument("--latest", "-l", action="store_true", help="Use the latest CSV file in output/data")

    args = parser.parse_args()

    # Determine input file
    input_file = args.input_file

    if not input_file and args.latest:
        input_file = find_latest_csv()
        if input_file:
            logger.info(f"Using latest CSV file: {input_file}")
        else:
            logger.error("No CSV files found in output/data directory")
            return 1

    if not input_file:
        logger.error("No input file specified. Use --input-file or --latest")
        return 1

    if not os.path.exists(input_file):
        logger.error(f"Input file not found: {input_file}")
        return 1

    # Run the deduplication
    try:
        print(f"\n=== STARTUP NAME DEDUPLICATION ===")
        print(f"Input file: {input_file}")

        # Create default output file if not provided
        output_file = args.output_file
        if not output_file:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            output_dir = os.path.dirname(input_file)
            filename = os.path.basename(input_file)
            name, ext = os.path.splitext(filename)
            output_file = os.path.join(output_dir, f"{name}_deduplicated_{timestamp}{ext}")

        print(f"Output file: {output_file}")
        print(f"Query context: {args.query or 'None'}")
        print("\nProcessing...")

        # Run the deduplication
        result_file = clean_and_deduplicate_startups(input_file, output_file, args.query)

        print(f"\nDeduplication complete!")
        print(f"Deduplicated file saved to: {result_file}")

        return 0

    except Exception as e:
        logger.error(f"Error during deduplication: {e}")
        print(f"\nError during deduplication: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
