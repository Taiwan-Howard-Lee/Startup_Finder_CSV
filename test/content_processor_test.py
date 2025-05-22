"""
Test script for the ContentProcessor.

This script tests the integration of the TextCleaner and TextChunker through the ContentProcessor.
"""

import sys
import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.content_processor import ContentProcessor

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_sample_data(file_path: str) -> List[Dict[str, Any]]:
    """
    Load sample data from a JSON file.

    Args:
        file_path: Path to the JSON file

    Returns:
        List of dictionaries containing sample data
    """
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        return data
    except Exception as e:
        logger.error(f"Error loading sample data: {e}")
        return []

def test_content_processor():
    """Test the ContentProcessor with sample data from a previous crawler run."""
    # Find the latest raw crawler results
    output_dir = Path("output/raw_results")
    result_files = list(output_dir.glob("crawler_cleaner_chunker_*.json"))

    if not result_files:
        # Try with raw crawler files
        result_files = list(output_dir.glob("raw_crawler_*.json"))

    result_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

    if not result_files:
        logger.error("No raw crawler results found.")
        return

    latest_file = result_files[0]
    logger.info(f"Using sample data from: {latest_file}")

    # Load the sample data
    sample_data = load_sample_data(latest_file)
    if not sample_data:
        logger.error("No sample data loaded.")
        return

    # Initialize the ContentProcessor
    processor = ContentProcessor(chunk_size=50000, overlap=1000)

    # Process and chunk the content
    logger.info(f"Processing {len(sample_data)} items")

    # Process the raw content
    content_key = "raw_html_preview" if "raw_html_preview" in sample_data[0] else "raw_html"
    processed_items = processor.process_batch(sample_data, content_key=content_key, content_type="html")
    logger.info(f"Processed {len(processed_items)} items")

    # Log processing statistics
    total_raw_length = sum(len(item.get(content_key, "")) for item in sample_data)
    total_cleaned_length = sum(len(item.get("cleaned_content", "")) for item in processed_items)

    if total_raw_length > 0:
        reduction_percentage = round((total_raw_length - total_cleaned_length) / total_raw_length * 100, 2)
        logger.info(f"Total raw content length: {total_raw_length} characters")
        logger.info(f"Total cleaned content length: {total_cleaned_length} characters")
        logger.info(f"Overall content reduction: {reduction_percentage}%")

    # Chunk the processed content
    chunks = processor.chunk_processed_content(processed_items)
    logger.info(f"Created {len(chunks)} chunks")

    # Log chunk statistics
    chunk_sizes = [len(chunk.get("chunk", "")) for chunk in chunks]
    if chunk_sizes:
        avg_chunk_size = sum(chunk_sizes) / len(chunk_sizes)
        logger.info(f"Average chunk size: {avg_chunk_size:.2f} characters")
        logger.info(f"Min chunk size: {min(chunk_sizes)} characters")
        logger.info(f"Max chunk size: {max(chunk_sizes)} characters")

    # Save the chunks to a file for inspection
    output_file = "output/chunks/content_processor_test_output.json"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    processor.save_chunks(chunks, output_file)
    logger.info(f"Saved chunks to {output_file}")

    # Test the combined process_and_chunk method
    logger.info("\nTesting combined process_and_chunk method...")
    combined_output_file = "output/chunks/content_processor_combined_test_output.json"
    combined_chunks = processor.process_and_chunk(
        sample_data,
        content_key=content_key,
        content_type="html",
        output_file=combined_output_file
    )

    logger.info(f"Created {len(combined_chunks)} chunks with combined method")
    logger.info(f"Saved combined chunks to {combined_output_file}")

    # Verify that both methods produce the same results
    if len(chunks) == len(combined_chunks):
        logger.info("Both methods produced the same number of chunks")
    else:
        logger.warning(f"Methods produced different numbers of chunks: {len(chunks)} vs {len(combined_chunks)}")

if __name__ == "__main__":
    # Create output directory if it doesn't exist
    os.makedirs("output/chunks", exist_ok=True)

    # Run the test
    test_content_processor()
