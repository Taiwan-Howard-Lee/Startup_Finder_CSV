"""
Test script for the full pipeline: Crawler -> Cleaner -> Chunker.

This script tests the integration of the crawler, text cleaner, and text chunker.
"""

import os
import sys
import json
import time
import logging
import argparse
import signal
import concurrent.futures
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.api_client import GeminiAPIClient
from src.utils.api_key_manager import APIKeyManager
from src.utils.google_search_client import GoogleSearchClient
from src.processor.crawler import WebCrawler
from src.utils.text_cleaner import TextCleaner
from src.utils.text_chunker import TextChunker
from src.collector.query_expander import QueryExpander

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CrawlerCleanerChunker:
    """
    A class that combines the crawler, text cleaner, and text chunker.
    """

    def __init__(self, max_workers: int = 15, chunk_size: int = 50000, overlap: int = 1000):
        """
        Initialize the crawler, cleaner, and chunker.

        Args:
            max_workers: Maximum number of parallel workers for the crawler
            chunk_size: Target size of each chunk in characters
            overlap: Number of characters to overlap between chunks
        """
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

        # Initialize text chunker
        self.text_chunker = TextChunker(chunk_size=chunk_size, overlap=overlap)

        # Set max workers
        self.max_workers = max_workers

        logger.info(f"Initialized CrawlerCleanerChunker with {max_workers} workers")
        logger.info(f"Using {len(self.key_manager.api_keys)} API keys and {len(self.key_manager.cx_ids)} CX IDs")
        logger.info(f"Chunk size: {chunk_size}, Overlap: {overlap}")

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
                        "raw_html_preview": raw_html[:1000] + "..." if raw_html and len(raw_html) > 1000 else raw_html,
                        "cleaned_content": cleaned_content,
                        "search_query": query,
                        "timestamp": datetime.now().isoformat()
                    }

                    raw_results.append(raw_result)
                except Exception as e:
                    logger.error(f"Error processing {url}: {e}")

            logger.info(f"Successfully crawled {len(raw_results)} webpages")
            return raw_results
        except Exception as e:
            logger.error(f"Error in search_and_crawl: {e}")
            return []

    def _fetch_raw_webpage(self, url: str, session):
        """
        Fetch a webpage and return its raw HTML content and BeautifulSoup object.

        Args:
            url: URL to fetch
            session: Requests session to use

        Returns:
            Tuple of (raw_html, soup) or (None, None) if fetch failed
        """
        try:
            import requests
            from bs4 import BeautifulSoup

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

    def process_batch(self, results: List[Dict[str, Any]], batch_size: int = 5) -> List[Dict[str, Any]]:
        """
        Process a batch of crawled results and chunk them.

        Args:
            results: List of crawled results
            batch_size: Number of results to process in each batch

        Returns:
            List of chunk objects
        """
        # Process results in batches
        all_chunks = []

        for i in range(0, len(results), batch_size):
            batch = results[i:i+batch_size]
            logger.info(f"Processing batch {i//batch_size + 1} with {len(batch)} results")

            # Extract cleaned text and metadata
            texts = []
            metadata = []

            for result in batch:
                cleaned_content = result.get("cleaned_content", "")
                if cleaned_content:
                    texts.append(cleaned_content)
                    metadata.append({
                        "url": result.get("url", ""),
                        "title": result.get("title", ""),
                        "search_query": result.get("search_query", "")
                    })

            # Chunk the batch
            if texts:
                logger.info(f"Chunking batch with {len(texts)} texts and {sum(len(t) for t in texts)} total characters")
                chunks = self.text_chunker.chunk_batch(texts, metadata)
                logger.info(f"Created {len(chunks)} chunks from batch")
                all_chunks.extend(chunks)

        logger.info(f"Created {len(all_chunks)} chunks in total")
        return all_chunks

def main():
    """Main function to run the test."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Test the crawler, cleaner, and chunker pipeline")
    parser.add_argument("--query", type=str, default="Diamond-like carbon (DLC) coating company",
                        help="Search query")
    parser.add_argument("--max-results", type=int, default=5,
                        help="Maximum number of search results per query")
    parser.add_argument("--num-expansions", type=int, default=10,
                        help="Number of query expansions to generate (default: 10 for 50 URLs total)")
    parser.add_argument("--workers", type=int, default=15,
                        help="Number of parallel workers (default: 15)")
    parser.add_argument("--chunk-size", type=int, default=50000,
                        help="Target size of each chunk in characters (default: 50000)")
    parser.add_argument("--overlap", type=int, default=1000,
                        help="Number of characters to overlap between chunks (default: 1000)")
    parser.add_argument("--batch-size", type=int, default=5,
                        help="Number of results to process in each batch (default: 5)")
    parser.add_argument("--output-file", type=str, default=None,
                        help="Output file path (default: auto-generated)")

    args = parser.parse_args()

    # Generate timestamp for output files
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Set output files
    raw_output_file = args.output_file or f"output/raw_results/crawler_cleaner_chunker_{timestamp}.json"
    chunks_output_file = f"output/chunks/chunks_{timestamp}.json"

    # Create output directories if they don't exist
    os.makedirs(os.path.dirname(raw_output_file), exist_ok=True)
    os.makedirs(os.path.dirname(chunks_output_file), exist_ok=True)

    # Print test information
    print("\n" + "=" * 80)
    print("CRAWLER -> CLEANER -> CHUNKER TEST")
    print("=" * 80)
    print(f"Query: {args.query}")
    print(f"Max results per query: {args.max_results}")
    print(f"Number of query expansions: {args.num_expansions}")
    print(f"Number of parallel workers: {args.workers}")
    print(f"Chunk size: {args.chunk_size}")
    print(f"Overlap: {args.overlap}")
    print(f"Batch size: {args.batch_size}")
    print(f"Raw output file: {raw_output_file}")
    print(f"Chunks output file: {chunks_output_file}")
    print("=" * 80)

    # Initialize the pipeline
    pipeline = CrawlerCleanerChunker(
        max_workers=args.workers,
        chunk_size=args.chunk_size,
        overlap=args.overlap
    )

    # Expand the query
    print("\nExpanding query...")
    expanded_queries = pipeline.expand_query(args.query, args.num_expansions)

    print("\nExpanded queries:")
    for i, query in enumerate(expanded_queries):
        print(f"  {i+1}. {query}")

    # Search and crawl
    print("\nSearching and crawling...")
    all_results = []

    start_time = time.time()

    # Process each expanded query
    for i, query in enumerate(expanded_queries):
        print(f"\nProcessing query {i+1}/{len(expanded_queries)}: {query}")

        # Search and crawl
        results = pipeline.search_and_crawl(query, args.max_results)

        # Add results to the list
        all_results.extend(results)

        # Print progress
        print(f"Found {len(results)} results for this query")
        print(f"Total results so far: {len(all_results)}")

        # Save intermediate results
        with open(f"{raw_output_file}_temp.json", "w") as f:
            json.dump(all_results, f, indent=2)

        print(f"Saved intermediate results to {raw_output_file}_temp.json")

    # Save final raw results
    with open(raw_output_file, "w") as f:
        json.dump(all_results, f, indent=2)

    print(f"\nSaved final raw results to {raw_output_file}")

    # Process results in batches and chunk them
    print("\nProcessing and chunking results...")
    chunks = pipeline.process_batch(all_results, args.batch_size)

    # Save chunks
    with open(chunks_output_file, "w") as f:
        json.dump(chunks, f, indent=2)

    print(f"Saved chunks to {chunks_output_file}")

    # Calculate elapsed time
    elapsed_time = time.time() - start_time

    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total time: {elapsed_time:.2f} seconds")
    print(f"Queries processed: {len(expanded_queries)}")
    print(f"Total results: {len(all_results)}")
    print(f"Total chunks: {len(chunks)}")
    print(f"Raw results saved to: {raw_output_file}")
    print(f"Chunks saved to: {chunks_output_file}")

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

    # Show chunk statistics
    chunk_sizes = [len(chunk.get("chunk", "")) for chunk in chunks]
    if chunk_sizes:
        avg_chunk_size = sum(chunk_sizes) / len(chunk_sizes)
        print(f"\nChunk statistics:")
        print(f"  Number of chunks: {len(chunks)}")
        print(f"  Average chunk size: {avg_chunk_size:.2f} characters")
        print(f"  Min chunk size: {min(chunk_sizes)} characters")
        print(f"  Max chunk size: {max(chunk_sizes)} characters")

    # Show top domains
    if domains:
        print("\nTop domains:")
        top_domains = sorted(domains.items(), key=lambda x: x[1], reverse=True)[:5]
        for domain, count in top_domains:
            print(f"  {domain}: {count} results")

    print("=" * 80)

    print("\nTo analyze the results, you can use:")
    print(f"  python -m json.tool {raw_output_file} | less")
    print(f"  python -m json.tool {chunks_output_file} | less")
    print("Or open the JSON files in a text editor.")

if __name__ == "__main__":
    # Handle keyboard interrupts gracefully
    def signal_handler(sig, frame):
        print("\nInterrupted by user. Exiting...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    # Run the test
    main()
