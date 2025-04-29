#!/usr/bin/env python3
"""
Test for URL processing in the Startup Finder.

This script tests the URL processing capacity by using the EnhancedStartupCrawler
to process different numbers of URLs for a single startup.
"""

import time
import os
import sys
from typing import List, Dict, Any

# Add the parent directory to the path so we can import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import setup_env to ensure API keys are available
import setup_env

# Import the modules we want to test
from src.processor.enhanced_crawler import EnhancedStartupCrawler

def test_url_processing():
    """
    Test the URL processing capacity of the EnhancedStartupCrawler.
    """
    print("\n" + "=" * 80)
    print("TESTING URL PROCESSING CAPACITY")
    print("=" * 80)
    
    # Ensure environment variables are loaded
    setup_env.setup_environment()
    
    # Create a crawler
    crawler = EnhancedStartupCrawler(max_workers=30)
    
    # Test with different max_results_per_startup values
    result_counts = [3, 5, 10]
    
    # Create a startup to test with
    startup_info = {"Company Name": "Carbon Clean"}
    
    for result_count in result_counts:
        print(f"\nTesting with max_results_per_startup={result_count}...")
        
        # Measure the time it takes to enrich the data
        start_time = time.time()
        
        # Enrich the startup data
        enriched_data = crawler._enrich_single_startup_enhanced(startup_info, result_count)
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        print(f"Processed startup with max_results_per_startup={result_count} in {elapsed_time:.2f} seconds")
        
        # Print the number of fields found
        field_count = len(enriched_data)
        print(f"  Fields found: {field_count}")
        print(f"  Fields: {', '.join(enriched_data.keys())}")
    
    print("\nURL processing test completed.")

if __name__ == "__main__":
    test_url_processing()
