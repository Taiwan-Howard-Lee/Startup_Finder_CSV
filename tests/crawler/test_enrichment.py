"""
Test script for the enrichment phase of the crawler.
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

def test_enrichment():
    """Test the enrichment phase of the crawler."""
    # Create a crawler with parallel processing
    crawler = StartupCrawler(max_workers=5)

    # Test query
    query = "decarbonisation startups in UK"

    # Measure time
    start_time = time.time()

    # Run the discovery phase
    logger.info(f"Starting discovery phase with query: {query}")
    startup_info_list = crawler.discover_startups(query, max_results=3)

    # Run the enrichment phase
    logger.info(f"Starting enrichment phase for {len(startup_info_list)} startups")
    enriched_startups = crawler.enrich_startup_data(startup_info_list, max_results_per_startup=2)

    # Log results
    logger.info(f"Enriched {len(enriched_startups)} startups")
    for startup in enriched_startups:
        logger.info(f"Startup: {startup.get('Company Name', 'Unknown')}")
        for key, value in startup.items():
            if key != "Company Name":
                logger.info(f"  {key}: {value}")

    # Calculate elapsed time
    elapsed_time = time.time() - start_time
    logger.info(f"Test completed in {elapsed_time:.2f} seconds")

    return enriched_startups

if __name__ == "__main__":
    # Ensure environment variables are set
    if not os.environ.get("GOOGLE_SEARCH_API_KEY") or not os.environ.get("GOOGLE_CX_ID"):
        print("Please set GOOGLE_SEARCH_API_KEY and GOOGLE_CX_ID environment variables")
        exit(1)

    # Run the test
    test_enrichment()
