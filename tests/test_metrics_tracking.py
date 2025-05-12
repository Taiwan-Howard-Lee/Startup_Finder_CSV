"""
Test script for metrics tracking with 100 URLs.
"""

import os
import sys
import time
import logging
from typing import List, Dict, Any

# Add the src directory to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.processor.crawler import StartupCrawler
from src.utils.metrics_collector import MetricsCollector
from src.utils.report_generator import export_consolidated_reports, display_metrics_dashboard

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def generate_test_urls(num_urls: int = 100) -> List[str]:
    """
    Generate a list of test URLs.

    Args:
        num_urls: Number of URLs to generate.

    Returns:
        List of URLs.
    """
    # Start with some real startup websites
    base_urls = [
        "https://www.tesla.com",
        "https://www.apple.com",
        "https://www.google.com",
        "https://www.microsoft.com",
        "https://www.amazon.com",
        "https://www.facebook.com",
        "https://www.netflix.com",
        "https://www.uber.com",
        "https://www.airbnb.com",
        "https://www.spotify.com",
        "https://www.stripe.com",
        "https://www.slack.com",
        "https://www.zoom.us",
        "https://www.shopify.com",
        "https://www.square.com",
        "https://www.twilio.com",
        "https://www.dropbox.com",
        "https://www.pinterest.com",
        "https://www.twitter.com",
        "https://www.linkedin.com"
    ]

    # Add some startup directories
    directory_urls = [
        "https://www.crunchbase.com/lists/unicorn-companies/a8512650-fae8-4a0a-8742-0baa7a6e0ee4/organization.companies",
        "https://www.ycombinator.com/companies",
        "https://www.techstars.com/portfolio",
        "https://www.500.co/startups",
        "https://www.sequoiacap.com/companies/",
        "https://www.accel.com/companies",
        "https://www.kleinerperkins.com/companies/",
        "https://www.a16z.com/portfolio/",
        "https://www.greylock.com/portfolio/",
        "https://www.benchmark.com/companies/"
    ]

    # Add some tech news sites
    news_urls = [
        "https://techcrunch.com/",
        "https://www.wired.com/",
        "https://www.theverge.com/",
        "https://www.engadget.com/",
        "https://www.cnet.com/",
        "https://www.recode.net/",
        "https://www.venturebeat.com/",
        "https://www.protocol.com/",
        "https://www.axios.com/technology",
        "https://www.businessinsider.com/tech"
    ]

    # Combine all URLs
    all_urls = base_urls + directory_urls + news_urls

    # If we need more URLs, generate variations
    if num_urls > len(all_urls):
        # Generate variations by adding paths
        variations = []
        for url in base_urls:
            variations.extend([
                f"{url}/about",
                f"{url}/company",
                f"{url}/team",
                f"{url}/products",
                f"{url}/services",
                f"{url}/blog",
                f"{url}/news",
                f"{url}/press",
                f"{url}/careers",
                f"{url}/jobs",
                f"{url}/contact"
            ])

        all_urls.extend(variations)

    # Return the requested number of URLs
    return all_urls[:num_urls]

def test_metrics_tracking(num_urls: int = 100):
    """
    Test metrics tracking with a specified number of URLs.

    Args:
        num_urls: Number of URLs to test with.
    """
    print(f"\nTesting metrics tracking with {num_urls} URLs...")

    # Initialize metrics collector
    metrics_collector = MetricsCollector()

    # Initialize crawler
    max_workers = 10  # Use 10 workers for testing
    crawler = StartupCrawler(max_workers=max_workers)

    # Generate test URLs
    urls = generate_test_urls(num_urls)
    print(f"Generated {len(urls)} test URLs")

    # Process URLs in parallel
    start_time = time.time()
    results = crawler.web_crawler.fetch_webpages_parallel(urls, metrics_collector=metrics_collector)
    end_time = time.time()

    # Process results to extract startup names
    print("\nExtracting startup names from fetched pages...")

    # Use a test query
    test_query = "innovative startups in clean energy"
    metrics_collector.add_query(test_query)

    # Process each result to extract startup names
    startup_info_list = []
    for url, (raw_html, soup) in results.items():
        if not raw_html or not soup:
            continue

        # Create a mock search result
        mock_result = {
            "title": soup.title.text if soup.title else "Unknown Title",
            "snippet": soup.get_text()[:200] if soup else "No snippet available",
            "url": url
        }

        # Process the search result
        try:
            validated_names, source_info = crawler._process_search_result(
                url,
                mock_result.get("title", ""),
                mock_result.get("snippet", ""),
                raw_html,
                soup,
                test_query,
                metrics_collector
            )

            # Add validated names to our list
            for name in validated_names:
                # Create basic info for this startup
                basic_info = {
                    "Company Name": name,
                    **source_info  # Unpack the stored source info
                }

                startup_info_list.append(basic_info)
                print(f"Found startup: {name}")

                # Track final startup
                metrics_collector.add_final_startup(name, basic_info)
        except Exception as e:
            logger.error(f"Error processing search result for {url}: {e}")

    # Display metrics dashboard
    display_metrics_dashboard(metrics_collector)

    # Export consolidated reports
    report_files = export_consolidated_reports(metrics_collector, "test_metrics")

    print("\nTest completed successfully!")
    print(f"Processed {len(urls)} URLs in {end_time - start_time:.2f} seconds")
    print(f"Found {len(startup_info_list)} startups")
    print("\nReport files:")
    for report_type, file_path in report_files.items():
        print(f"- {report_type}: {file_path}")

if __name__ == "__main__":
    # Run the test with 20 URLs
    test_metrics_tracking(20)
