#!/usr/bin/env python3
"""
Test for search query results capacity in the Startup Finder.

This script tests the search query results capacity by using the GoogleSearchClient
with different numbers of results and measuring the performance.
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
from src.utils.google_search_client import GoogleSearchClient

def test_search_query_results():
    """
    Test the search query results capacity of the GoogleSearchClient.
    """
    print("\n" + "=" * 80)
    print("TESTING SEARCH QUERY RESULTS CAPACITY")
    print("=" * 80)
    
    # Ensure environment variables are loaded
    setup_env.setup_environment()
    
    # Create a GoogleSearchClient
    google_search = GoogleSearchClient()
    
    # Test with different numbers of results
    result_counts = [5, 10, 20, 30, 40, 50]
    
    for result_count in result_counts:
        print(f"\nTesting with {result_count} results...")
        
        # Create a search query
        query = "decarbonisation startups in UK"
        
        # Measure the time it takes to search
        start_time = time.time()
        
        # Perform the search
        results = google_search.search(query, num_results=result_count)
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        print(f"Searched for {result_count} results in {elapsed_time:.2f} seconds")
        print(f"Actually found {len(results)} results")
        
        # Print the first few results
        for i, result in enumerate(results[:3]):
            title = result.get("title", "No title")
            url = result.get("url", "No URL")
            print(f"  {i+1}. {title} - {url}")
    
    print("\nSearch query results test completed.")

if __name__ == "__main__":
    test_search_query_results()
