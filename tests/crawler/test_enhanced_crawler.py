"""
Test script for the enhanced crawler with Jina-inspired techniques.
"""

import os
import time
import logging
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.processor.crawler import WebCrawler, URLNormalizer

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_url_normalization():
    """Test URL normalization."""
    logger.info("Testing URL normalization...")

    test_urls = [
        "https://www.example.com",
        "https://www.example.com/",
        "https://example.com",
        "https://example.com/index.html?utm_source=test",
        "https://example.com/index.html?a=1&b=2",
        "https://example.com/index.html?b=2&a=1",
        "https://example.com:443/test",
        "https://example.com/test#fragment"
    ]

    normalized_urls = [URLNormalizer.normalize(url) for url in test_urls]

    logger.info("Original URLs:")
    for url in test_urls:
        logger.info(f"  {url}")

    logger.info("Normalized URLs:")
    for url in normalized_urls:
        logger.info(f"  {url}")

    # Check for duplicates
    unique_urls = set(normalized_urls)
    logger.info(f"Number of unique normalized URLs: {len(unique_urls)} (out of {len(test_urls)})")

    return normalized_urls

def test_adaptive_crawling():
    """Test adaptive crawling."""
    logger.info("Testing adaptive crawling...")

    # Create a crawler
    crawler = WebCrawler(max_workers=5)

    # Test URL
    start_url = "https://techcrunch.com/"

    # Measure time
    start_time = time.time()

    # Perform adaptive crawling
    logger.info(f"Starting adaptive crawling from {start_url}")
    results = crawler.adaptive_crawl(start_url, max_depth=1, max_pages=5, filter_same_domain=True)

    # Log results
    logger.info(f"Crawled {len(results)} pages")
    for url in results:
        logger.info(f"  {url}")

    # Calculate elapsed time
    elapsed_time = time.time() - start_time
    logger.info(f"Adaptive crawling completed in {elapsed_time:.2f} seconds")

    return results

def test_content_extraction_strategies():
    """Test different content extraction strategies."""
    logger.info("Testing content extraction strategies...")

    # Create a crawler
    crawler = WebCrawler(max_workers=5)

    # Test URLs for different website types
    test_urls = {
        "news": "https://techcrunch.com/",
        "linkedin": "https://www.linkedin.com/company/microsoft/",
        "twitter": "https://twitter.com/Microsoft",
        "wordpress": "https://wordpress.org/",
        "generic": "https://example.com/"
    }

    results = {}

    # Test each URL
    for website_type, url in test_urls.items():
        logger.info(f"Testing {website_type} website: {url}")

        # Detect website type
        detected_type = crawler._detect_website_type(url)
        logger.info(f"  Detected website type: {detected_type}")

        # Choose extraction strategies
        strategies = crawler._choose_extraction_strategy(url, detected_type)
        logger.info(f"  Chosen strategies: {[s.__class__.__name__ for s in strategies]}")

        # Fetch the webpage
        raw_html, soup = crawler.fetch_webpage(url)

        # Log result
        if raw_html and soup:
            logger.info(f"  Successfully fetched {url}")
            results[url] = (raw_html, soup)
        else:
            logger.info(f"  Failed to fetch {url}")

    return results

if __name__ == "__main__":
    # Run the tests
    logger.info("Running tests for enhanced crawler...")

    # Test URL normalization
    normalized_urls = test_url_normalization()

    # Test adaptive crawling
    crawled_pages = test_adaptive_crawling()

    # Test content extraction strategies
    extracted_content = test_content_extraction_strategies()

    logger.info("All tests completed.")
