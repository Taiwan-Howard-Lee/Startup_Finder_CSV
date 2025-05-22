#!/usr/bin/env python3
"""
Deduplicate and Overwrite Startups CSV

This script cleans and deduplicates startup names in a CSV file using LLM-based processing,
then overwrites the original file with the deduplicated data.
"""

import os
import sys
import csv
import time
import json
import logging
import argparse
from typing import List, Dict, Any, Set, Optional

# Import setup_env to ensure API keys are available
import sys
import os

# Add the root directory to the path to import setup_env
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import setup_env

# Import API client
from .api_client import GeminiAPIClient

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

def clean_startup_name(name: str) -> str:
    """
    Clean a startup name by removing common suffixes and normalizing.

    Args:
        name: Startup name to clean

    Returns:
        Cleaned startup name
    """
    import re

    # Remove common suffixes
    suffixes = [
        r'\s+Inc\.?$', r'\s+LLC\.?$', r'\s+Ltd\.?$', r'\s+Limited$',
        r'\s+Corp\.?$', r'\s+Corporation$', r'\s+Co\.?$', r'\s+Company$',
        r'\s+GmbH$', r'\s+S\.?A\.?$', r'\s+B\.?V\.?$', r'\s+P\.?L\.?C\.?$'
    ]

    for suffix in suffixes:
        name = re.sub(suffix, '', name, flags=re.IGNORECASE)

    # Remove quotes and special characters
    name = re.sub(r'[\'"`]', '', name)

    # Normalize whitespace
    name = re.sub(r'\s+', ' ', name).strip()

    return name

def deduplicate_with_llm(names: List[str], query: str) -> List[str]:
    """
    Deduplicate startup names using the Gemini API.

    Args:
        names: List of startup names to deduplicate
        query: Original search query for context

    Returns:
        Deduplicated list of startup names
    """
    # Initialize the API client
    api_client = GeminiAPIClient()

    # Create the prompt
    prompt = f"""
    You are a startup name standardization expert. Your task is to deduplicate and standardize a list of startup names.

    Original search query: {query}

    Below is a list of startup names that may contain duplicates or variations of the same company.
    Please deduplicate this list by:
    1. Identifying similar names that refer to the same company
    2. Standardizing the names with proper capitalization
    3. Removing unnecessary suffixes (Inc, LLC, Ltd, etc.)
    4. Ensuring consistency in formatting

    Return a JSON array of unique, standardized startup names.

    Startup names:
    {json.dumps(names, indent=2)}
    """

    try:
        # Call the LLM
        # Use the pro_model from the API client
        response = api_client.pro_model.generate_content(prompt)

        # Extract the JSON array from the response
        response_text = response.text

        # Find JSON array in the response
        json_start = response_text.find('[')
        json_end = response_text.rfind(']') + 1

        if json_start >= 0 and json_end > json_start:
            json_text = response_text[json_start:json_end]
            deduplicated_names = json.loads(json_text)

            logger.info(f"Deduplicated {len(names)} names to {len(deduplicated_names)} unique startups using LLM")
            return deduplicated_names

        # If JSON parsing fails, use basic deduplication
        logger.warning("Failed to parse LLM response, using basic deduplication")
        return basic_deduplication(names)

    except Exception as e:
        logger.error(f"Error deduplicating with LLM: {e}")
        # Fallback to basic deduplication
        return basic_deduplication(names)

def basic_deduplication(names: List[str]) -> List[str]:
    """
    Perform basic deduplication of startup names.

    Args:
        names: List of startup names to deduplicate

    Returns:
        Deduplicated list of startup names
    """
    # Clean all names
    cleaned_names = [clean_startup_name(name) for name in names]

    # Create a mapping of cleaned names to original names
    cleaned_to_original = {}
    for i, name in enumerate(names):
        cleaned = cleaned_names[i]
        if cleaned not in cleaned_to_original:
            cleaned_to_original[cleaned] = name

    # Get unique cleaned names
    unique_cleaned = list(cleaned_to_original.keys())

    # Map back to original names
    unique_names = [cleaned_to_original[cleaned] for cleaned in unique_cleaned]

    logger.info(f"Deduplicated {len(names)} names to {len(unique_names)} unique startups using basic deduplication")
    return unique_names

def deduplicate_csv(file_path: str, query: str = "") -> bool:
    """
    Deduplicate startup names in a CSV file and overwrite the original file.

    Args:
        file_path: Path to the CSV file
        query: Original search query for context

    Returns:
        True if successful, False otherwise
    """
    try:
        # Read the CSV file
        with open(file_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

            if not rows:
                logger.warning(f"No data found in {file_path}")
                return False

            # Get the field names
            fieldnames = reader.fieldnames

            # Extract startup names
            name_column = "Company Name"  # Assuming this is the column name
            names = [row.get(name_column, "") for row in rows if row.get(name_column)]

            if not names:
                logger.warning(f"No startup names found in column '{name_column}'")
                return False

            logger.info(f"Found {len(names)} startup names in {file_path}")

            # Deduplicate names
            deduplicated_names = deduplicate_with_llm(names, query)

            # Create a mapping of original names to rows
            name_to_rows = {}
            for row in rows:
                name = row.get(name_column, "")
                if name:
                    name_to_rows[name] = row

            # Create output rows with deduplicated names
            output_rows = []
            for name in deduplicated_names:
                # Check if we have a row for this name
                if name in name_to_rows:
                    row = name_to_rows[name].copy()
                    output_rows.append(row)
                else:
                    # This is a standardized name that doesn't match any original
                    # Try to find a similar name in the original data
                    cleaned_name = clean_startup_name(name)
                    for orig_name, row in name_to_rows.items():
                        if clean_startup_name(orig_name) == cleaned_name:
                            new_row = row.copy()
                            new_row[name_column] = name  # Use the standardized name
                            output_rows.append(new_row)
                            break

            # Write the deduplicated data back to the file
            if output_rows:
                # Create a backup of the original file
                backup_file = f"{file_path}.bak"
                os.rename(file_path, backup_file)
                logger.info(f"Created backup of original file: {backup_file}")

                # Write the deduplicated data
                with open(file_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(output_rows)

                logger.info(f"Wrote {len(output_rows)} deduplicated startups to {file_path}")
                return True
            else:
                logger.warning("No output rows generated")
                return False

    except Exception as e:
        logger.error(f"Error deduplicating CSV: {e}")
        return False

def main():
    """Main function to run the deduplication."""
    parser = argparse.ArgumentParser(description="Deduplicate startup names in a CSV file and overwrite the original")
    parser.add_argument("--file", "-f", type=str, required=True, help="Path to CSV file")
    parser.add_argument("--query", "-q", type=str, default="", help="Original search query for context")

    args = parser.parse_args()

    # Check if the file exists
    if not os.path.exists(args.file):
        logger.error(f"File not found: {args.file}")
        return 1

    # Run the deduplication
    print(f"\n=== STARTUP NAME DEDUPLICATION ===")
    print(f"File: {args.file}")
    print(f"Query context: {args.query or 'None'}")
    print("\nProcessing...")

    success = deduplicate_csv(args.file, args.query)

    if success:
        print(f"\nDeduplication complete!")
        print(f"Original file has been updated: {args.file}")
        print(f"A backup of the original file was created: {args.file}.bak")
        return 0
    else:
        print(f"\nDeduplication failed. See logs for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
