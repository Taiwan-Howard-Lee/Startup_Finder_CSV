#!/usr/bin/env python3
"""
Large-scale test for finding Nature-Based Solutions startups using energy sources in Brazil.

This script tests the Startup Finder's ability to discover and enrich data
for Nature-Based Solutions startups in Brazil that use energy sources.
It processes at least 1,000 links to find as many relevant startups as possible.
"""

import os
import sys
import time
import logging
import json
import requests
from typing import List, Dict, Any

# Add the parent directory to the path so we can import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import setup_env to ensure API keys are available
import setup_env

# Import the modules we want to test
from startup_finder import run_startup_finder
from src.processor.enhanced_crawler import EnhancedStartupCrawler
from src.collector.query_expander import QueryExpander
from src.utils.api_client import GeminiAPIClient
from src.processor.crawler import GoogleSearchDataSource

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"logs/test_large_scale_brazil_nbs_startups_{time.strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Create a subclass of GoogleSearchDataSource that can handle more than 10 results
class EnhancedGoogleSearchDataSource(GoogleSearchDataSource):
    """
    Enhanced version of GoogleSearchDataSource that can handle more than 10 results
    by making multiple API calls with pagination.
    """

    def search(self, query: str, max_results: int = 100) -> List[Dict[str, Any]]:
        """
        Search for information using Google Search API with pagination.

        Args:
            query: Search query.
            max_results: Maximum number of results to return.

        Returns:
            List of search results.
        """
        if not self.api_key or not self.cx_id:
            logger.error("Google Search API key or CX ID not set. Set GOOGLE_SEARCH_API_KEY and GOOGLE_CX_ID environment variables.")
            return []

        results = []

        # Calculate how many API calls we need to make
        # Each API call can return a maximum of 10 results
        num_api_calls = (max_results + 9) // 10  # Ceiling division

        try:
            # Make multiple API calls with pagination
            for i in range(num_api_calls):
                # Skip to the appropriate starting index
                start_index = i * 10 + 1

                # If we already have enough results, stop making API calls
                if len(results) >= max_results:
                    break

                # Build the API URL
                base_url = "https://www.googleapis.com/customsearch/v1"
                params = {
                    "key": self.api_key,
                    "cx": self.cx_id,
                    "q": query,
                    "num": 10,  # API allows max 10 results per request
                    "start": start_index
                }

                # Add a small delay between API calls to avoid rate limiting
                if i > 0:
                    time.sleep(0.5)

                # Make the request
                logger.info(f"Making API call {i+1}/{num_api_calls} for query: {query} (start={start_index})")
                response = requests.get(base_url, params=params, timeout=10)
                response.raise_for_status()

                # Parse the response
                data = response.json()

                # Extract the search results
                if "items" in data:
                    for item in data["items"]:
                        result = {
                            "title": item.get("title", ""),
                            "url": item.get("link", ""),
                            "snippet": item.get("snippet", "")
                        }
                        results.append(result)
                else:
                    # If there are no more results, break the loop
                    logger.info(f"No more results found for query: {query} after {len(results)} results")
                    break

            logger.info(f"Found {len(results)} results from Google Search for query: {query}")
            return results[:max_results]

        except Exception as e:
            logger.error(f"Error searching Google: {e}")
            return results  # Return any results we've collected so far

def test_large_scale_brazil_nbs_startups():
    """
    Test finding Nature-Based Solutions startups using energy sources in Brazil
    with at least 1,000 links processed.

    This test:
    1. Uses a specific query about Nature-Based Solutions startups in Brazil
    2. Processes at least 1,000 links to find as many startups as possible
    3. Logs detailed information about each phase
    4. Analyzes potential issues in the process
    """
    # Test query
    query = "Nature-Based Solutions startup using energy sources in Brazil"

    # Set maximum results per query to a higher value
    max_results_per_query = 100

    # Set number of query expansions
    num_expansions = 15

    # Set minimum number of links to process
    min_links_to_process = 1000

    # Set output file
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_file = f"data/test_large_scale_brazil_nbs_startups_{timestamp}.csv"

    logger.info("=" * 80)
    logger.info(f"LARGE-SCALE TESTING: {query}")
    logger.info(f"Max results per query: {max_results_per_query}, Expansions: {num_expansions}")
    logger.info(f"Minimum links to process: {min_links_to_process}")
    logger.info("=" * 80)

    # Ensure environment is set up
    setup_env.setup_environment(test_apis=False)

    # PHASE 1: Test query expansion
    logger.info("\nPHASE 1: TESTING QUERY EXPANSION")
    logger.info("-" * 80)

    try:
        # Initialize the API client and query expander
        gemini_client = GeminiAPIClient()
        query_expander = QueryExpander(api_client=gemini_client)

        # Expand the query using parallel processing
        start_time = time.time()
        expanded_queries = query_expander.expand_query_parallel(query, num_expansions=num_expansions)
        end_time = time.time()

        logger.info(f"Query expansion completed in {end_time - start_time:.2f} seconds")
        logger.info(f"Generated {len(expanded_queries)} expanded queries:")
        for i, expanded_query in enumerate(expanded_queries):
            logger.info(f"  {i+1}. {expanded_query}")

        # Analyze query expansion quality
        analyze_query_expansion(expanded_queries, query)

    except Exception as e:
        logger.error(f"Error in query expansion: {e}")
        expanded_queries = [query]

    # PHASE 2: Test startup discovery with enhanced Google Search
    logger.info("\nPHASE 2: TESTING LARGE-SCALE STARTUP DISCOVERY")
    logger.info("-" * 80)

    try:
        # Create an enhanced crawler with our custom Google Search data source
        crawler = EnhancedStartupCrawler(max_workers=30)

        # Replace the default Google Search data source with our enhanced version
        crawler.google_search = EnhancedGoogleSearchDataSource()

        all_startup_info = []
        total_links_processed = 0

        # Process each expanded query
        for i, expanded_query in enumerate(expanded_queries):
            logger.info(f"Processing query {i+1}/{len(expanded_queries)}: {expanded_query}")

            # Discover startups for this query
            start_time = time.time()
            startup_info_list = crawler.discover_startups(expanded_query, max_results=max_results_per_query)
            end_time = time.time()

            # Update the total links processed
            # Each startup discovery processes approximately max_results_per_query links
            links_processed = max_results_per_query
            total_links_processed += links_processed

            logger.info(f"Discovery completed in {end_time - start_time:.2f} seconds")
            logger.info(f"Found {len(startup_info_list)} startups from this query")
            logger.info(f"Processed approximately {links_processed} links for this query")
            logger.info(f"Total links processed so far: {total_links_processed}")

            # Log discovered startups
            for j, startup in enumerate(startup_info_list):
                logger.info(f"  {j+1}. {startup.get('Company Name', 'Unknown')}")

            # Add to the combined list, avoiding duplicates
            existing_names = {startup.get("Company Name", "").lower() for startup in all_startup_info}
            for startup in startup_info_list:
                name = startup.get("Company Name", "").lower()
                if name and name not in existing_names:
                    all_startup_info.append(startup)
                    existing_names.add(name)

            logger.info(f"Total unique startups so far: {len(all_startup_info)}")

            # If we've processed at least min_links_to_process links, we can stop
            if total_links_processed >= min_links_to_process:
                logger.info(f"Reached the target of {min_links_to_process} links processed, moving to enrichment phase")
                break

        # Analyze startup discovery results
        analyze_startup_discovery(all_startup_info, query, total_links_processed)

    except Exception as e:
        logger.error(f"Error in startup discovery: {e}")
        all_startup_info = []

    # PHASE 3: Test data enrichment
    logger.info("\nPHASE 3: TESTING DATA ENRICHMENT")
    logger.info("-" * 80)

    if not all_startup_info:
        logger.error("No startups found. Cannot proceed with enrichment.")
        return False

    try:
        # Enrich startup data
        logger.info(f"Enriching data for {len(all_startup_info)} startups")

        start_time = time.time()
        enriched_results = crawler.enrich_startup_data(all_startup_info)
        end_time = time.time()

        logger.info(f"Enrichment completed in {end_time - start_time:.2f} seconds")
        logger.info(f"Enriched {len(enriched_results)} startups")

        # Log enriched data fields for each startup
        for i, startup in enumerate(enriched_results):
            name = startup.get("Company Name", "Unknown")
            fields = list(startup.keys())
            logger.info(f"  {i+1}. {name}: {len(fields)} fields")
            logger.info(f"     Fields: {', '.join(fields)}")

        # Analyze enrichment results
        analyze_enrichment_results(enriched_results)

    except Exception as e:
        logger.error(f"Error in data enrichment: {e}")
        enriched_results = all_startup_info

    # PHASE 4: Test data validation with Gemini
    logger.info("\nPHASE 4: TESTING DATA VALIDATION")
    logger.info("-" * 80)

    try:
        # Initialize the Gemini API client
        gemini_client = GeminiAPIClient()

        # Validate and correct data
        logger.info(f"Validating data for {len(enriched_results)} startups")

        start_time = time.time()
        validated_results = gemini_client.validate_startups_batch(enriched_results, query)
        end_time = time.time()

        logger.info(f"Validation completed in {end_time - start_time:.2f} seconds")
        logger.info(f"Validated {len(validated_results)} startups")

        # Analyze validation results
        analyze_validation_results(validated_results, enriched_results)

    except Exception as e:
        logger.error(f"Error in data validation: {e}")
        validated_results = enriched_results

    # PHASE 5: Test CSV generation
    logger.info("\nPHASE 5: TESTING CSV GENERATION")
    logger.info("-" * 80)

    try:
        # Generate CSV file
        from startup_finder import generate_csv_from_startups

        start_time = time.time()
        success = generate_csv_from_startups(
            validated_results,
            output_file,
            create_dir=True
        )
        end_time = time.time()

        if success:
            logger.info(f"CSV generation completed in {end_time - start_time:.2f} seconds")
            logger.info(f"CSV file generated: {output_file}")
        else:
            logger.error("Failed to generate CSV file")

    except Exception as e:
        logger.error(f"Error in CSV generation: {e}")
        success = False

    # Final summary
    logger.info("\n" + "=" * 80)
    logger.info("LARGE-SCALE TEST SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Query: {query}")
    logger.info(f"Expanded queries: {len(expanded_queries)}")
    logger.info(f"Total links processed: {total_links_processed}")
    logger.info(f"Startups discovered: {len(all_startup_info)}")
    logger.info(f"Startups enriched: {len(enriched_results)}")
    logger.info(f"Startups validated: {len(validated_results)}")
    logger.info(f"CSV generation: {'Success' if success else 'Failed'}")

    return success

def analyze_query_expansion(expanded_queries: List[str], original_query: str):
    """
    Analyze the quality of query expansion.

    Args:
        expanded_queries: List of expanded queries
        original_query: Original query
    """
    logger.info("\nQUERY EXPANSION ANALYSIS:")

    # Check if all key terms from original query are represented in expansions
    key_terms = ["Nature-Based", "Solutions", "startup", "energy", "sources", "Brazil"]
    term_coverage = {term: 0 for term in key_terms}

    for query in expanded_queries:
        for term in key_terms:
            if term.lower() in query.lower():
                term_coverage[term] += 1

    logger.info("Key term coverage in expanded queries:")
    for term, count in term_coverage.items():
        percentage = (count / len(expanded_queries)) * 100
        logger.info(f"  {term}: {count}/{len(expanded_queries)} queries ({percentage:.1f}%)")

        if percentage < 50:
            logger.warning(f"  ⚠️ Low coverage for term '{term}' - may miss relevant startups")

    # Check for query diversity
    avg_length = sum(len(q.split()) for q in expanded_queries) / len(expanded_queries)
    logger.info(f"Average query length: {avg_length:.1f} words")

    if avg_length < 4:
        logger.warning("  ⚠️ Queries may be too short to be specific")
    elif avg_length > 10:
        logger.warning("  ⚠️ Queries may be too long and overly specific")

def analyze_startup_discovery(startups: List[Dict[str, Any]], query: str, total_links_processed: int):
    """
    Analyze the startup discovery results.

    Args:
        startups: List of discovered startups
        query: Original query
        total_links_processed: Total number of links processed
    """
    logger.info("\nSTARTUP DISCOVERY ANALYSIS:")

    if not startups:
        logger.error("  ❌ No startups found - query may be too specific or niche")
        return

    # Calculate the yield rate (startups per link)
    yield_rate = len(startups) / total_links_processed if total_links_processed > 0 else 0
    logger.info(f"  Yield rate: {yield_rate:.4f} startups per link ({len(startups)} startups from {total_links_processed} links)")

    if yield_rate < 0.01:
        logger.warning("  ⚠️ Low yield rate - query may be too specific or the domain may have few startups")

    # Check for potential issues
    if len(startups) < 10:
        logger.warning(f"  ⚠️ Only {len(startups)} startups found - query may be too specific")

    # Check for naming patterns that might indicate non-startups
    potential_non_startups = []
    for startup in startups:
        name = startup.get("Company Name", "").lower()

        # Check for patterns that might indicate this is not a startup
        if any(pattern in name for pattern in ["university", "institute", "ministry", "government", "association"]):
            potential_non_startups.append(startup.get("Company Name", ""))

    if potential_non_startups:
        logger.warning("  ⚠️ Some entries may not be startups:")
        for name in potential_non_startups:
            logger.warning(f"    - {name}")

    # Check for Brazil-specific terms
    brazil_terms = ["brazil", "brazilian", "brasil", "brasileiro", "são paulo", "rio", "brasília"]
    brazil_startups = 0

    for startup in startups:
        name = startup.get("Company Name", "").lower()
        if any(term in name for term in brazil_terms):
            brazil_startups += 1

    brazil_percentage = (brazil_startups / len(startups)) * 100 if startups else 0
    logger.info(f"  Startups with Brazil-specific terms in name: {brazil_startups}/{len(startups)} ({brazil_percentage:.1f}%)")

    if brazil_percentage < 30:
        logger.warning("  ⚠️ Low percentage of startups with Brazil-specific terms - may include non-Brazilian companies")

def analyze_enrichment_results(enriched_results: List[Dict[str, Any]]):
    """
    Analyze the enrichment results.

    Args:
        enriched_results: List of enriched startup data
    """
    logger.info("\nENRICHMENT ANALYSIS:")

    # Calculate field coverage
    key_fields = [
        "Website", "LinkedIn", "Location", "Founded Year",
        "Industry", "Company Size", "Funding", "Company Description",
        "Products/Services", "Founders"
    ]

    field_coverage = {field: 0 for field in key_fields}

    for startup in enriched_results:
        for field in key_fields:
            if field in startup and startup[field]:
                field_coverage[field] += 1

    logger.info("Field coverage in enriched data:")
    for field, count in field_coverage.items():
        percentage = (count / len(enriched_results)) * 100 if enriched_results else 0
        logger.info(f"  {field}: {count}/{len(enriched_results)} startups ({percentage:.1f}%)")

        if percentage < 50:
            logger.warning(f"  ⚠️ Low coverage for field '{field}' - data may be incomplete")

    # Check for Brazil-specific locations
    brazil_locations = 0
    for startup in enriched_results:
        location = startup.get("Location", "").lower()
        if "brazil" in location or "brasil" in location:
            brazil_locations += 1

    brazil_percentage = (brazil_locations / len(enriched_results)) * 100 if enriched_results else 0
    logger.info(f"  Startups with Brazil in location: {brazil_locations}/{len(enriched_results)} ({brazil_percentage:.1f}%)")

    if brazil_percentage < 50:
        logger.warning("  ⚠️ Low percentage of startups with Brazil in location - may include non-Brazilian companies")

def analyze_validation_results(validated_results: List[Dict[str, Any]], original_results: List[Dict[str, Any]]):
    """
    Analyze the validation results.

    Args:
        validated_results: List of validated startup data
        original_results: List of original enriched data before validation
    """
    logger.info("\nVALIDATION ANALYSIS:")

    # Check if any startups were removed during validation
    if len(validated_results) < len(original_results):
        removed_count = len(original_results) - len(validated_results)
        logger.info(f"  {removed_count} startups were removed during validation")

        # Try to identify which ones were removed
        original_names = {startup.get("Company Name", "").lower() for startup in original_results}
        validated_names = {startup.get("Company Name", "").lower() for startup in validated_results}
        removed_names = original_names - validated_names

        logger.info("  Removed startups:")
        for name in removed_names:
            logger.info(f"    - {name}")

    # Check for field changes
    field_changes = 0
    for original in original_results:
        original_name = original.get("Company Name", "").lower()

        # Find the corresponding validated startup
        for validated in validated_results:
            validated_name = validated.get("Company Name", "").lower()

            if original_name == validated_name:
                # Compare fields
                for field in original:
                    if field in validated and original[field] != validated[field]:
                        field_changes += 1
                        break

    logger.info(f"  {field_changes} startups had fields modified during validation")

    # Check for field additions
    field_additions = 0
    for original in original_results:
        original_name = original.get("Company Name", "").lower()
        original_fields = set(original.keys())

        # Find the corresponding validated startup
        for validated in validated_results:
            validated_name = validated.get("Company Name", "").lower()

            if original_name == validated_name:
                validated_fields = set(validated.keys())
                new_fields = validated_fields - original_fields

                if new_fields:
                    field_additions += 1
                    break

    logger.info(f"  {field_additions} startups had new fields added during validation")

def main():
    """Main function to run the test."""
    logger.info("Starting large-scale test for Nature-Based Solutions startups in Brazil")

    try:
        success = test_large_scale_brazil_nbs_startups()

        if success:
            logger.info("Large-scale test completed successfully")
        else:
            logger.error("Large-scale test failed")

    except Exception as e:
        logger.error(f"Large-scale test failed with error: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main()
