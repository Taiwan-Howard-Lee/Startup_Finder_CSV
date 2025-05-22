#!/usr/bin/env python3
"""
Startup Finder

A comprehensive tool to find and gather information about startups based on search queries.
This script combines query expansion, web crawling, startup name extraction, and data enrichment
to generate a detailed CSV file with startup information.
"""

import os
import csv
import time
import logging
import argparse
import re
import traceback
import json
import concurrent.futures
import asyncio
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from bs4 import BeautifulSoup

# Import setup_env to ensure API keys are available
import setup_env

# Type checking imports
if TYPE_CHECKING:
    from src.utils.metrics_collector import MetricsCollector

# Import core functionality
from src.processor.enhanced_crawler import EnhancedStartupCrawler
from src.processor.website_extractor import WebsiteExtractor
from src.processor.linkedin_extractor import LinkedInExtractor
from src.collector.query_expander import QueryExpander
from src.utils.api_client import GeminiAPIClient
from src.utils.content_processor import ContentProcessor

# Import optimization utilities
from src.utils.optimization_utils import (
    MemoryOptimizer, ParallelProcessor, CacheManager,
    cache_manager, lru_cache_api_call
)
from src.utils.smart_content_processor import (
    ContentRelevanceFilter, EntityExtractor, SiteSpecificExtractor
)
from src.utils.api_optimizer import (
    APIOptimizer, RateLimiter, CircuitBreaker,
    rate_limited, with_circuit_breaker, with_retry
)
from src.utils.query_optimizer import QueryOptimizer
from src.utils.database_manager import DatabaseManager
from src.utils.progressive_loader import (
    ProgressiveLoader, ProgressTracker, progress_callback
)

# Import logging configuration
from src.utils.logging_config import configure_logging

# Configure logging with a file in the output/logs directory
os.makedirs("output/logs", exist_ok=True)
log_file = os.path.join("output/logs", f"startup_finder_{time.strftime('%Y%m%d')}.log")
configure_logging(log_level="INFO", log_file=log_file)

# Get logger for this module
logger = logging.getLogger(__name__)

# Create output directories if they don't exist
os.makedirs("output/data", exist_ok=True)
os.makedirs("output/queries", exist_ok=True)
os.makedirs("output/reports", exist_ok=True)

# Initialize global utilities
db_manager = DatabaseManager()
entity_extractor = EntityExtractor()


def edit_queries_manually(queries: List[str]) -> List[str]:
    """
    Allow the user to manually edit the expanded queries.

    This function writes the queries to a file in the output/queries directory,
    tells the user where the file is located, and waits for them to edit it manually.
    It also applies query optimization techniques to improve the quality of queries.

    Args:
        queries: List of queries to edit.

    Returns:
        List of edited queries.
    """
    # First, apply query optimization to remove duplicates and similar queries
    logger.info(f"Optimizing {len(queries)} queries before manual editing")

    # Normalize queries
    normalized_queries = [QueryOptimizer.normalize_query(q) for q in queries]

    # Remove duplicates
    unique_queries = []
    seen = set()
    for i, query in enumerate(normalized_queries):
        if query not in seen:
            unique_queries.append(queries[i])  # Keep the original format
            seen.add(query)

    # Try to use semantic deduplication if available
    try:
        optimized_queries = QueryOptimizer.deduplicate_semantically(unique_queries, threshold=0.85)
        logger.info(f"Reduced queries from {len(queries)} to {len(optimized_queries)} using semantic deduplication")
    except Exception as e:
        logger.warning(f"Semantic deduplication failed: {e}. Using simple deduplication instead.")
        optimized_queries = unique_queries
        logger.info(f"Reduced queries from {len(queries)} to {len(optimized_queries)} using simple deduplication")

    # Create a file in the output/queries directory
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    temp_file_path = os.path.join("output/queries", f"queries_{timestamp}.txt")

    try:
        # Write queries to the file
        with open(temp_file_path, 'w', encoding='utf-8') as f:
            f.write("# Edit the queries below. Each line will be used as a separate search query.\n")
            f.write("# Delete a line to remove that query. Add new lines to add new queries.\n")
            f.write("# Save the file when you're done.\n")
            f.write("# Lines starting with # are comments and will be ignored.\n\n")
            for query in optimized_queries:
                f.write(f"{query}\n")

        # Tell the user where the file is and wait for them to edit it
        print(f"\nOptimized queries have been written to: {temp_file_path}")
        print("Please edit this file with your preferred text editor.")
        print("Each line will be used as a separate search query.")
        print("Delete lines to remove queries, add new lines to add queries.")
        print("Lines starting with # are comments and will be ignored.")
        input("Press Enter when you've finished editing the file...")

        # Read back the edited queries
        edited_queries = []
        with open(temp_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if line and not line.startswith('#'):
                    edited_queries.append(line)

        # Save the final queries to the database for future reference
        try:
            db_manager.save_query(queries[0], edited_queries)  # Use the first query as the original query
            logger.info(f"Saved {len(edited_queries)} edited queries to database")
        except Exception as e:
            logger.warning(f"Failed to save queries to database: {e}")

        # Final optimization to ensure no duplicates
        final_queries = []
        seen = set()
        for query in edited_queries:
            normalized = QueryOptimizer.normalize_query(query)
            if normalized not in seen:
                final_queries.append(query)
                seen.add(normalized)

        print(f"\nLoaded {len(final_queries)} unique queries after editing.")
        return final_queries

    except Exception as e:
        logger.error(f"Error during manual query editing: {e}")
        print(f"Error during manual query editing: {e}")
        print("Proceeding with original queries.")
        return queries


def load_env_from_file():
    """Load environment variables from .env file."""
    try:
        with open(".env", "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                key, value = line.split("=", 1)
                os.environ[key] = value

        logger.info("Loaded API keys from .env file")
    except Exception as e:
        logger.error(f"Error loading environment variables: {e}")


def save_api_keys_to_file(filename=".env"):
    """
    Save the API keys to a .env file for future use.

    Args:
        filename: The name of the file to save the API keys to.

    Returns:
        bool: True if the API keys were saved successfully, False otherwise.
    """
    try:
        with open(filename, "w") as f:
            # Save Gemini API key
            if os.environ.get("GEMINI_API_KEY"):
                f.write(f"# Gemini API Keys\n")
                f.write(f"GEMINI_API_KEY={os.environ.get('GEMINI_API_KEY')}\n\n")

            # Save Google Search API keys (numbered format)
            google_api_keys_found = False
            i = 1
            f.write(f"# Google Search API Keys (add more as needed)\n")
            while True:
                key = os.environ.get(f"GOOGLE_SEARCH_API_KEY_{i}")
                if not key:
                    break
                f.write(f"GOOGLE_SEARCH_API_KEY_{i}={key}\n")
                google_api_keys_found = True
                i += 1

            # Save legacy Google Search API key if it exists
            if os.environ.get("GOOGLE_SEARCH_API_KEY"):
                f.write(f"GOOGLE_SEARCH_API_KEY={os.environ.get('GOOGLE_SEARCH_API_KEY')}\n")
                google_api_keys_found = True

            if not google_api_keys_found:
                f.write(f"# GOOGLE_SEARCH_API_KEY_1=YOUR_API_KEY\n")

            f.write("\n")

            # Save Google Custom Search Engine IDs (numbered format)
            google_cx_ids_found = False
            i = 1
            f.write(f"# Google Custom Search Engine IDs (add more as needed)\n")
            while True:
                cx = os.environ.get(f"GOOGLE_CX_ID_{i}")
                if not cx:
                    break
                f.write(f"GOOGLE_CX_ID_{i}={cx}\n")
                google_cx_ids_found = True
                i += 1

            # Save legacy Google CX ID if it exists
            if os.environ.get("GOOGLE_CX_ID"):
                f.write(f"GOOGLE_CX_ID={os.environ.get('GOOGLE_CX_ID')}\n")
                google_cx_ids_found = True

            if not google_cx_ids_found:
                f.write(f"# GOOGLE_CX_ID_1=YOUR_CX_ID\n")

        print(f"\nAPI keys saved to {filename}")
        print(f"In the future, you can load these keys with: source {filename}")
        return True
    except Exception as e:
        print(f"Error saving API keys to file: {e}")
        return False


@with_retry(max_retries=3, initial_wait=1.0, backoff_factor=2.0)
def enrich_startup_data(crawler: EnhancedStartupCrawler, startup_name: str) -> Dict[str, Any]:
    """
    Enhanced function to enrich startup data with LinkedIn and company website information.
    Uses optimized processing, caching, and smart content extraction.

    Args:
        crawler: StartupCrawler instance.
        startup_name: Name of the startup.

    Returns:
        Dictionary with enriched startup data.
    """
    logger.info(f"Enriching data for: {startup_name}")

    # Check if we already have this startup in the database
    cached_data = db_manager.get_startup(startup_name)
    if cached_data:
        logger.info(f"Found cached data for {startup_name} in database")
        return cached_data

    # Start with basic info
    startup_data = {"Company Name": startup_name}

    # Step 1: Find the company's official website
    try:
        # Check cache first
        website_query = f"{startup_name} official website"
        cached_results = cache_manager.get_cached_value(f"website_search:{website_query}")

        if cached_results:
            website_results = cached_results
            logger.info(f"Using cached website search results for {startup_name}")
        else:
            # Search for the official website
            website_results = crawler.google_search.search(website_query, max_results=3)
            # Cache the results
            cache_manager.cache_value(f"website_search:{website_query}", website_results)

        if website_results:
            for result in website_results:
                official_url = result.get("url", "")
                # Skip social media sites
                if any(domain in official_url.lower() for domain in ["linkedin.com", "twitter.com", "facebook.com"]):
                    continue
                # Check if the URL contains the company name
                normalized_name = startup_name.lower().replace(" ", "").replace("-", "").replace(".", "")
                normalized_url = official_url.lower().replace("www.", "").replace("http://", "").replace("https://", "")

                if normalized_name in normalized_url.replace(".", "") or normalized_url.split(".")[0] == normalized_name:
                    startup_data["Website"] = official_url
                    logger.info(f"Found official website for {startup_name}: {official_url}")
                    break

            # If we couldn't find a good match, use the first result
            if "Website" not in startup_data and website_results:
                startup_data["Website"] = website_results[0].get("url", "")
                logger.info(f"Using first result as website for {startup_name}: {startup_data['Website']}")
    except Exception as e:
        logger.error(f"Error finding official website for {startup_name}: {e}")

    # Step 2: Find the company's LinkedIn page
    try:
        # Check cache first
        linkedin_query = f"site:linkedin.com/company/ \"{startup_name}\""
        cached_results = cache_manager.get_cached_value(f"linkedin_search:{linkedin_query}")

        if cached_results:
            linkedin_results = cached_results
            logger.info(f"Using cached LinkedIn search results for {startup_name}")
        else:
            # Search for the LinkedIn page
            linkedin_results = crawler.google_search.search(linkedin_query, max_results=3)
            # Cache the results
            cache_manager.cache_value(f"linkedin_search:{linkedin_query}", linkedin_results)

        if linkedin_results:
            for result in linkedin_results:
                linkedin_url = result.get("url", "")
                if "linkedin.com/company/" in linkedin_url.lower():
                    startup_data["LinkedIn"] = linkedin_url
                    logger.info(f"Found LinkedIn page for {startup_name}: {linkedin_url}")
                    break
    except Exception as e:
        logger.error(f"Error finding LinkedIn page for {startup_name}: {e}")

    # Step 3: Extract data from the official website if available
    if "Website" in startup_data and startup_data["Website"]:
        try:
            official_url = startup_data["Website"]

            # Check if we have cached content
            cached_content = db_manager.get_url_content(official_url)

            if cached_content:
                logger.info(f"Using cached content for website {official_url}")
                raw_html, cleaned_content = cached_content
                # Create a soup object from the raw HTML
                soup = BeautifulSoup(raw_html, 'lxml') if raw_html else None
            else:
                # Fetch the website
                raw_html, soup = crawler.web_crawler.fetch_webpage(official_url)

                if raw_html and soup:
                    # Use site-specific extractor for better content extraction
                    cleaned_content = SiteSpecificExtractor.extract_content(official_url, raw_html)
                    # Cache the content
                    db_manager.save_url_content(official_url, raw_html, cleaned_content)
                else:
                    cleaned_content = ""

            if raw_html and soup:
                # Extract data using the website extractor
                website_data = WebsiteExtractor.extract_data(startup_name, official_url, raw_html, soup)

                # Try to extract organization names using NLP
                try:
                    organizations = entity_extractor.extract_organizations(cleaned_content)
                    if organizations and "Company Name" not in website_data:
                        # Find the organization name that best matches the startup name
                        best_match = None
                        best_score = 0

                        for org in organizations:
                            # Simple string similarity score
                            org_lower = org.lower()
                            name_lower = startup_name.lower()

                            if org_lower == name_lower:
                                best_match = org
                                break

                            if org_lower in name_lower or name_lower in org_lower:
                                score = len(set(org_lower) & set(name_lower)) / len(set(org_lower) | set(name_lower))
                                if score > best_score:
                                    best_score = score
                                    best_match = org

                        if best_match and best_score > 0.5:
                            website_data["Company Name"] = best_match
                            logger.info(f"Extracted company name from website: {best_match}")
                except Exception as e:
                    logger.warning(f"Error extracting organizations from website: {e}")

                # Merge the extracted data
                for key, value in website_data.items():
                    if value and (key not in startup_data or not startup_data[key]):
                        startup_data[key] = value

                logger.info(f"Extracted website data for {startup_name}: {list(website_data.keys())}")
        except Exception as e:
            logger.error(f"Error extracting data from website {startup_data.get('Website')}: {e}")

    # Step 4: Extract data from the LinkedIn page if available
    if "LinkedIn" in startup_data and startup_data["LinkedIn"]:
        try:
            linkedin_url = startup_data["LinkedIn"]

            # Check if we have cached content
            cached_content = db_manager.get_url_content(linkedin_url)

            if cached_content:
                logger.info(f"Using cached content for LinkedIn {linkedin_url}")
                raw_html, cleaned_content = cached_content
                # Create a soup object from the raw HTML
                soup = BeautifulSoup(raw_html, 'lxml') if raw_html else None
            else:
                # Fetch the LinkedIn page
                raw_html, soup = crawler.web_crawler.fetch_webpage(linkedin_url)

                if raw_html and soup:
                    # Use site-specific extractor for better content extraction
                    cleaned_content = SiteSpecificExtractor.extract_linkedin_content(raw_html)
                    # Cache the content
                    db_manager.save_url_content(linkedin_url, raw_html, cleaned_content)
                else:
                    cleaned_content = ""

            if raw_html and soup:
                # Extract data using the LinkedIn extractor
                linkedin_data = LinkedInExtractor.extract_data(startup_name, linkedin_url, raw_html, soup)

                # Merge the extracted data
                for key, value in linkedin_data.items():
                    if value and (key not in startup_data or not startup_data[key]):
                        startup_data[key] = value

                logger.info(f"Extracted LinkedIn data for {startup_name}: {list(linkedin_data.keys())}")
        except Exception as e:
            logger.error(f"Error extracting data from LinkedIn {startup_data.get('LinkedIn')}: {e}")

    # Step 5: Gather additional information from general search results
    try:
        # Create a specific query for this startup
        specific_query = f"\"{startup_name}\" startup company information"

        # Check cache first
        cached_results = cache_manager.get_cached_value(f"info_search:{specific_query}")

        if cached_results:
            search_results = cached_results
            logger.info(f"Using cached info search results for {startup_name}")
        else:
            # Search for specific information about this startup
            search_results = crawler.google_search.search(specific_query, max_results=3)
            # Cache the results
            cache_manager.cache_value(f"info_search:{specific_query}", search_results)

        # Prepare URLs for parallel fetching
        urls_to_fetch = []
        url_to_result_map = {}

        for result in search_results:
            url = result.get("url", "")
            if url:
                # Skip URLs we've already processed
                if url == startup_data.get("Website") or url == startup_data.get("LinkedIn"):
                    continue
                urls_to_fetch.append(url)
                url_to_result_map[url] = result

        # Fetch webpages in parallel - use async if available
        try:
            # Try to use async fetching for better performance
            webpage_results = {}

            async def fetch_all():
                results = await ParallelProcessor.process_urls_async(urls_to_fetch)
                return results

            # Run the async function
            if urls_to_fetch:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                raw_results = loop.run_until_complete(fetch_all())
                loop.close()

                # Process the results
                for url, html_content in raw_results.items():
                    if html_content:
                        soup = BeautifulSoup(html_content, 'lxml')
                        webpage_results[url] = (html_content, soup)

            logger.info(f"Fetched {len(webpage_results)} pages asynchronously")
        except Exception as e:
            logger.warning(f"Async fetching failed: {e}. Falling back to parallel fetching.")
            # Fall back to the original parallel fetching
            webpage_results = crawler.web_crawler.fetch_webpages_parallel(urls_to_fetch)

        # Process each result
        for url, (raw_html, soup) in webpage_results.items():
            if not raw_html or not soup:
                continue

            result = url_to_result_map[url]

            # Use site-specific extractor for better content extraction
            cleaned_content = SiteSpecificExtractor.extract_content(url, raw_html)

            # Cache the content
            db_manager.save_url_content(url, raw_html, cleaned_content)

            # Extract basic information
            try:
                # Try to find location
                if "Location" not in startup_data or not startup_data["Location"]:
                    location_patterns = [
                        r"(?:located|based|headquarters) in ([^\.]+)",
                        r"(?:HQ|Headquarters):\s*([^,\.]+(?:,\s*[A-Z]{2})?)"
                    ]

                    for pattern in location_patterns:
                        location_match = re.search(pattern, cleaned_content, re.IGNORECASE)
                        if location_match:
                            startup_data["Location"] = location_match.group(1).strip()
                            break

                # Try to find founding year
                if "Founded Year" not in startup_data or not startup_data["Founded Year"]:
                    year_pattern = r"(?:founded|established|started) in (\d{4})"
                    year_match = re.search(year_pattern, cleaned_content, re.IGNORECASE)
                    if year_match:
                        startup_data["Founded Year"] = year_match.group(1)

                # Try to find product description
                if "Product Description" not in startup_data or not startup_data["Product Description"]:
                    # Use the snippet as a fallback
                    startup_data["Product Description"] = result.get("snippet", "")

                # Try to find industry
                if "Industry" not in startup_data or not startup_data["Industry"]:
                    industry_patterns = [
                        r"(?:industry|sector):\s*([^\.,]+)",
                        r"(?:operates|operating) in the ([^\.,]+) (?:industry|sector)"
                    ]

                    for pattern in industry_patterns:
                        industry_match = re.search(pattern, cleaned_content, re.IGNORECASE)
                        if industry_match:
                            startup_data["Industry"] = industry_match.group(1).strip()
                            break

                # Try to find funding information
                if "Funding" not in startup_data or not startup_data["Funding"]:
                    funding_patterns = [
                        r"(?:raised|secured|closed) (?:a|an)\s+([^\.,]+)\s+(?:funding|investment|round)",
                        r"(?:funding|investment) of\s+([^\.,]+)"
                    ]

                    for pattern in funding_patterns:
                        funding_match = re.search(pattern, cleaned_content, re.IGNORECASE)
                        if funding_match:
                            startup_data["Funding"] = funding_match.group(1).strip()
                            break

            except Exception as e:
                logger.error(f"Error extracting additional data from {url}: {e}")

    except Exception as e:
        logger.error(f"Error gathering additional info for {startup_name}: {e}")

    # Save the startup data to the database
    try:
        db_manager.save_startup(startup_name, startup_data, "enrichment", "")
        logger.info(f"Saved startup data for {startup_name} to database")
    except Exception as e:
        logger.warning(f"Failed to save startup data to database: {e}")

    return startup_data


def batch_enrich_startups(crawler: EnhancedStartupCrawler, startup_info_list: List[Dict[str, Any]],
                       metrics_collector: Optional["MetricsCollector"] = None) -> List[Dict[str, Any]]:
    """
    Enrich a batch of startups with detailed information using optimized parallel processing.

    This function uses:
    - Adaptive thread pool sizing based on system resources
    - Progressive loading with feedback
    - Database caching for results
    - Smart error handling and retry logic

    Args:
        crawler: StartupCrawler instance.
        startup_info_list: List of basic startup information.
        metrics_collector: Optional metrics collector.

    Returns:
        List of enriched startup data.
    """
    logger.info(f"Enriching data for {len(startup_info_list)} startups using optimized parallel processing")

    # Get optimal number of workers based on system resources
    max_workers = ParallelProcessor.get_optimal_workers()
    logger.info(f"Using {max_workers} worker threads based on system resources")

    # Create a progress tracker
    progress_tracker = ProgressTracker(len(startup_info_list), "Startup enrichment")

    # Check database for already processed startups
    enriched_results = []
    startups_to_process = []

    for startup_info in startup_info_list:
        startup_name = startup_info.get("Company Name", "Unknown")

        # Check if we already have this startup in the database
        cached_data = db_manager.get_startup(startup_name)
        if cached_data:
            logger.info(f"Using cached data for {startup_name} from database")
            enriched_results.append(cached_data)

            # Track startup for metrics
            if metrics_collector:
                metrics_collector.add_final_startup(startup_name, cached_data)
                metrics_collector.total_startups += 1

            # Update progress
            progress_tracker.update(1)
        else:
            # Add to list of startups to process
            startups_to_process.append(startup_info)

    logger.info(f"Found {len(enriched_results)} startups in cache, processing {len(startups_to_process)} new startups")

    # Process remaining startups in parallel
    if startups_to_process:
        # Use ThreadPoolExecutor with optimal number of workers
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit tasks for enriching each startup
            future_to_startup = {}
            for startup_info in startups_to_process:
                startup_name = startup_info.get("Company Name", "Unknown")
                logger.info(f"Submitting: {startup_name}")

                # Track startup for metrics
                if metrics_collector:
                    metrics_collector.add_final_startup(startup_name, startup_info)

                # Start timing for enrichment
                start_time = time.time()

                # Submit with retry logic already applied via decorator
                future = executor.submit(enrich_startup_data, crawler, startup_name)
                future_to_startup[future] = (startup_name, start_time, startup_info)

            # Process results as they complete
            for future in concurrent.futures.as_completed(future_to_startup):
                startup_name, start_time, startup_info = future_to_startup[future]
                try:
                    enriched_data = future.result()
                    enriched_results.append(enriched_data)

                    # Update progress
                    progress_tracker.update(1)

                    # Calculate processing time
                    processing_time = time.time() - start_time
                    logger.info(f"Completed: {startup_name} in {processing_time:.2f} seconds")
                    logger.debug(f"Data fields: {list(enriched_data.keys())}")

                    # Track enrichment time and field values for metrics
                    if metrics_collector:
                        metrics_collector.startup_enrichment_times.append(processing_time)
                        metrics_collector.startup_enrichment_time_map[startup_name] = processing_time

                        # Track field completion
                        for field, value in enriched_data.items():
                            if value:
                                metrics_collector.field_values[startup_name][field] = value
                                metrics_collector.field_counts[field] += 1

                        metrics_collector.total_startups += 1

                    # Save to database (redundant but ensures it's saved)
                    try:
                        db_manager.save_startup(startup_name, enriched_data, "batch_enrichment", "")
                    except Exception as db_error:
                        logger.warning(f"Error saving {startup_name} to database: {db_error}")

                except Exception as e:
                    logger.error(f"Error enriching data for {startup_name}: {e}")
                    # Add basic info to maintain order
                    basic_data = {"Company Name": startup_name, "Error": str(e)}
                    enriched_results.append(basic_data)

                    # Update progress even for errors
                    progress_tracker.update(1)

                    # Track error in metrics
                    if metrics_collector:
                        metrics_collector.add_error(f"Enrichment error for {startup_name}: {e}")

    # Mark progress as complete
    progress_tracker.complete()

    # Save session data
    try:
        session_id = f"batch_enrichment_{time.strftime('%Y%m%d_%H%M%S')}"
        session_data = {
            "startups_processed": len(startup_info_list),
            "startups_from_cache": len(startup_info_list) - len(startups_to_process),
            "new_startups_processed": len(startups_to_process),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        db_manager.save_session(session_id, "completed", session_data)
        logger.info(f"Saved session data with ID: {session_id}")
    except Exception as e:
        logger.warning(f"Error saving session data: {e}")

    logger.info(f"Enrichment complete. Processed {len(enriched_results)} startups")
    return enriched_results


@with_retry(max_retries=2, initial_wait=1.0, backoff_factor=2.0)
def validate_and_correct_data_with_gemini(enriched_data: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
    """
    Use Gemini 2.0 Flash with search grounding to validate and correct the startup data before CSV generation.
    Uses optimized parallel processing, caching, and smart retry logic.

    This function uses:
    - Adaptive batch processing to avoid rate limits
    - Caching of validation results
    - Circuit breaker pattern for API calls
    - Progressive loading with feedback
    - Database storage of validated results

    Args:
        enriched_data: List of enriched startup dictionaries.
        query: Original search query to provide context.

    Returns:
        List of validated and corrected startup data dictionaries.
    """
    logger.info("PHASE 3: DATA VALIDATION WITH GEMINI 2.0 FLASH AND SEARCH GROUNDING")
    logger.info("Validating and correcting data with Gemini 2.0 Flash using optimized processing")
    logger.info("Using gemini-2.0-flash model with web search capabilities")

    # Create a session ID for this validation run
    session_id = f"validation_{time.strftime('%Y%m%d_%H%M%S')}"

    # Create a progress tracker
    progress_tracker = ProgressTracker(len(enriched_data), "Startup validation")

    try:
        # Initialize the Gemini API client
        gemini_client = GeminiAPIClient()

        # Initialize the ContentProcessor for text cleaning and chunking
        content_processor = ContentProcessor(
            chunk_size=8000,   # Smaller chunk size for better performance
            overlap=500        # Smaller overlap for better performance
        )
        logger.info(f"Initialized ContentProcessor with chunk_size=8000, overlap=500")

        # Create a rate limiter for API calls
        rate_limiter = RateLimiter(calls_per_second=0.5, calls_per_minute=30)

        # Create a circuit breaker for API calls
        circuit_breaker = CircuitBreaker(failure_threshold=3, reset_timeout=60)

        # Check database for already validated startups
        validated_data = []
        startups_to_validate = []

        for i, startup in enumerate(enriched_data):
            startup_name = startup.get("Company Name", "Unknown")

            # Generate a unique key for this startup validation
            validation_key = f"validation:{startup_name}:{query}"

            # Check if we have cached validation results
            cached_result = cache_manager.get_cached_value(validation_key)

            if cached_result:
                logger.info(f"Using cached validation result for {startup_name}")
                validated_data.append(cached_result)

                # Update progress
                progress_tracker.update(1)
            else:
                # Add to list of startups to validate
                startups_to_validate.append((i, startup))

        logger.info(f"Found {len(validated_data)} startups in cache, validating {len(startups_to_validate)} new startups")

        # Prepare the data for processing
        # Convert each startup dictionary to a JSON string for processing
        startup_texts = []
        startup_indices = []

        for i, startup in startups_to_validate:
            # Convert the startup data to a formatted text representation
            startup_text = json.dumps(startup, indent=2)
            startup_texts.append(startup_text)
            startup_indices.append(i)

        if startup_texts:
            # Clean and chunk the startup texts
            # This helps handle large amounts of text more efficiently
            startup_metadata = [{"startup_index": i, "original_index": idx} for i, idx in enumerate(startup_indices)]
            chunks = content_processor.chunk_batch(startup_texts, startup_metadata)

            logger.info(f"Created {len(chunks)} chunks from {len(startup_texts)} startup texts")

            # Define the validation prompt
            validation_prompt = f"""
            You are a data validation expert for startup information. Your task is to validate and correct the information about a startup.

            Original search query: {query}

            Below is the startup data in JSON format. Please validate and correct any inaccuracies or inconsistencies.
            Focus on:
            1. Company name spelling and capitalization
            2. Website URL format and validity
            3. Location information
            4. Industry categorization
            5. Founded year (should be a valid year)
            6. Product/service description accuracy

            If any information is missing or seems incorrect, please correct it based on your knowledge.
            If you're unsure about any information, leave it as is.

            Return the corrected JSON data with the same structure.

            Startup data:
            {{startup_data}}
            """

            # Process chunks in batches to avoid rate limits
            batch_size = min(3, max(1, len(chunks) // 5))
            logger.info(f"Processing chunks in batches of {batch_size}")

            # Process chunks in batches
            chunk_results = []
            for batch_idx, batch in enumerate(MemoryOptimizer.chunk_large_list(chunks, batch_size)):
                logger.info(f"Processing batch {batch_idx+1}/{(len(chunks) + batch_size - 1) // batch_size}")

                # Process batch in parallel
                with concurrent.futures.ThreadPoolExecutor(max_workers=batch_size) as executor:
                    # Submit tasks for validating each chunk in the batch
                    future_to_chunk = {}
                    for chunk in batch:
                        chunk_text = chunk["chunk"]
                        chunk_sources = chunk["sources"]

                        # Create a function to call with rate limiting and circuit breaking
                        def validate_chunk():
                            # Wait if needed to respect rate limits
                            rate_limiter.wait_if_needed()

                            # Process the chunk with the Gemini API
                            return gemini_client.validate_startups_chunk(chunk_text, query,
                                                                        [s["startup_index"] for s in chunk_sources if "startup_index" in s])

                        # Submit the task with circuit breaker protection
                        future = executor.submit(
                            circuit_breaker.execute,
                            validate_chunk
                        )
                        future_to_chunk[future] = chunk

                        # Log progress
                        logger.info(f"Submitted chunk {chunk['chunk_index']+1}/{chunk['total_chunks']} for validation")

                    # Process results as they complete
                    for future in concurrent.futures.as_completed(future_to_chunk):
                        chunk = future_to_chunk[future]

                        try:
                            # Get the validation result
                            validated_chunk = future.result()
                            chunk_results.append(validated_chunk)

                            # Update progress based on number of startups in this chunk
                            num_startups = len([s for s in chunk["sources"] if "startup_index" in s])
                            progress_tracker.update(num_startups)

                            # Log progress
                            logger.info(f"Validated chunk {chunk['chunk_index']+1}/{chunk['total_chunks']} with {num_startups} startups")

                        except Exception as e:
                            logger.error(f"Error validating chunk {chunk['chunk_index']+1}/{chunk['total_chunks']}: {e}")
                            # Don't update progress here, will handle missing startups later

                # Add a delay between batches to avoid rate limits
                if batch_idx < (len(chunks) + batch_size - 1) // batch_size - 1:
                    logger.info(f"Waiting 5 seconds before processing next batch...")
                    time.sleep(5)

            # Combine the validated chunks into a single result
            new_validated_data = gemini_client.combine_validated_chunks(chunk_results,
                                                                      [enriched_data[i] for _, i in startups_to_validate])

            # Cache the validated results
            for i, startup in enumerate(new_validated_data):
                startup_name = startup.get("Company Name", "Unknown")
                validation_key = f"validation:{startup_name}:{query}"
                cache_manager.cache_value(validation_key, startup)

                # Save to database
                try:
                    db_manager.save_startup(startup_name, startup, "validation", query)
                except Exception as db_error:
                    logger.warning(f"Error saving {startup_name} to database: {db_error}")

            # Add the new validated data to the results
            validated_data.extend(new_validated_data)

        # Ensure the validated data is in the same order as the input data
        if len(validated_data) != len(enriched_data):
            logger.warning(f"Validated data length ({len(validated_data)}) doesn't match input data length ({len(enriched_data)})")

            # Create a mapping of company names to validated data
            validated_map = {item.get("Company Name", f"Unknown_{i}"): item
                            for i, item in enumerate(validated_data)}

            # Rebuild the validated data in the original order
            ordered_validated_data = []
            for startup in enriched_data:
                name = startup.get("Company Name", "Unknown")
                if name in validated_map:
                    ordered_validated_data.append(validated_map[name])
                else:
                    # If we don't have validated data for this startup, use the original
                    ordered_validated_data.append(startup)
                    logger.warning(f"No validated data found for {name}, using original data")

            validated_data = ordered_validated_data

        # Mark progress as complete
        progress_tracker.complete()

        # Save session data
        try:
            session_data = {
                "startups_processed": len(enriched_data),
                "startups_from_cache": len(enriched_data) - len(startups_to_validate),
                "new_startups_validated": len(startups_to_validate),
                "query": query,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            db_manager.save_session(session_id, "completed", session_data)
            logger.info(f"Saved validation session data with ID: {session_id}")
        except Exception as e:
            logger.warning(f"Error saving validation session data: {e}")

        logger.info(f"Validation complete. Processed {len(validated_data)} startups")
        return validated_data

    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Error validating data with Gemini 2.0 Flash: {e}")
        logger.debug(f"Error traceback: {error_traceback}")

        # Save session data with error status
        try:
            session_data = {
                "startups_processed": len(enriched_data),
                "error": str(e),
                "query": query,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            db_manager.save_session(session_id, "error", session_data)
        except Exception as db_error:
            logger.warning(f"Error saving validation session data: {db_error}")

        logger.warning("Proceeding with original data due to validation error")
        return enriched_data


def load_intermediate_results(filepath: str) -> List[Dict[str, Any]]:
    """
    Load intermediate results from a CSV file.

    Args:
        filepath: Path to the CSV file containing intermediate results.

    Returns:
        List of startup dictionaries loaded from the file.
    """
    try:
        if not os.path.exists(filepath):
            logger.error(f"Intermediate results file not found: {filepath}")
            return []

        startups = []
        with open(filepath, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                startups.append(row)

        logger.info(f"Loaded {len(startups)} startups from {filepath}")
        print(f"Loaded {len(startups)} startups from {filepath}")
        return startups
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Error loading intermediate results: {e}")
        logger.debug(f"Error traceback: {error_traceback}")
        print(f"Error loading intermediate results: {e}")
        return []

def find_latest_intermediate_file(phase: str = None) -> str:
    """
    Find the latest intermediate results file for a given phase.

    Args:
        phase: Optional phase to filter by (e.g., "discovery", "enrichment", "validation").

    Returns:
        Path to the latest intermediate results file, or None if not found.
    """
    try:
        if not os.path.exists("output/intermediate"):
            return None

        files = os.listdir("output/intermediate")

        # Filter by phase if specified
        if phase:
            files = [f for f in files if f"_{phase}_" in f or f"_{phase}." in f]

        # Filter CSV files only
        files = [f for f in files if f.endswith(".csv")]

        if not files:
            return None

        # Sort by timestamp (assuming format includes YYYYMMDD_HHMMSS)
        files.sort(key=lambda x: re.findall(r'(\d{8}_\d{6})', x)[-1] if re.findall(r'(\d{8}_\d{6})', x) else "", reverse=True)

        # Return the most recent file
        return os.path.join("output/intermediate", files[0])
    except Exception as e:
        logger.error(f"Error finding latest intermediate file: {e}")
        return None

def save_intermediate_results(data: List[Dict[str, Any]], base_filename: str, phase: str, batch_num: int = None) -> str:
    """
    Save intermediate results to a CSV file to prevent data loss.

    Args:
        data: List of startup dictionaries to save.
        base_filename: Base filename for the output file.
        phase: Current processing phase (e.g., "discovery", "enrichment", "validation").
        batch_num: Optional batch number for incremental saves within a phase.

    Returns:
        str: Path to the saved file.
    """
    # Create directory if it doesn't exist
    os.makedirs("output/intermediate", exist_ok=True)

    # Generate filename
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    if batch_num is not None:
        filename = f"output/intermediate/{base_filename}_{phase}_batch{batch_num}_{timestamp}.csv"
    else:
        filename = f"output/intermediate/{base_filename}_{phase}_{timestamp}.csv"

    try:
        # Define the fields we want to include in the CSV
        all_fields = set()
        for startup in data:
            all_fields.update(startup.keys())

        fields = ["Company Name"] + sorted([f for f in all_fields if f != "Company Name"])

        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fields)

            # Write the header
            writer.writeheader()

            # Write the data
            for startup in data:
                writer.writerow(startup)

        logger.info(f"Saved intermediate results to {filename}")
        print(f"Saved intermediate results to {filename}")
        return filename
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Error saving intermediate results: {e}")
        logger.debug(f"Error traceback: {error_traceback}")
        print(f"Error saving intermediate results: {e}")
        return None

def generate_csv_from_startups(enriched_data: List[Dict[str, Any]], output_file: str, create_dir: bool = True) -> bool:
    """
    Generate a CSV file from the enriched startup data.

    Args:
        enriched_data: List of enriched startup dictionaries.
        output_file: Path to the output CSV file.
        create_dir: Whether to create the directory if it doesn't exist.

    Returns:
        bool: True if CSV generation was successful, False otherwise.
    """
    # Define the fields we want to include in the CSV
    fields = [
        "Company Name",
        "Website",
        "LinkedIn",
        "Location",
        "Founded Year",
        "Industry",
        "Company Size",
        "Funding",
        "Product Description",
        "Products/Services",
        "Founders",
        "Founder LinkedIn Profiles",
        "CEO/Leadership",
        "Team",
        "Technology Stack",
        "Competitors",
        "Market Focus",
        "Social Media Links",
        "Latest News",
        "Investors",
        "Growth Metrics",
        "Contact",
        "Source URL"
    ]

    try:
        # Create directory if it doesn't exist and create_dir is True
        if create_dir:
            output_dir = os.path.dirname(output_file)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
                logger.info(f"Created directory: {output_dir}")

        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fields)

            # Write the header
            writer.writeheader()

            # Write the data
            for startup in enriched_data:
                # Create a row with only the fields we want
                row = {}
                for field in fields:
                    if field == "Source URL":
                        row[field] = startup.get("Original URL", "")
                    else:
                        row[field] = startup.get(field, "")
                writer.writerow(row)

        logger.info(f"CSV file generated: {output_file}")
        return True
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Error generating CSV file: {e}")
        logger.debug(f"Error traceback: {error_traceback}")
        return False


def check_environment_setup():
    """Check if the environment is properly set up with required API keys."""
    missing_keys = []

    # Check for Gemini API key
    if not os.environ.get("GEMINI_API_KEY"):
        missing_keys.append("GEMINI_API_KEY")

    # Check for Google Search API keys (numbered format)
    google_api_keys_found = False
    i = 1
    while True:
        key = os.environ.get(f"GOOGLE_SEARCH_API_KEY_{i}")
        if not key:
            break
        google_api_keys_found = True
        i += 1

    # Check for legacy Google Search API key
    if not google_api_keys_found and not os.environ.get("GOOGLE_SEARCH_API_KEY"):
        missing_keys.append("GOOGLE_SEARCH_API_KEY")

    # Check for Google Custom Search Engine IDs (numbered format)
    google_cx_ids_found = False
    i = 1
    while True:
        cx = os.environ.get(f"GOOGLE_CX_ID_{i}")
        if not cx:
            break
        google_cx_ids_found = True
        i += 1

    # Check for legacy Google CX ID
    if not google_cx_ids_found and not os.environ.get("GOOGLE_CX_ID"):
        missing_keys.append("GOOGLE_CX_ID")

    if missing_keys:
        error_msg = f"Missing required environment variables: {', '.join(missing_keys)}"
        logger.error(error_msg)
        return False, error_msg

    return True, "Environment is properly set up"


def validate_find_mode_inputs(query, max_results, num_expansions):
    """Validate inputs for find mode."""
    errors = []

    # Check query
    if not query or not query.strip():
        errors.append("Search query cannot be empty")

    # Check max_results
    if not isinstance(max_results, int) or max_results <= 0:
        errors.append("Maximum results must be a positive integer")

    # Check num_expansions
    if not isinstance(num_expansions, int) or num_expansions < 0:
        errors.append("Number of expansions must be a non-negative integer")

    if errors:
        return False, errors

    return True, "Inputs are valid"


def validate_enrich_mode_inputs(input_file):
    """Validate inputs for enrich mode."""
    errors = []

    # Check if input file exists
    if not input_file or not input_file.strip():
        errors.append("Input file path cannot be empty")
    elif not os.path.exists(input_file):
        errors.append(f"Input file does not exist: {input_file}")
    else:
        # Check if input file is a valid CSV
        try:
            with open(input_file, 'r', newline='') as f:
                reader = csv.reader(f)
                header = next(reader, None)

                if not header:
                    errors.append("Input CSV file is empty")
                elif "Name" not in header and "Company Name" not in header:
                    errors.append("Input CSV file must have a 'Name' or 'Company Name' column")

                # Check if there's at least one row of data
                if not any(row for row in reader):
                    errors.append("Input CSV file does not contain any startup names")
        except csv.Error:
            errors.append(f"File is not a valid CSV: {input_file}")
        except Exception as e:
            errors.append(f"Error reading input file: {str(e)}")

    if errors:
        return False, errors

    return True, "Input file is valid"


def validate_both_mode_inputs(query, direct_startups, max_results, num_expansions):
    """Validate inputs for both mode."""
    errors = []

    # Check if either query or direct_startups is provided
    if (not query or not query.strip()) and (not direct_startups or len(direct_startups) == 0):
        errors.append("Either search query or direct startups must be provided")

    # If query is provided, validate it
    if query and query.strip():
        valid, query_errors = validate_find_mode_inputs(query, max_results, num_expansions)
        if not valid:
            errors.extend(query_errors)

    # If direct_startups is provided, validate it
    if direct_startups:
        if not all(name.strip() for name in direct_startups):
            errors.append("Startup names cannot be empty")

    if errors:
        return False, errors

    return True, "Inputs are valid"


def validate_output_file(output_file):
    """Validate and prepare output file path."""
    if not output_file:
        # Generate default output file name
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_file = f"output/data/startups_{timestamp}.csv"

    # Add .csv extension if not provided
    if not output_file.endswith('.csv'):
        output_file += '.csv'

    # Check if output directory exists, create if not
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            return False, f"Error creating output directory: {str(e)}", None

    # Check if output file is writable
    try:
        # Try to open the file for writing
        open(output_file, 'w').close()
        # Remove the empty file
        os.remove(output_file)
    except Exception as e:
        return False, f"Output file is not writable: {str(e)}", None

    return True, "Output file is valid", output_file


def load_startups_from_csv(input_file):
    """Load startup names from a CSV file."""
    startup_info_list = []
    try:
        with open(input_file, 'r', newline='') as f:
            reader = csv.DictReader(f)

            # Check if the CSV has the required columns
            header = reader.fieldnames
            if not header:
                raise ValueError("CSV file is empty")

            name_column = None
            if "Name" in header:
                name_column = "Name"
            elif "Company Name" in header:
                name_column = "Company Name"
            else:
                raise ValueError("CSV file must have a 'Name' or 'Company Name' column")

            # Read startup names
            for row in reader:
                name = row.get(name_column, "").strip()
                if name:
                    startup_info_list.append({"Company Name": name})

            if not startup_info_list:
                raise ValueError("No valid startup names found in the CSV file")

    except csv.Error as e:
        raise ValueError(f"Error parsing CSV file: {str(e)}")
    except Exception as e:
        raise ValueError(f"Error reading input file: {str(e)}")

    return startup_info_list


def find_startups(query, max_results=10, num_expansions=5, output_file=None, use_query_expansion=True, metrics_collector=None, batch_size=500):
    """
    Find startups based on search queries and save to CSV.

    This function only performs the discovery phase without enrichment.

    Args:
        query: Search query to find startups.
        max_results: Maximum number of search results to process per query (default: 10).
        num_expansions: Number of query expansions to generate (default: 5).
        output_file: Path to the output CSV file.
        use_query_expansion: Whether to use query expansion.
        metrics_collector: Optional metrics collector.
        batch_size: Number of URLs to process in each batch (default: 500).

    Returns:
        List of discovered startup info dictionaries or None if an error occurred.
    """
    # Validate environment
    env_valid, env_msg = check_environment_setup()
    if not env_valid:
        logger.error(env_msg)
        print(f"Error: {env_msg}")
        return None

    # Validate inputs
    inputs_valid, input_errors = validate_find_mode_inputs(query, max_results, num_expansions)
    if not inputs_valid:
        error_msg = "\n".join(input_errors)
        logger.error(f"Invalid inputs for find mode: {error_msg}")
        print(f"Error: {error_msg}")
        return None

    # Validate output file
    output_valid, output_msg, validated_output_file = validate_output_file(output_file)
    if not output_valid:
        logger.error(output_msg)
        print(f"Error: {output_msg}")
        return None

    # Create an enhanced crawler with maximum parallel processing and API key rotation
    max_workers = 30  # Use a high number of workers for maximum speed

    # Initialize the API key manager
    from src.utils.api_key_manager import APIKeyManager
    key_manager = APIKeyManager()

    # Create the enhanced crawler with API key rotation
    crawler = EnhancedStartupCrawler(max_workers=max_workers, key_manager=key_manager)
    print(f"Using {max_workers} parallel workers for maximum speed")
    print(f"Using {len(key_manager.api_keys)} API keys and {len(key_manager.cx_ids)} CX IDs for rotation")

    # Initialize query expander if needed
    expanded_queries = [query]  # Default to just the original query
    if use_query_expansion:
        try:
            # Initialize the API client and query expander
            gemini_client = GeminiAPIClient()
            query_expander = QueryExpander(api_client=gemini_client)

            # Expand the query using parallel processing - use fewer expansions to reduce API calls
            print("\nExpanding search query using parallel processing...")
            start_time = time.time()
            # Limit the number of expansions to reduce API calls
            actual_num_expansions = min(num_expansions, 5)  # Cap at 5 expansions to reduce API calls
            expanded_queries = query_expander.expand_query_parallel(query, num_expansions=actual_num_expansions)
            end_time = time.time()

            print(f"\nExpanded queries (generated in {end_time - start_time:.2f} seconds):")
            for i, expanded_query in enumerate(expanded_queries):
                print(f"  {i+1}. {expanded_query}")

            # Allow manual editing of the expanded queries
            print("\nWould you like to manually edit the expanded queries? (y/n)")
            edit_choice = input("Your choice: ").strip().lower()
            if edit_choice == 'y' or edit_choice == 'yes':
                expanded_queries = edit_queries_manually(expanded_queries)
        except Exception as e:
            logger.error(f"Error expanding query: {e}")
            print(f"\nError expanding query: {e}")
            print("Proceeding with original query only.")
            expanded_queries = [query]

    # Phase 1: Discover startup names with LLM filtering
    print("\n" + "=" * 80)
    print("STARTUP DISCOVERY")
    print("=" * 80)

    start_time = time.time()
    all_startup_info = []

    print(f"Searching for: {len(expanded_queries)} queries")
    print(f"Processing up to {max_results} search results per query")
    print("This may take a few minutes...")

    # Generate base filename for intermediate results
    base_filename = f"startup_finder_{time.strftime('%Y%m%d_%H%M%S')}"

    # Process each expanded query
    for i, expanded_query in enumerate(expanded_queries):
        print(f"\nProcessing query {i+1}/{len(expanded_queries)}: {expanded_query}")

        # Process in batches based on batch_size
        # For search queries, we'll divide max_results into batches
        # Use a smaller batch size to reduce API calls
        results_per_batch = min(batch_size, max_results, 5)  # Cap at 5 results per batch to reduce API calls
        num_batches = min(2, (max_results + results_per_batch - 1) // results_per_batch)  # Limit to 2 batches for faster processing

        query_startup_info = []

        for j in range(num_batches):
            batch_start = j * results_per_batch
            batch_end = min((j + 1) * results_per_batch, max_results)
            batch_size_actual = batch_end - batch_start

            if batch_size_actual <= 0:
                break

            print(f"  Processing batch {j+1}/{num_batches}: results {batch_start+1}-{batch_end}")

            # Discover startups for this batch
            batch_results = crawler.discover_startups(
                expanded_query,
                max_results=batch_size_actual,
                start_index=batch_start,
                metrics_collector=metrics_collector
            )

            # Add batch results to query results
            query_startup_info.extend(batch_results)

            # Save intermediate results after each batch
            if batch_results:
                save_intermediate_results(
                    batch_results,
                    f"{base_filename}_query{i+1}_batch{j+1}",
                    "discovery"
                )

            print(f"  Found {len(batch_results)} startups in this batch")
            print(f"  Total for query so far: {len(query_startup_info)}")

        # Add to the combined list, avoiding duplicates
        existing_names = {startup.get("Company Name", "").lower() for startup in all_startup_info}
        for startup in query_startup_info:
            name = startup.get("Company Name", "").lower()
            if name and name not in existing_names:
                all_startup_info.append(startup)
                existing_names.add(name)

        print(f"Found {len(query_startup_info)} startups from this query")
        print(f"Total unique startups so far: {len(all_startup_info)}")

        # Save intermediate results after each query
        if all_startup_info:
            save_intermediate_results(all_startup_info, base_filename, "discovery", i+1)

    discovery_time = time.time() - start_time

    print(f"\nDiscovery completed in {discovery_time:.2f} seconds")
    print(f"Found {len(all_startup_info)} unique startups across all queries")

    if not all_startup_info:
        print("\nNo startups found. Exiting.")
        return None

    # Generate CSV file with just the names and basic info
    success = generate_csv_from_startups(all_startup_info, validated_output_file, create_dir=True)

    if success:
        # Generate reports
        if metrics_collector:
            from src.utils.report_generator import export_consolidated_reports

            # Generate timestamp for report filenames
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            base_filename = f"startup_finder_find_{timestamp}"

            # Export consolidated reports
            report_files = export_consolidated_reports(metrics_collector, base_filename)

            # Summary
            print("\n" + "=" * 80)
            print("SUMMARY")
            print("=" * 80)
            print(f"Original search query: {query}")
            print(f"Number of expanded queries: {len(expanded_queries)}")
            print(f"Discovery time: {discovery_time:.2f} seconds")
            print(f"Startups found: {len(all_startup_info)}")
            print(f"CSV file generated: {validated_output_file}")
            print(f"Metrics report: {report_files['metrics']}")
        else:
            print(f"\nCSV file generated: {validated_output_file}")
    else:
        print("\nFailed to generate CSV file.")

    return all_startup_info


def enrich_startups_from_data(startup_data, output_file, metrics_collector=None):
    """
    Enrich startup data from a list of dictionaries.

    This function only performs the enrichment phase without discovery.

    Args:
        startup_data: List of startup dictionaries.
        output_file: Path to the output CSV file.
        metrics_collector: Optional metrics collector.

    Returns:
        List of enriched startup data dictionaries or None if an error occurred.
    """
    # Validate environment
    env_valid, env_msg = check_environment_setup()
    if not env_valid:
        logger.error(env_msg)
        print(f"Error: {env_msg}")
        return None

    # Validate output file
    output_valid, output_msg, validated_output_file = validate_output_file(output_file)
    if not output_valid:
        logger.error(output_msg)
        print(f"Error: {output_msg}")
        return None

    # Create an enhanced crawler with maximum parallel processing and API key rotation
    max_workers = 30  # Use a high number of workers for maximum speed

    # Initialize the API key manager
    from src.utils.api_key_manager import APIKeyManager
    key_manager = APIKeyManager()

    # Create the enhanced crawler with API key rotation
    crawler = EnhancedStartupCrawler(max_workers=max_workers, key_manager=key_manager)
    print(f"Using {max_workers} parallel workers for maximum speed")
    print(f"Using {len(key_manager.api_keys)} API keys and {len(key_manager.cx_ids)} CX IDs for rotation")

    # Generate base filename for intermediate results
    base_filename = f"startup_finder_{time.strftime('%Y%m%d_%H%M%S')}"

    # Phase 1: Enrich startup data
    print("\n" + "=" * 80)
    print("DATA ENRICHMENT")
    print("=" * 80)
    print(f"Enriching data for {len(startup_data)} startups")
    print("This may take a few minutes...")

    start_time = time.time()

    # Batch process startups and save intermediate results after each batch
    batch_size = max(1, min(10, len(startup_data) // 5))  # Process in batches of ~20% of total
    enriched_results = []

    for i in range(0, len(startup_data), batch_size):
        batch = startup_data[i:i+batch_size]
        print(f"\nEnriching batch {i//batch_size + 1}/{(len(startup_data) + batch_size - 1) // batch_size}: {len(batch)} startups")

        batch_enriched = batch_enrich_startups(crawler, batch, metrics_collector=metrics_collector)
        enriched_results.extend(batch_enriched)

        # Save intermediate results after each batch
        save_intermediate_results(enriched_results, base_filename, "enrichment", i//batch_size + 1)

    enrichment_time = time.time() - start_time

    print(f"\nEnrichment completed in {enrichment_time:.2f} seconds")

    # Phase 2: Validate and correct data with Gemini 2.0 Flash
    print("\n" + "=" * 80)
    print("DATA VALIDATION WITH SEARCH GROUNDING")
    print("=" * 80)
    print("Using Gemini 2.0 Flash with search grounding to validate and correct startup data")
    print("This allows the AI to access real-time information from the web for more accurate results")

    start_time = time.time()

    # Batch process validation to save intermediate results
    batch_size = max(1, min(10, len(enriched_results) // 5))  # Process in batches of ~20% of total
    validated_results = []

    for i in range(0, len(enriched_results), batch_size):
        batch = enriched_results[i:i+batch_size]
        print(f"\nValidating batch {i//batch_size + 1}/{(len(enriched_results) + batch_size - 1) // batch_size}: {len(batch)} startups")

        batch_validated = validate_and_correct_data_with_gemini(batch, "startup companies")
        validated_results.extend(batch_validated)

        # Save intermediate results after each batch
        save_intermediate_results(validated_results, base_filename, "validation", i//batch_size + 1)

    validation_time = time.time() - start_time

    print(f"\nValidation completed in {validation_time:.2f} seconds")
    print(f"Validated {len(validated_results)} startups using search grounding")

    # Generate CSV file
    success = generate_csv_from_startups(validated_results, validated_output_file, create_dir=True)

    if success:
        # Generate reports
        if metrics_collector:
            from src.utils.report_generator import export_consolidated_reports

            # Generate timestamp for report filenames
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            base_filename = f"startup_finder_enrich_{timestamp}"

            # Export consolidated reports
            report_files = export_consolidated_reports(metrics_collector, base_filename)

            # Summary
            print("\n" + "=" * 80)
            print("SUMMARY")
            print("=" * 80)
            print(f"Enrichment time: {enrichment_time:.2f} seconds")
            print(f"Validation time: {validation_time:.2f} seconds")
            print(f"Total time: {enrichment_time + validation_time:.2f} seconds")
            print(f"Startups enriched: {len(validated_results)}")
            print(f"CSV file generated: {validated_output_file}")
            print(f"Metrics report: {report_files['metrics']}")
        else:
            print(f"\nCSV file generated: {validated_output_file}")
    else:
        print("\nFailed to generate CSV file.")

    return validated_results

def enrich_startups(input_file, output_file, metrics_collector=None):
    """
    Enrich existing startup data from a CSV file and save to a new CSV.

    This function only performs the enrichment phase without discovery.

    Args:
        input_file: Path to input CSV file with startup names.
        output_file: Path to the output CSV file.
        metrics_collector: Optional metrics collector.

    Returns:
        List of enriched startup data dictionaries or None if an error occurred.
    """
    # Validate environment
    env_valid, env_msg = check_environment_setup()
    if not env_valid:
        logger.error(env_msg)
        print(f"Error: {env_msg}")
        return None

    # Validate inputs
    inputs_valid, input_errors = validate_enrich_mode_inputs(input_file)
    if not inputs_valid:
        error_msg = "\n".join(input_errors)
        logger.error(f"Invalid inputs for enrich mode: {error_msg}")
        print(f"Error: {error_msg}")
        return None

    # Validate output file
    output_valid, output_msg, validated_output_file = validate_output_file(output_file)
    if not output_valid:
        logger.error(output_msg)
        print(f"Error: {output_msg}")
        return None

    # Load startup names from CSV
    try:
        startup_info_list = load_startups_from_csv(input_file)
        print(f"Loaded {len(startup_info_list)} startup names from {input_file}")
    except Exception as e:
        logger.error(f"Error loading startup names: {e}")
        print(f"Error: {e}")
        return None

    # Create an enhanced crawler with maximum parallel processing and API key rotation
    max_workers = 30  # Use a high number of workers for maximum speed

    # Initialize the API key manager
    from src.utils.api_key_manager import APIKeyManager
    key_manager = APIKeyManager()

    # Create the enhanced crawler with API key rotation
    crawler = EnhancedStartupCrawler(max_workers=max_workers, key_manager=key_manager)
    print(f"Using {max_workers} parallel workers for maximum speed")
    print(f"Using {len(key_manager.api_keys)} API keys and {len(key_manager.cx_ids)} CX IDs for rotation")

    # Phase 1: Enrich startup data
    print("\n" + "=" * 80)
    print("DATA ENRICHMENT")
    print("=" * 80)
    print(f"Enriching data for {len(startup_info_list)} startups")
    print("This may take a few minutes...")

    start_time = time.time()

    # Generate base filename for intermediate results
    base_filename = f"startup_finder_{time.strftime('%Y%m%d_%H%M%S')}"

    # Batch process startups and save intermediate results after each batch
    batch_size = max(1, min(10, len(startup_info_list) // 5))  # Process in batches of ~20% of total
    enriched_results = []

    for i in range(0, len(startup_info_list), batch_size):
        batch = startup_info_list[i:i+batch_size]
        print(f"\nEnriching batch {i//batch_size + 1}/{(len(startup_info_list) + batch_size - 1) // batch_size}: {len(batch)} startups")

        batch_enriched = crawler.enrich_startup_data(batch, metrics_collector=metrics_collector)
        enriched_results.extend(batch_enriched)

        # Save intermediate results after each batch
        save_intermediate_results(enriched_results, base_filename, "enrichment", i//batch_size + 1)

    enrichment_time = time.time() - start_time

    print(f"\nEnrichment completed in {enrichment_time:.2f} seconds")

    # Phase 2: Validate and correct data with Gemini 2.0 Flash
    print("\n" + "=" * 80)
    print("DATA VALIDATION WITH SEARCH GROUNDING")
    print("=" * 80)
    print("Using Gemini 2.0 Flash with search grounding to validate and correct startup data")
    print("This allows the AI to access real-time information from the web for more accurate results")

    start_time = time.time()

    # Batch process validation to save intermediate results
    batch_size = max(1, min(10, len(enriched_results) // 5))  # Process in batches of ~20% of total
    validated_results = []

    for i in range(0, len(enriched_results), batch_size):
        batch = enriched_results[i:i+batch_size]
        print(f"\nValidating batch {i//batch_size + 1}/{(len(enriched_results) + batch_size - 1) // batch_size}: {len(batch)} startups")

        batch_validated = validate_and_correct_data_with_gemini(batch, "startup companies")
        validated_results.extend(batch_validated)

        # Save intermediate results after each batch
        save_intermediate_results(validated_results, base_filename, "validation", i//batch_size + 1)

    validation_time = time.time() - start_time

    print(f"\nValidation completed in {validation_time:.2f} seconds")
    print(f"Validated {len(validated_results)} startups using search grounding")

    # Save final validated results
    save_intermediate_results(validated_results, base_filename, "final_validation")

    # Generate CSV file
    success = generate_csv_from_startups(validated_results, validated_output_file, create_dir=True)

    if success:
        # Generate reports
        if metrics_collector:
            from src.utils.report_generator import export_consolidated_reports

            # Generate timestamp for report filenames
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            base_filename = f"startup_finder_enrich_{timestamp}"

            # Export consolidated reports
            report_files = export_consolidated_reports(metrics_collector, base_filename)

            # Summary
            print("\n" + "=" * 80)
            print("SUMMARY")
            print("=" * 80)
            print(f"Enrichment time: {enrichment_time:.2f} seconds")
            print(f"Validation time: {validation_time:.2f} seconds")
            print(f"Total time: {enrichment_time + validation_time:.2f} seconds")
            print(f"Startups enriched: {len(validated_results)}")
            print(f"CSV file generated: {validated_output_file}")
            print(f"Metrics report: {report_files['metrics']}")
        else:
            print(f"\nCSV file generated: {validated_output_file}")
    else:
        print("\nFailed to generate CSV file.")

    return validated_results


def find_and_enrich_startups(query, max_results, num_expansions, output_file, use_query_expansion,
                        direct_startups=None, metrics_collector=None, resume_data=None, start_phase="discovery"):
    """
    Find and enrich startups (combines both functions).

    Args:
        query: Search query to find startups.
        max_results: Maximum number of search results to process per query.
        num_expansions: Number of query expansions to generate.
        output_file: Path to the output CSV file.
        use_query_expansion: Whether to use query expansion.
        direct_startups: List of startup names to directly search for.
        metrics_collector: Optional metrics collector.
        resume_data: Optional data to resume from a checkpoint.
        start_phase: Phase to start from when resuming ("discovery", "enrichment", "validation").

    Returns:
        bool: True if successful, False otherwise.
    """
    # Validate environment
    env_valid, env_msg = check_environment_setup()
    if not env_valid:
        logger.error(env_msg)
        print(f"Error: {env_msg}")
        return False

    # Validate inputs
    inputs_valid, input_errors = validate_both_mode_inputs(query, direct_startups, max_results, num_expansions)
    if not inputs_valid:
        error_msg = "\n".join(input_errors)
        logger.error(f"Invalid inputs for both mode: {error_msg}")
        print(f"Error: {error_msg}")
        return False

    # Validate output file
    output_valid, output_msg, validated_output_file = validate_output_file(output_file)
    if not output_valid:
        logger.error(output_msg)
        print(f"Error: {output_msg}")
        return False

    # Create an enhanced crawler with maximum parallel processing and API key rotation
    max_workers = 30  # Use a high number of workers for maximum speed

    # Initialize the API key manager
    from src.utils.api_key_manager import APIKeyManager
    key_manager = APIKeyManager()

    # Create the enhanced crawler with API key rotation
    crawler = EnhancedStartupCrawler(max_workers=max_workers, key_manager=key_manager)
    print(f"Using {max_workers} parallel workers for maximum speed")
    print(f"Using {len(key_manager.api_keys)} API keys and {len(key_manager.cx_ids)} CX IDs for rotation")

    # Create a metrics collector if not provided
    if metrics_collector is None:
        from src.utils.metrics_collector import MetricsCollector
        metrics_collector = MetricsCollector()

    # Initialize query expander if needed
    expanded_queries = [query]  # Default to just the original query
    if use_query_expansion:
        try:
            # Initialize the API client and query expander
            gemini_client = GeminiAPIClient()
            query_expander = QueryExpander(api_client=gemini_client)

            # Expand the query using parallel processing
            print("\nExpanding search query using parallel processing...")
            start_time = time.time()
            expanded_queries = query_expander.expand_query_parallel(query, num_expansions=num_expansions)
            end_time = time.time()

            print(f"\nExpanded queries (generated in {end_time - start_time:.2f} seconds):")
            for i, expanded_query in enumerate(expanded_queries):
                print(f"  {i+1}. {expanded_query}")

            # Allow manual editing of the expanded queries
            print("\nWould you like to manually edit the expanded queries? (y/n)")
            edit_choice = input("Your choice: ").strip().lower()
            if edit_choice == 'y' or edit_choice == 'yes':
                expanded_queries = edit_queries_manually(expanded_queries)
        except Exception as e:
            logger.error(f"Error expanding query: {e}")
            print(f"\nError expanding query: {e}")
            print("Proceeding with original query only.")
            expanded_queries = [query]

    # Generate base filename for intermediate results
    base_filename = f"startup_finder_{time.strftime('%Y%m%d_%H%M%S')}"

    # Initialize startup info list
    all_startup_info = []

    # If resuming from a checkpoint, use the resume data
    if resume_data and start_phase != "discovery":
        all_startup_info = resume_data
        print(f"Resuming with {len(all_startup_info)} startups from checkpoint")
        phase1_time = 0  # Skip phase 1 timing
    else:
        # Phase 1: Discover startup names with LLM filtering
        print("\n" + "=" * 80)
        print("PHASE 1: STARTUP DISCOVERY")
        print("=" * 80)

        start_time = time.time()

        # If direct startups are provided, use them instead of discovery
        if direct_startups and len(direct_startups) > 0:
            print(f"Using {len(direct_startups)} directly provided startups:")
            for startup_name in direct_startups:
                print(f"- {startup_name}")
                all_startup_info.append({"Company Name": startup_name})
        else:
            print(f"Searching for: {len(expanded_queries)} queries")
            print(f"Processing up to {max_results} search results per query")
            print("This may take a few minutes...")

            # Process each expanded query
            for i, expanded_query in enumerate(expanded_queries):
                print(f"\nProcessing query {i+1}/{len(expanded_queries)}: {expanded_query}")

                # Discover startups for this query
                startup_info_list = crawler.discover_startups(expanded_query, max_results=max_results, metrics_collector=metrics_collector)

                # Add to the combined list, avoiding duplicates
                existing_names = {startup.get("Company Name", "").lower() for startup in all_startup_info}
                for startup in startup_info_list:
                    name = startup.get("Company Name", "").lower()
                    if name and name not in existing_names:
                        all_startup_info.append(startup)
                        existing_names.add(name)

                print(f"Found {len(startup_info_list)} startups from this query")
                print(f"Total unique startups so far: {len(all_startup_info)}")

                # Save intermediate results after each query
                if all_startup_info:
                    save_intermediate_results(all_startup_info, base_filename, "discovery", i+1)

        phase1_time = time.time() - start_time

    print(f"\nPhase 1 completed in {phase1_time:.2f} seconds")
    print(f"Found {len(all_startup_info)} unique startups across all queries")

    if not all_startup_info:
        print("\nNo startups found. Exiting.")
        return False

    # Initialize enriched results
    enriched_results = []

    # If resuming from validation phase, skip enrichment
    if resume_data and start_phase == "validation":
        enriched_results = resume_data
        print(f"Resuming with {len(enriched_results)} enriched startups from checkpoint")
        phase2_time = 0  # Skip phase 2 timing
    else:
        # Phase 2: Enrich startup data
        print("\n" + "=" * 80)
        print("PHASE 2: DATA ENRICHMENT")
        print("=" * 80)
        print(f"Enriching data for {len(all_startup_info)} startups")
        print("This may take a few minutes...")

        start_time = time.time()

        # Save pre-enrichment data
        save_intermediate_results(all_startup_info, base_filename, "pre_enrichment")

        # Use our custom enrichment function for direct startups
        if direct_startups:
            # Batch process startups and save intermediate results after each batch
            batch_size = max(1, min(10, len(all_startup_info) // 5))  # Process in batches of ~20% of total
            enriched_results = []

            for i in range(0, len(all_startup_info), batch_size):
                batch = all_startup_info[i:i+batch_size]
                print(f"\nEnriching batch {i//batch_size + 1}/{(len(all_startup_info) + batch_size - 1) // batch_size}: {len(batch)} startups")

                batch_enriched = batch_enrich_startups(crawler, batch, metrics_collector=metrics_collector)
                enriched_results.extend(batch_enriched)

                # Save intermediate results after each batch
                save_intermediate_results(enriched_results, base_filename, "enrichment", i//batch_size + 1)
        else:
            # Use the crawler's built-in enrichment for discovered startups
            # Batch process startups and save intermediate results after each batch
            batch_size = max(1, min(10, len(all_startup_info) // 5))  # Process in batches of ~20% of total
            enriched_results = []

            for i in range(0, len(all_startup_info), batch_size):
                batch = all_startup_info[i:i+batch_size]
                print(f"\nEnriching batch {i//batch_size + 1}/{(len(all_startup_info) + batch_size - 1) // batch_size}: {len(batch)} startups")

                batch_enriched = crawler.enrich_startup_data(batch, metrics_collector=metrics_collector)
                enriched_results.extend(batch_enriched)

                # Save intermediate results after each batch
                save_intermediate_results(enriched_results, base_filename, "enrichment", i//batch_size + 1)

        phase2_time = time.time() - start_time

    print(f"\nPhase 2 completed in {phase2_time:.2f} seconds")

    # Phase 3: Validate and correct data with Gemini 2.0 Flash using search grounding
    print("\n" + "=" * 80)
    print("PHASE 3: DATA VALIDATION WITH SEARCH GROUNDING")
    print("=" * 80)
    print("Using Gemini 2.0 Flash with search grounding to validate and correct startup data")
    print("This allows the AI to access real-time information from the web for more accurate results")
    print("The model is explicitly configured with web search capabilities for enhanced validation")

    start_time = time.time()

    # Batch process validation to save intermediate results
    batch_size = max(1, min(10, len(enriched_results) // 5))  # Process in batches of ~20% of total
    validated_results = []

    for i in range(0, len(enriched_results), batch_size):
        batch = enriched_results[i:i+batch_size]
        print(f"\nValidating batch {i//batch_size + 1}/{(len(enriched_results) + batch_size - 1) // batch_size}: {len(batch)} startups")

        batch_validated = validate_and_correct_data_with_gemini(batch, query)
        validated_results.extend(batch_validated)

        # Save intermediate results after each batch
        save_intermediate_results(validated_results, base_filename, "validation", i//batch_size + 1)

    phase3_time = time.time() - start_time

    print(f"\nPhase 3 completed in {phase3_time:.2f} seconds")
    print(f"Validated {len(validated_results)} startups using search grounding")

    # Save final validated results
    save_intermediate_results(validated_results, base_filename, "final_validation")

    # Generate CSV file
    print("\n" + "=" * 80)
    print("GENERATING CSV FILE")
    print("=" * 80)

    success = generate_csv_from_startups(
        validated_results,
        validated_output_file,
        create_dir=True
    )

    if success:
        # Generate consolidated metrics reports
        from src.utils.report_generator import export_consolidated_reports

        # Generate timestamp for report filenames
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        base_filename = f"startup_finder_{timestamp}"

        # Export consolidated reports
        report_files = export_consolidated_reports(metrics_collector, base_filename)

        # Summary
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Original search query: {query}")
        print(f"Number of expanded queries: {len(expanded_queries)}")
        print(f"Phase 1 (Discovery) time: {phase1_time:.2f} seconds")
        print(f"Phase 2 (Enrichment) time: {phase2_time:.2f} seconds")
        print(f"Phase 3 (Validation with Search Grounding) time: {phase3_time:.2f} seconds")
        print(f"Total time: {phase1_time + phase2_time + phase3_time:.2f} seconds")
        print(f"Startups found: {len(all_startup_info)}")
        print(f"Startups validated: {len(validated_results)}")
        print(f"CSV files generated:")
        print(f"- Main startup data: {validated_output_file}")
        print(f"- Consolidated metrics report: {report_files['metrics']}")
        print(f"- Consolidated startup data: {report_files['startups']}")
        print("\nSearch grounding was used to access real-time information from the web")
        print("This enhances the accuracy and completeness of the startup data")
    else:
        print("\nFailed to generate CSV file.")

    print("\n" + "=" * 80)
    print("PROCESS COMPLETE")
    print("=" * 80)

    return success


def run_startup_finder(mode="both", query=None, max_results=10, num_expansions=10,
                      input_file=None, output_file=None, use_query_expansion=True,
                      direct_startups=None, resume_file=None, resume_phase=None, resume_latest=False,
                      batch_size=500):
    """
    Run the startup finder in the specified mode.

    Args:
        mode: Operation mode - "find", "enrich", or "both"
        query: Search query to find startups (for "find" and "both" modes)
        max_results: Maximum number of search results per query (for "find" and "both" modes)
        num_expansions: Number of query expansions (for "find" and "both" modes)
        input_file: Path to input CSV file with startup names (for "enrich" mode)
        output_file: Path to the output CSV file
        use_query_expansion: Whether to use query expansion (for "find" and "both" modes)
        direct_startups: List of startup names to directly search for (for "both" mode)
        resume_file: Path to a specific intermediate results file to resume from
        resume_phase: Phase to resume from (discovery, enrichment, validation)
        resume_latest: Whether to resume from the latest available checkpoint
        batch_size: Number of URLs to process in each batch (default: 500)

    Returns:
        bool: True if successful, False otherwise.
    """
    print("\n" + "=" * 80)
    print("STARTUP FINDER")
    print("=" * 80)

    # Load environment variables from .env file
    load_env_from_file()

    # Ensure environment is set up
    setup_env.setup_environment(test_apis=False)

    # Create a metrics collector
    from src.utils.metrics_collector import MetricsCollector
    metrics_collector = MetricsCollector()

    # Handle resume options
    resume_data = None
    if resume_file:
        print(f"Resuming from specific checkpoint: {resume_file}")
        resume_data = load_intermediate_results(resume_file)
    elif resume_phase:
        latest_file = find_latest_intermediate_file(resume_phase)
        if latest_file:
            print(f"Resuming from latest {resume_phase} checkpoint: {latest_file}")
            resume_data = load_intermediate_results(latest_file)
        else:
            print(f"No checkpoint found for phase: {resume_phase}")
    elif resume_latest:
        latest_file = find_latest_intermediate_file()
        if latest_file:
            print(f"Resuming from latest checkpoint: {latest_file}")
            resume_data = load_intermediate_results(latest_file)
        else:
            print("No checkpoint found")

    # Determine which phase to start from based on the checkpoint
    start_phase = "discovery"
    if resume_data:
        # Check if the data has enrichment fields
        has_enrichment = any("Description" in startup or "Founded" in startup for startup in resume_data)

        if has_enrichment:
            start_phase = "validation"
            print("Resuming from validation phase")
        else:
            start_phase = "enrichment"
            print("Resuming from enrichment phase")

    # Run the appropriate function based on the mode
    if mode == "find":
        if not query:
            print("Error: Query is required for 'find' mode")
            return False

        print(f"Mode: Find startups only")
        result = find_startups(query, max_results, num_expansions, output_file, use_query_expansion, metrics_collector, batch_size)
        return result is not None

    elif mode == "enrich":
        if not input_file and not resume_data:
            print("Error: Input file is required for 'enrich' mode")
            return False

        print(f"Mode: Enrich existing startup data only")

        # Use resume data if available, otherwise use input file
        if resume_data:
            result = enrich_startups_from_data(resume_data, output_file, metrics_collector)
        else:
            result = enrich_startups(input_file, output_file, metrics_collector)

        return result is not None

    else:  # mode == "both"
        if not query and not direct_startups and not resume_data:
            print("Error: Either query, direct startups, or resume data are required for 'both' mode")
            return False

        print(f"Mode: Find and enrich startups")

        # If resuming, pass the resume data and start phase
        if resume_data:
            return find_and_enrich_startups(query, max_results, num_expansions, output_file,
                                          use_query_expansion, direct_startups, metrics_collector,
                                          resume_data=resume_data, start_phase=start_phase)
        else:
            return find_and_enrich_startups(query, max_results, num_expansions, output_file,
                                          use_query_expansion, direct_startups, metrics_collector)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Startup Finder - Find and gather information about startups")

    parser.add_argument("--mode", type=str, choices=["find", "enrich", "both"], default="both",
                        help="Operation mode: find startups, enrich existing data, or both (default: both)")
    parser.add_argument("--query", "-q", type=str,
                        help="Search query to find startups (required for 'find' and 'both' modes)")
    parser.add_argument("--max-results", "-m", type=int, default=10,
                        help="Maximum number of search results per query (default: 10)")
    parser.add_argument("--num-expansions", "-n", type=int, default=10,
                        help="Number of query expansions to generate (1-100, default: 10)")
    parser.add_argument("--input-file", "-i", type=str,
                        help="Path to input CSV file with startup names (required for 'enrich' mode)")
    parser.add_argument("--output-file", "-o", type=str,
                        help="Path to the output CSV file (default: output/data/startups_TIMESTAMP.csv)")
    parser.add_argument("--no-expansion", action="store_true",
                        help="Disable query expansion")
    parser.add_argument("--startups", "-s", type=str, nargs="+",
                        help="List of startup names to directly search for (for 'both' mode)")
    parser.add_argument("--startups-file", "-f", type=str,
                        help="Path to a file containing startup names, one per line (for 'both' mode)")
    parser.add_argument("--max-workers", "-w", type=int, default=30,
                        help="Maximum number of parallel workers for web crawling (default: 30)")
    parser.add_argument("--batch-size", "-b", type=int, default=500,
                        help="Number of URLs to process in each batch (default: 500)")
    parser.add_argument("--resume", "-r", type=str,
                        help="Resume from a specific intermediate results file")
    parser.add_argument("--resume-phase", type=str, choices=["discovery", "enrichment", "validation"],
                        help="Resume from the latest checkpoint of a specific phase")
    parser.add_argument("--resume-latest", action="store_true",
                        help="Resume from the latest available checkpoint")

    return parser.parse_args()


def get_integer_input(prompt, default, min_value, max_value):
    """Get integer input from user with validation."""
    while True:
        try:
            value_str = input(prompt).strip() or str(default)
            value = int(value_str)

            if value < min_value or value > max_value:
                print(f"Value must be between {min_value} and {max_value}. Using default: {default}")
                return default

            return value
        except ValueError:
            print(f"Invalid input. Please enter a number. Using default: {default}")
            return default


def interactive_mode():
    """Run the startup finder in interactive mode."""
    print("\nStartup Finder - Interactive Mode")
    print("\nChoose operation mode:")
    print("1. Find startups based on search queries")
    print("2. Enrich existing startup data")
    print("3. Find and enrich startups (complete process)")
    print("4. Resume from a checkpoint")

    mode_choice = input("\nEnter your choice (1-4): ").strip()

    if mode_choice == "1":
        # Find startups mode
        print("\n--- FIND STARTUPS MODE ---")
        print("This mode will search for startups based on your query and save basic information to a CSV file.")

        # Get search query
        print("\nEnter a search query to find startups. Examples:")
        print("- top ai startups 2024")
        print("- fintech startups in singapore")
        print("- healthcare ai companies")
        print("- cybersecurity startups")
        query = input("\nYour search query: ").strip()
        if not query:
            print("No query provided. Exiting.")
            return False

        # Get other parameters
        max_results = get_integer_input("\nMaximum number of search results to process (1-50, default: 20): ", 20, 1, 50)
        use_query_expansion = input("\nUse query expansion to improve results? (y/n, default: y): ").strip().lower() != 'n'
        num_expansions = 10
        if use_query_expansion:
            num_expansions = get_integer_input("\nNumber of query expansions (1-100, default: 10): ", 10, 1, 100)

        # Get batch size
        batch_size = get_integer_input("\nNumber of URLs to process in each batch (100-1000, default: 500): ", 500, 100, 1000)

        # Get output file
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        default_filename = f"output/data/startups_find_{timestamp}.csv"
        output_file = input(f"\nOutput CSV file name (default: {default_filename}): ").strip() or default_filename

        # Run the finder
        return run_startup_finder(
            mode="find",
            query=query,
            max_results=max_results,
            num_expansions=num_expansions,
            output_file=output_file,
            use_query_expansion=use_query_expansion,
            batch_size=batch_size
        )

    elif mode_choice == "2":
        # Enrich startups mode
        print("\n--- ENRICH STARTUPS MODE ---")
        print("This mode will enrich existing startup data from a CSV file.")
        print("The input CSV should have a column named 'Name' or 'Company Name' with startup names.")

        # Get input file
        input_file = input("\nPath to input CSV file with startup names: ").strip()
        if not input_file:
            print("No input file provided. Exiting.")
            return False

        # Get batch size
        batch_size = get_integer_input("\nNumber of startups to process in each batch (10-100, default: 50): ", 50, 10, 100)

        # Get output file
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        default_filename = f"output/data/startups_enriched_{timestamp}.csv"
        output_file = input(f"\nOutput CSV file name (default: {default_filename}): ").strip() or default_filename

        # Run the enricher
        return run_startup_finder(
            mode="enrich",
            input_file=input_file,
            output_file=output_file,
            batch_size=batch_size
        )

    elif mode_choice == "4":
        # Resume mode
        print("\n--- RESUME FROM CHECKPOINT MODE ---")
        print("This mode will resume processing from a previous checkpoint.")

        print("\nChoose resume option:")
        print("1. Resume from a specific checkpoint file")
        print("2. Resume from the latest checkpoint of a specific phase")
        print("3. Resume from the latest available checkpoint")

        resume_choice = input("\nEnter your choice (1-3): ").strip()

        resume_file = None
        resume_phase = None
        resume_latest = False

        if resume_choice == "1":
            # Resume from specific file
            resume_file = input("\nEnter the path to the checkpoint file: ").strip()
            if not resume_file:
                print("No checkpoint file provided. Exiting.")
                return False

        elif resume_choice == "2":
            # Resume from latest checkpoint of a specific phase
            print("\nChoose phase to resume from:")
            print("1. Discovery phase")
            print("2. Enrichment phase")
            print("3. Validation phase")

            phase_choice = input("\nEnter your choice (1-3): ").strip()

            if phase_choice == "1":
                resume_phase = "discovery"
            elif phase_choice == "2":
                resume_phase = "enrichment"
            elif phase_choice == "3":
                resume_phase = "validation"
            else:
                print("Invalid choice. Using enrichment phase.")
                resume_phase = "enrichment"

        else:  # Default to option 3
            # Resume from latest checkpoint
            resume_latest = True

        # Get batch size
        batch_size = get_integer_input("\nNumber of items to process in each batch (100-1000, default: 500): ", 500, 100, 1000)

        # Get output file
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        default_filename = f"output/data/startups_resumed_{timestamp}.csv"
        output_file = input(f"\nOutput CSV file name (default: {default_filename}): ").strip() or default_filename

        # Run the finder with resume options
        return run_startup_finder(
            mode="both",  # Default to both mode for resume
            query="startup companies",  # Use a generic query
            output_file=output_file,
            resume_file=resume_file,
            resume_phase=resume_phase,
            resume_latest=resume_latest,
            batch_size=batch_size
        )

    else:  # Default to option 3 (both)
        # Find and enrich mode
        print("\n--- FIND AND ENRICH STARTUPS MODE ---")
        print("This mode will search for startups and then enrich the data with detailed information.")

        print("\nChoose how to find startups:")
        print("1. Search for startups using a query")
        print("2. Directly input startup names")
        print("3. Load startup names from a file")

        find_choice = input("\nEnter your choice (1-3): ").strip()

        direct_startups = None
        query = None

        if find_choice == "2":
            # Get startup names directly from user
            print("\nEnter startup names, one per line. Enter an empty line when done.")
            startups = []
            while True:
                startup = input("Startup name: ").strip()
                if not startup:
                    break
                startups.append(startup)

            if not startups:
                print("No startup names provided. Exiting.")
                return False

            direct_startups = startups
            query = "startup companies"  # Generic query

        elif find_choice == "3":
            # Get startup names from a file
            file_path = input("\nEnter the path to the file containing startup names: ").strip()
            if not file_path:
                print("No file path provided. Exiting.")
                return False

            try:
                with open(file_path, 'r') as f:
                    startups = [line.strip() for line in f if line.strip()]

                if not startups:
                    print("No startup names found in the file. Exiting.")
                    return False

                print(f"Loaded {len(startups)} startup names from {file_path}")
                direct_startups = startups
                query = "startup companies"  # Generic query

            except Exception as e:
                print(f"Error loading startups file: {e}")
                return False

        else:  # Default to option 1
            # Get search query from user
            print("\nEnter a search query to find startups. Examples:")
            print("- top ai startups 2024")
            print("- fintech startups in singapore")
            print("- healthcare ai companies")
            print("- cybersecurity startups")
            query = input("\nYour search query: ").strip()

            if not query:
                print("No query provided. Exiting.")
                return False

        # Get parameters for query-based search
        max_results = 10  # Reduced from 20 to improve performance
        num_expansions = 5  # Reduced from 10 to improve performance
        use_query_expansion = True

        if find_choice == "1":
            max_results = get_integer_input("\nMaximum number of search results to process (1-50, default: 10): ", 10, 1, 50)
            use_query_expansion = input("\nUse query expansion to improve results? (y/n, default: y): ").strip().lower() != 'n'
            if use_query_expansion:
                num_expansions = get_integer_input("\nNumber of query expansions (1-20, default: 5): ", 5, 1, 20)

        # Get batch size
        batch_size = get_integer_input("\nNumber of items to process in each batch (100-1000, default: 500): ", 500, 100, 1000)

        # Get output file
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        default_filename = f"output/data/startups_{timestamp}.csv"
        output_file = input(f"\nOutput CSV file name (default: {default_filename}): ").strip() or default_filename

        # Run the finder and enricher
        return run_startup_finder(
            mode="both",
            query=query,
            max_results=max_results,
            num_expansions=num_expansions,
            output_file=output_file,
            use_query_expansion=use_query_expansion,
            direct_startups=direct_startups,
            batch_size=batch_size
        )


if __name__ == "__main__":
    # Parse command line arguments
    args = parse_arguments()

    # Get direct startups if provided
    direct_startups = None
    if args.startups:
        direct_startups = args.startups
    elif args.startups_file and args.mode != "enrich":
        try:
            with open(args.startups_file, 'r') as f:
                direct_startups = [line.strip() for line in f if line.strip()]
            print(f"Loaded {len(direct_startups)} startup names from {args.startups_file}")
        except Exception as e:
            print(f"Error loading startups file: {e}")

    # Check if we have the required arguments for the selected mode
    if args.resume or args.resume_phase or args.resume_latest:
        # Run in resume mode
        run_startup_finder(
            mode=args.mode,
            query=args.query or "startup companies",  # Use a generic query if none provided
            max_results=args.max_results,
            num_expansions=args.num_expansions,
            input_file=args.input_file,
            output_file=args.output_file,
            use_query_expansion=not args.no_expansion,
            direct_startups=direct_startups,
            resume_file=args.resume,
            resume_phase=args.resume_phase,
            resume_latest=args.resume_latest,
            batch_size=args.batch_size
        )
    elif args.mode == "find" and args.query:
        # Run in find mode
        run_startup_finder(
            mode="find",
            query=args.query,
            max_results=args.max_results,
            num_expansions=args.num_expansions,
            output_file=args.output_file,
            use_query_expansion=not args.no_expansion,
            batch_size=args.batch_size
        )
    elif args.mode == "enrich" and args.input_file:
        # Run in enrich mode
        run_startup_finder(
            mode="enrich",
            input_file=args.input_file,
            output_file=args.output_file,
            batch_size=args.batch_size
        )
    elif args.mode == "both" and (args.query or direct_startups):
        # Run in both mode
        query = args.query or "startup companies"  # Generic query if only direct startups provided
        run_startup_finder(
            mode="both",
            query=query,
            max_results=args.max_results,
            num_expansions=args.num_expansions,
            output_file=args.output_file,
            use_query_expansion=not args.no_expansion,
            direct_startups=direct_startups,
            batch_size=args.batch_size
        )
    # Otherwise, run in interactive mode
    else:
        interactive_mode()
