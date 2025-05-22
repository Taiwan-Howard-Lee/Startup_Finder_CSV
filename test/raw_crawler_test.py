#!/usr/bin/env python3
"""
Raw Crawler Test for Startup Finder

This script tests the query expansion and crawling components of the Startup Finder
without using LLM extraction. It returns the raw output from the crawler.
"""

import os
import sys
import json
import time
import logging
import argparse
import signal
import concurrent.futures
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional

# Global variable for graceful shutdown
shutdown_requested = False

def signal_handler(sig, frame):
    """Handle interrupt signals to save progress before exiting."""
    global shutdown_requested
    print("\nInterrupt received. Finishing current batch and saving progress...")
    shutdown_requested = True

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import setup_env to ensure API keys are available
import setup_env

# Import the necessary components
from src.collector.query_expander import QueryExpander
from src.utils.api_client import GeminiAPIClient
from src.utils.api_key_manager import APIKeyManager
from src.utils.google_search_client import GoogleSearchClient
from src.processor.crawler import WebCrawler
from src.utils.text_cleaner import TextCleaner

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"output/logs/raw_crawler_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Create output directories if they don't exist
os.makedirs("output/data", exist_ok=True)
os.makedirs("output/raw_results", exist_ok=True)
os.makedirs("output/logs", exist_ok=True)

class RawCrawler:
    """
    A crawler that expands queries and fetches web content without LLM extraction.
    """

    def __init__(self, max_workers: int = 10):
        """Initialize the raw crawler."""
        # Initialize API key manager
        self.key_manager = APIKeyManager()

        # Initialize Google Search client with API key rotation
        api_key, cx_id = self.key_manager.get_next_key_pair()
        self.search_client = GoogleSearchClient(
            api_key=api_key,
            cx_id=cx_id
        )

        # Initialize web crawler
        self.web_crawler = WebCrawler(max_workers=max_workers)

        # Initialize Gemini client for query expansion
        self.gemini_client = GeminiAPIClient()

        # Initialize query expander
        self.query_expander = QueryExpander(api_client=self.gemini_client)

        # Initialize text cleaner
        self.text_cleaner = TextCleaner()

        # Set max workers
        self.max_workers = max_workers

        logger.info(f"Initialized RawCrawler with {max_workers} workers")
        logger.info(f"Using {len(self.key_manager.api_keys)} API keys and {len(self.key_manager.cx_ids)} CX IDs")

    def _fetch_raw_webpage(self, url: str, session: requests.Session) -> Tuple[Optional[str], Optional[BeautifulSoup]]:
        """
        Fetch a webpage and return its raw HTML content and BeautifulSoup object.

        Args:
            url: URL to fetch
            session: Requests session to use

        Returns:
            Tuple of (raw_html, soup) or (None, None) if fetch failed
        """
        try:
            # Set headers to mimic a browser
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            }

            # Make the request
            response = session.get(url, headers=headers, timeout=10, verify=False)
            response.raise_for_status()

            # Get the raw HTML
            raw_html = response.text

            # Parse with BeautifulSoup
            soup = BeautifulSoup(raw_html, "lxml")

            return raw_html, soup
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None, None

    def expand_query(self, query: str, num_expansions: int) -> List[str]:
        """Expand a query into multiple variations."""
        logger.info(f"Expanding query: {query} with {num_expansions} expansions")

        try:
            expanded_queries = self.query_expander.expand_query_parallel(
                query=query,
                num_expansions=num_expansions
            )

            # Ensure we have at least one query (the original) even if expansion fails
            if not expanded_queries:
                logger.warning("Query expansion returned no results. Using original query.")
                expanded_queries = [query]

            logger.info(f"Generated {len(expanded_queries)} expanded queries")
            return expanded_queries
        except Exception as e:
            logger.error(f"Error expanding query: {e}")
            logger.info("Falling back to original query only")
            return [query]

    def search_and_crawl(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Search for results and crawl the webpages."""
        logger.info(f"Searching for: {query} with max_results={max_results}")

        try:
            # Try to get search results, rotating API keys if needed
            try:
                search_results = self.search_client.search(query, num_results=max_results)
            except Exception as e:
                logger.warning(f"Error with current API key: {e}. Trying with a new key...")
                # Rotate to a new API key and try again
                api_key, cx_id = self.key_manager.get_next_key_pair()
                self.search_client = GoogleSearchClient(
                    api_key=api_key,
                    cx_id=cx_id
                )
                search_results = self.search_client.search(query, num_results=max_results)

            logger.info(f"Found {len(search_results)} search results")

            # Extract URLs
            urls = [result.get("link") for result in search_results if result.get("link")]
            logger.info(f"Extracted {len(urls)} URLs")

            # Crawl webpages directly using requests to get raw HTML
            raw_results = []

            # Use the WebCrawler's session for connection pooling
            session = self.web_crawler.session

            # For parallel processing
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all fetch tasks
                future_to_url = {executor.submit(self._fetch_raw_webpage, url, session): url for url in urls}

                # Process results as they complete
                webpage_results = {}
                for future in concurrent.futures.as_completed(future_to_url):
                    url = future_to_url[future]
                    try:
                        raw_html, soup = future.result()
                        webpage_results[url] = (raw_html, soup)
                    except Exception as e:
                        logger.error(f"Error fetching {url}: {e}")
                        webpage_results[url] = (None, None)

            # Process results
            for url, (raw_html, soup) in webpage_results.items():
                if not raw_html or not soup:
                    logger.warning(f"Failed to fetch content from {url}")
                    continue

                try:
                    # Get title
                    title = soup.title.text.strip() if soup.title else "No title"

                    # Clean the content using TextCleaner
                    cleaned_content = self.text_cleaner.extract_text_from_html(raw_html) if raw_html else ""

                    # Calculate content lengths
                    raw_length = len(raw_html) if raw_html else 0
                    cleaned_length = len(cleaned_content) if cleaned_content else 0

                    # Calculate content reduction percentage
                    if raw_length > 0:
                        reduction_percentage = round((raw_length - cleaned_length) / raw_length * 100, 2)
                    else:
                        reduction_percentage = 0

                    # Store raw result with both raw and cleaned content
                    raw_result = {
                        "url": url,
                        "title": title,
                        "raw_content_length": raw_length,
                        "cleaned_content_length": cleaned_length,
                        "content_reduction_percentage": reduction_percentage,
                        "raw_html_preview": raw_html[:1000] + "..." if raw_html and len(raw_html) > 1000 else raw_html,  # Include a preview of raw HTML
                        "cleaned_content": cleaned_content,  # Include the full cleaned content
                        "search_query": query,
                        "timestamp": datetime.now().isoformat()
                    }

                    raw_results.append(raw_result)
                except Exception as e:
                    logger.error(f"Error processing result for {url}: {e}")

            logger.info(f"Successfully crawled {len(raw_results)} webpages")
            return raw_results

        except Exception as e:
            logger.error(f"Error in search_and_crawl for query '{query}': {e}")
            return []

def main():
    """Main function to run the raw crawler test."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Raw Crawler Test for Startup Finder")
    parser.add_argument("--query", type=str, default="Diamond-like carbon (DLC) coating company",
                        help="Search query to use")
    parser.add_argument("--max-results", type=int, default=5,
                        help="Maximum number of search results per query")
    parser.add_argument("--num-expansions", type=int, default=10,
                        help="Number of query expansions to generate (default: 10 for 50 URLs total)")
    parser.add_argument("--workers", type=int, default=15,
                        help="Number of parallel workers (default: 15)")
    parser.add_argument("--output-file", type=str, default=None,
                        help="Output JSON file path")
    args = parser.parse_args()

    # Ensure environment is set up
    setup_env.setup_environment(test_apis=False)

    # Generate timestamp for output files
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Set output file
    output_file = args.output_file or f"output/raw_results/raw_crawler_with_cleaned_content_{timestamp}.json"

    print("\n" + "=" * 80)
    print("RAW CRAWLER TEST (WITH FULL AND CLEANED CONTENT)")
    print("=" * 80)
    print(f"Query: {args.query}")
    print(f"Max results per query: {args.max_results}")
    print(f"Number of query expansions: {args.num_expansions}")
    print(f"Number of parallel workers: {args.workers}")
    print(f"Output file: {output_file}")
    print("=" * 80)

    # Initialize raw crawler
    crawler = RawCrawler(max_workers=args.workers)

    # Start timing
    start_time = time.time()

    # Expand query
    print("\nExpanding query...")
    expanded_queries = crawler.expand_query(args.query, args.num_expansions)

    print("\nExpanded queries:")
    for i, expanded_query in enumerate(expanded_queries):
        print(f"  {i+1}. {expanded_query}")

    # Search and crawl for each expanded query
    all_results = []

    # Create a temporary file for intermediate results
    temp_output_file = output_file.replace('.json', '_temp.json')

    print("\nSearching and crawling...")
    try:
        for i, expanded_query in enumerate(expanded_queries):
            # Check if shutdown was requested
            if shutdown_requested:
                print("\nShutdown requested. Saving progress and exiting...")
                break

            print(f"\nProcessing query {i+1}/{len(expanded_queries)}: {expanded_query}")

            # Search and crawl
            results = crawler.search_and_crawl(expanded_query, args.max_results)

            # Add to all results
            all_results.extend(results)

            print(f"Found {len(results)} results for this query")
            print(f"Total results so far: {len(all_results)}")

            # Save intermediate results every 2 queries or on the last query
            if (i + 1) % 2 == 0 or i == len(expanded_queries) - 1 or shutdown_requested:
                try:
                    with open(temp_output_file, 'w', encoding='utf-8') as f:
                        json.dump(all_results, f, indent=2, ensure_ascii=False)
                    print(f"Saved intermediate results to {temp_output_file}")
                except Exception as e:
                    print(f"Warning: Failed to save intermediate results: {e}")
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Saving current results...")
    except Exception as e:
        print(f"\nError during processing: {e}")
        logger.error(f"Error during processing: {e}")
    finally:
        # End timing
        end_time = time.time()
        elapsed_time = end_time - start_time

        # Save final results to JSON file
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(all_results, f, indent=2, ensure_ascii=False)
            print(f"\nSaved final results to {output_file}")
        except Exception as e:
            print(f"\nError saving final results: {e}")
            logger.error(f"Error saving final results: {e}")
            print(f"Check {temp_output_file} for the most recent intermediate results")

    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total time: {elapsed_time:.2f} seconds")
    print(f"Queries processed: {min(i+1, len(expanded_queries)) if 'i' in locals() else 0}/{len(expanded_queries)}")
    print(f"Total results: {len(all_results)}")
    print(f"Results saved to: {output_file}")

    # Calculate statistics
    domains = {}
    total_raw_length = 0
    total_cleaned_length = 0

    for result in all_results:
        # Domain statistics
        url = result.get("url", "")
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            domains[domain] = domains.get(domain, 0) + 1
        except:
            pass

        # Content length statistics
        total_raw_length += result.get("raw_content_length", 0)
        total_cleaned_length += result.get("cleaned_content_length", 0)

    # Calculate average reduction percentage
    if total_raw_length > 0:
        overall_reduction = round((total_raw_length - total_cleaned_length) / total_raw_length * 100, 2)
    else:
        overall_reduction = 0

    # Show content length statistics
    print("\nContent length statistics:")
    print(f"  Total raw content length: {total_raw_length} characters")
    print(f"  Total cleaned content length: {total_cleaned_length} characters")
    print(f"  Overall content reduction: {overall_reduction}%")

    # Show top domains
    if domains:
        print("\nTop domains:")
        top_domains = sorted(domains.items(), key=lambda x: x[1], reverse=True)[:5]
        for domain, count in top_domains:
            print(f"  {domain}: {count} results")

    print("=" * 80)

    # Print instructions for next steps
    print("\nTo analyze the results, you can use:")
    print(f"  python -m json.tool {output_file} | less")
    print("Or open the JSON file in a text editor.")

    if shutdown_requested:
        print("\nProcess was interrupted but progress was saved.")
        print(f"To continue, run the script again with different query expansions.")

if __name__ == "__main__":
    main()
