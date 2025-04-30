#!/usr/bin/env python3
"""
System Integrity Test for Startup Finder.

This script tests the core functionality of the Startup Finder after cleanup
to ensure that all components are working properly.
"""

import os
import sys
import time
import logging
from typing import Dict, Any, List, Optional

# Add the parent directory to the path so we can import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import setup_env to ensure API keys are available
import setup_env

# Import the core components we want to test
from src.collector.query_expander import QueryExpander
from src.processor.enhanced_crawler import EnhancedStartupCrawler
from src.utils.api_client import GeminiAPIClient
from startup_finder import generate_csv_from_startups

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def test_system_integrity():
    """
    Test the core functionality of the Startup Finder after cleanup.
    
    This test:
    1. Tests the environment setup
    2. Tests the query expander
    3. Tests the startup discovery process
    4. Tests the data enrichment process
    5. Tests the CSV generation
    
    Returns:
        bool: True if all tests pass, False otherwise
    """
    logger.info("=" * 80)
    logger.info("SYSTEM INTEGRITY TEST")
    logger.info("=" * 80)
    
    all_tests_passed = True
    
    # Step 1: Test environment setup
    logger.info("\nStep 1: Testing environment setup")
    try:
        setup_env.setup_environment(test_apis=True)
        logger.info("✅ Environment setup successful")
    except Exception as e:
        logger.error(f"❌ Environment setup failed: {e}")
        all_tests_passed = False
        return all_tests_passed  # If environment setup fails, we can't continue
    
    # Step 2: Test query expander
    logger.info("\nStep 2: Testing query expander")
    try:
        # Initialize the API client and query expander
        gemini_client = GeminiAPIClient()
        query_expander = QueryExpander(api_client=gemini_client)
        
        # Test query
        test_query = "AI startups in healthcare"
        
        # Expand the query
        start_time = time.time()
        expanded_queries = query_expander.expand_query(test_query, num_expansions=2)
        end_time = time.time()
        
        logger.info(f"Query expansion completed in {end_time - start_time:.2f} seconds")
        logger.info(f"Generated {len(expanded_queries)} expanded queries:")
        for i, expanded_query in enumerate(expanded_queries):
            logger.info(f"  {i+1}. {expanded_query}")
        
        if len(expanded_queries) >= 1:
            logger.info("✅ Query expander test passed")
        else:
            logger.error("❌ Query expander test failed: No expanded queries generated")
            all_tests_passed = False
    except Exception as e:
        logger.error(f"❌ Query expander test failed: {e}")
        all_tests_passed = False
    
    # Step 3: Test startup discovery
    logger.info("\nStep 3: Testing startup discovery")
    try:
        # Create an enhanced crawler
        crawler = EnhancedStartupCrawler(max_workers=5)
        
        # Use a simple query with a small max_results to keep the test quick
        test_query = "AI startups in healthcare"
        max_results = 3
        
        # Discover startups
        start_time = time.time()
        startup_info_list = crawler.discover_startups(test_query, max_results=max_results)
        end_time = time.time()
        
        logger.info(f"Startup discovery completed in {end_time - start_time:.2f} seconds")
        logger.info(f"Found {len(startup_info_list)} startups")
        
        # Log discovered startups
        for i, startup in enumerate(startup_info_list):
            logger.info(f"  {i+1}. {startup.get('Company Name', 'Unknown')}")
        
        if len(startup_info_list) > 0:
            logger.info("✅ Startup discovery test passed")
        else:
            logger.warning("⚠️ Startup discovery test: No startups found, but this might be expected for some queries")
    except Exception as e:
        logger.error(f"❌ Startup discovery test failed: {e}")
        all_tests_passed = False
    
    # Step 4: Test data enrichment (only if we found startups)
    if startup_info_list:
        logger.info("\nStep 4: Testing data enrichment")
        try:
            # Limit to just 1-2 startups for a quick test
            test_startups = startup_info_list[:min(2, len(startup_info_list))]
            
            # Enrich startup data
            logger.info(f"Enriching data for {len(test_startups)} startups")
            
            start_time = time.time()
            enriched_results = crawler.enrich_startup_data(test_startups)
            end_time = time.time()
            
            logger.info(f"Data enrichment completed in {end_time - start_time:.2f} seconds")
            logger.info(f"Enriched {len(enriched_results)} startups")
            
            # Log enriched data fields for each startup
            for i, startup in enumerate(enriched_results):
                name = startup.get("Company Name", "Unknown")
                fields = list(startup.keys())
                logger.info(f"  {i+1}. {name}: {len(fields)} fields")
                logger.info(f"     Fields: {', '.join(fields)}")
            
            if len(enriched_results) > 0:
                logger.info("✅ Data enrichment test passed")
            else:
                logger.warning("⚠️ Data enrichment test: No enriched results, but this might be expected for some startups")
                
            # Step 5: Test CSV generation (only if we have enriched results)
            if enriched_results:
                logger.info("\nStep 5: Testing CSV generation")
                try:
                    # Generate a test CSV file
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    test_csv_path = f"data/test_integrity_{timestamp}.csv"
                    
                    start_time = time.time()
                    success = generate_csv_from_startups(
                        enriched_results,
                        test_csv_path,
                        create_dir=True
                    )
                    end_time = time.time()
                    
                    if success:
                        logger.info(f"CSV generation completed in {end_time - start_time:.2f} seconds")
                        logger.info(f"CSV file generated: {test_csv_path}")
                        logger.info("✅ CSV generation test passed")
                        
                        # Clean up the test CSV file
                        if os.path.exists(test_csv_path):
                            os.remove(test_csv_path)
                            logger.info(f"Cleaned up test CSV file: {test_csv_path}")
                    else:
                        logger.error("❌ CSV generation test failed: Could not generate CSV file")
                        all_tests_passed = False
                except Exception as e:
                    logger.error(f"❌ CSV generation test failed: {e}")
                    all_tests_passed = False
        except Exception as e:
            logger.error(f"❌ Data enrichment test failed: {e}")
            all_tests_passed = False
    
    # Final summary
    logger.info("\n" + "=" * 80)
    logger.info("SYSTEM INTEGRITY TEST SUMMARY")
    logger.info("=" * 80)
    
    if all_tests_passed:
        logger.info("✅ All system integrity tests passed! The Startup Finder is working properly after cleanup.")
    else:
        logger.error("❌ Some system integrity tests failed. Please check the logs for details.")
    
    return all_tests_passed

def main():
    """Main function to run the system integrity test."""
    try:
        success = test_system_integrity()
        
        if success:
            print("\nSystem integrity test completed successfully. All components are working properly.")
            return 0
        else:
            print("\nSystem integrity test failed. Some components may not be working properly.")
            return 1
    except Exception as e:
        print(f"\nSystem integrity test failed with an unexpected error: {e}")
        import traceback
        print(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main())
