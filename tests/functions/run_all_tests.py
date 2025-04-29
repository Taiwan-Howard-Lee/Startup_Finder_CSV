#!/usr/bin/env python3
"""
Run all tests for the Startup Finder.

This script runs all the test functions to verify the improvements made to the Startup Finder.
"""

import os
import sys
import time

# Add the parent directory to the path so we can import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import the test modules
from tests.functions.test_parallel_processing import test_parallel_processing
from tests.functions.test_search_query_results import test_search_query_results
from tests.functions.test_gemini_validation import test_gemini_validation_batch_size
from tests.functions.test_search_grounding import test_search_grounding_capacity
from tests.functions.test_url_processing import test_url_processing

def run_all_tests():
    """
    Run all tests for the Startup Finder.
    """
    print("\n" + "=" * 80)
    print("RUNNING ALL TESTS FOR STARTUP FINDER")
    print("=" * 80)
    
    # Record the start time
    start_time = time.time()
    
    # Run each test
    tests = [
        ("Search Query Results", test_search_query_results),
        ("URL Processing", test_url_processing),
        ("Gemini Validation Batch Size", test_gemini_validation_batch_size),
        ("Search Grounding Capacity", test_search_grounding_capacity),
        ("Parallel Processing", test_parallel_processing)
    ]
    
    for test_name, test_function in tests:
        print(f"\n\nRunning test: {test_name}")
        print("-" * 80)
        
        try:
            test_function()
            print(f"\n✅ {test_name} test completed successfully.")
        except Exception as e:
            print(f"\n❌ {test_name} test failed: {e}")
    
    # Record the end time and calculate the total time
    end_time = time.time()
    total_time = end_time - start_time
    
    print("\n" + "=" * 80)
    print(f"ALL TESTS COMPLETED IN {total_time:.2f} SECONDS")
    print("=" * 80)

if __name__ == "__main__":
    run_all_tests()
