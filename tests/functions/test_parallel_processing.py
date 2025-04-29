#!/usr/bin/env python3
"""
Test for parallel processing capacity in the Startup Finder.

This script tests the parallel processing capacity by creating an EnhancedStartupCrawler
with different numbers of workers and measuring the performance.
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

def test_parallel_processing():
    """
    Test the parallel processing capacity of the EnhancedStartupCrawler.
    """
    print("\n" + "=" * 80)
    print("TESTING PARALLEL PROCESSING CAPACITY")
    print("=" * 80)
    
    # Ensure environment variables are loaded
    setup_env.setup_environment()
    
    # Test with different numbers of workers
    worker_counts = [10, 20, 30, 40, 50]
    
    for worker_count in worker_counts:
        print(f"\nTesting with {worker_count} workers...")
        
        # Create a crawler with the specified number of workers
        crawler = EnhancedStartupCrawler(max_workers=worker_count)
        
        # Create a list of startup names to test with
        startup_names = [
            "Carbon Clean",
            "Climeworks",
            "Carbfix",
            "Charm Industrial",
            "Heirloom Carbon",
            "Verdox",
            "Mission Zero Technologies",
            "Twelve",
            "Remora",
            "Captura"
        ]
        
        # Create a list of startup info dictionaries
        startup_info_list = [{"Company Name": name} for name in startup_names]
        
        # Measure the time it takes to enrich the data
        start_time = time.time()
        
        # Only process the first 3 startups to keep the test quick
        results = crawler.enrich_startup_data(startup_info_list[:3], max_results_per_startup=3)
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        print(f"Processed 3 startups with {worker_count} workers in {elapsed_time:.2f} seconds")
        print(f"Average time per startup: {elapsed_time / 3:.2f} seconds")
        
        # Print the number of fields found for each startup
        for result in results:
            company_name = result.get("Company Name", "Unknown")
            field_count = len(result)
            print(f"  {company_name}: {field_count} fields found")
    
    print("\nParallel processing test completed.")

if __name__ == "__main__":
    test_parallel_processing()
