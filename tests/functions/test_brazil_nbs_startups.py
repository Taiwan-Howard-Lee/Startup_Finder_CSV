#!/usr/bin/env python3
"""
Test for finding Nature-Based Solutions startups using energy sources in Brazil.

This script tests the Startup Finder's ability to discover and enrich data
for Nature-Based Solutions startups in Brazil that use energy sources.
It limits the maximum results to 10 startups in stage 1.
"""

import os
import sys
import time
import logging
import json
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

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"logs/test_brazil_nbs_startups_{time.strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def test_brazil_nbs_startups():
    """
    Test finding Nature-Based Solutions startups using energy sources in Brazil.
    
    This test:
    1. Uses a specific query about Nature-Based Solutions startups in Brazil
    2. Limits results to 10 startups in stage 1
    3. Logs detailed information about each phase
    4. Analyzes potential issues in the process
    """
    # Test query
    query = "Nature-Based Solutions startup using energy sources in Brazil"
    
    # Set maximum results to 10 for stage 1
    max_results = 10
    
    # Set number of query expansions
    num_expansions = 5
    
    # Set output file
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_file = f"data/test_brazil_nbs_startups_{timestamp}.csv"
    
    logger.info("=" * 80)
    logger.info(f"TESTING: {query}")
    logger.info(f"Max results: {max_results}, Expansions: {num_expansions}")
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
    
    # PHASE 2: Test startup discovery
    logger.info("\nPHASE 2: TESTING STARTUP DISCOVERY")
    logger.info("-" * 80)
    
    try:
        # Create an enhanced crawler
        crawler = EnhancedStartupCrawler(max_workers=30)
        
        all_startup_info = []
        
        # Process each expanded query
        for i, expanded_query in enumerate(expanded_queries):
            logger.info(f"Processing query {i+1}/{len(expanded_queries)}: {expanded_query}")
            
            # Discover startups for this query
            start_time = time.time()
            startup_info_list = crawler.discover_startups(expanded_query, max_results=max_results)
            end_time = time.time()
            
            logger.info(f"Discovery completed in {end_time - start_time:.2f} seconds")
            logger.info(f"Found {len(startup_info_list)} startups from this query")
            
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
            
            # If we have at least 10 startups, break to move to the next phase
            if len(all_startup_info) >= 10:
                logger.info("Reached the target of 10 startups, moving to enrichment phase")
                break
        
        # Analyze startup discovery results
        analyze_startup_discovery(all_startup_info, query)
        
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
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Query: {query}")
    logger.info(f"Expanded queries: {len(expanded_queries)}")
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

def analyze_startup_discovery(startups: List[Dict[str, Any]], query: str):
    """
    Analyze the startup discovery results.
    
    Args:
        startups: List of discovered startups
        query: Original query
    """
    logger.info("\nSTARTUP DISCOVERY ANALYSIS:")
    
    if not startups:
        logger.error("  ❌ No startups found - query may be too specific or niche")
        return
    
    # Check for potential issues
    if len(startups) < 5:
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
    logger.info("Starting test for Nature-Based Solutions startups in Brazil")
    
    try:
        success = test_brazil_nbs_startups()
        
        if success:
            logger.info("Test completed successfully")
        else:
            logger.error("Test failed")
            
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main()
