"""
Test script for the parallel processing capabilities of the crawler.
"""

import os
import time
import logging
import concurrent.futures
import sys
from typing import List, Dict, Any

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.processor.crawler import WebCrawler

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_parallel_fetching():
    """Test parallel webpage fetching."""
    # Create a crawler with parallel processing
    crawler = WebCrawler(max_workers=5)

    # Test URLs
    urls = [
        "https://www.bbc.co.uk/news/business",
        "https://techcrunch.com/",
        "https://www.reuters.com/business/",
        "https://www.ft.com/",
        "https://www.bloomberg.com/",
        "https://www.cnbc.com/",
        "https://www.forbes.com/",
        "https://www.wsj.com/",
        "https://www.economist.com/",
        "https://www.businessinsider.com/"
    ]

    # Measure time for sequential fetching
    logger.info("Testing sequential fetching...")
    start_time = time.time()

    sequential_results = {}
    for url in urls:
        raw_html, soup = crawler.fetch_webpage(url)
        sequential_results[url] = (raw_html is not None, soup is not None)

    sequential_time = time.time() - start_time
    logger.info(f"Sequential fetching completed in {sequential_time:.2f} seconds")

    # Measure time for parallel fetching
    logger.info("Testing parallel fetching...")
    start_time = time.time()

    parallel_results = crawler.fetch_webpages_parallel(urls)
    parallel_results_status = {url: (raw_html is not None, soup is not None) for url, (raw_html, soup) in parallel_results.items()}

    parallel_time = time.time() - start_time
    logger.info(f"Parallel fetching completed in {parallel_time:.2f} seconds")

    # Compare results
    logger.info(f"Sequential vs Parallel time: {sequential_time:.2f}s vs {parallel_time:.2f}s")
    logger.info(f"Speedup factor: {sequential_time / parallel_time:.2f}x")

    # Check if results are consistent
    for url in urls:
        if url in sequential_results and url in parallel_results_status:
            if sequential_results[url] != parallel_results_status[url]:
                logger.warning(f"Inconsistent results for {url}")

    return sequential_time, parallel_time, parallel_results

if __name__ == "__main__":
    test_parallel_fetching()
