"""
Test script for finding decarbonisation startups in the UK.
"""

import os
import time
import logging
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.processor.crawler import StartupCrawler

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_uk_startups():
    """Test finding decarbonisation startups in the UK."""
    # Create a crawler with parallel processing
    crawler = StartupCrawler(max_workers=5)

    # Test query
    query = "decarbonisation startups in UK"

    # Measure time
    start_time = time.time()

    # Run the crawler
    logger.info(f"Starting crawler test with query: {query}")
    startup_info_list = crawler.discover_startups(query, max_results=5)

    # Log results
    logger.info(f"Found {len(startup_info_list)} startups")
    for startup in startup_info_list:
        logger.info(f"Startup: {startup.get('Company Name', 'Unknown')}")

    # Calculate elapsed time
    elapsed_time = time.time() - start_time
    logger.info(f"Test completed in {elapsed_time:.2f} seconds")

    return startup_info_list

if __name__ == "__main__":
    # Ensure environment variables are set
    if not os.environ.get("GOOGLE_SEARCH_API_KEY") or not os.environ.get("GOOGLE_CX_ID"):
        print("Please set GOOGLE_SEARCH_API_KEY and GOOGLE_CX_ID environment variables")
        exit(1)

    # Run the test
    test_uk_startups()
