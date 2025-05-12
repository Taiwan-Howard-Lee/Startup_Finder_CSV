"""
Test the integration of the simplified query expander with the startup discovery process.
"""

import os
import sys
import time
import logging

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import setup_env

from src.collector.query_expander import QueryExpander
from src.processor.enhanced_crawler import EnhancedStartupCrawler
from src.utils.api_client import GeminiAPIClient

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_query_expansion_integration():
    """Test the integration of the simplified query expander with the startup discovery process."""
    print("\n=== Testing Query Expansion Integration ===\n")
    
    # Ensure environment is set up
    setup_env.setup_environment(test_apis=False)
    
    # Create the query expander and crawler
    api_client = GeminiAPIClient()
    query_expander = QueryExpander(api_client=api_client)
    crawler = EnhancedStartupCrawler(max_workers=10)
    
    # Test query
    query = "UK decarbonisation startups"
    num_expansions = 3
    max_results = 3  # Limit results for testing
    
    print(f"Original Query: {query}")
    print(f"Number of expansions: {num_expansions}")
    print(f"Max results per query: {max_results}")
    print("-" * 50)
    
    # Expand the query
    start_time = time.time()
    expanded_queries = query_expander.expand_query(query, num_expansions=num_expansions)
    expansion_time = time.time() - start_time
    
    print(f"Generated {len(expanded_queries)} queries in {expansion_time:.2f} seconds:")
    for i, expanded_query in enumerate(expanded_queries):
        print(f"{i+1}. {expanded_query}")
    
    # Discover startups for each expanded query
    all_startups = []
    startup_names = set()
    
    print("\nDiscovering startups for each expanded query:")
    for i, expanded_query in enumerate(expanded_queries):
        print(f"\nQuery {i+1}: {expanded_query}")
        
        # Discover startups
        start_time = time.time()
        startups = crawler.discover_startups(expanded_query, max_results=max_results)
        discovery_time = time.time() - start_time
        
        # Track unique startups
        new_startups = []
        for startup in startups:
            name = startup.get("Company Name", "").lower()
            if name and name not in startup_names:
                new_startups.append(startup)
                startup_names.add(name)
                all_startups.append(startup)
        
        print(f"Found {len(startups)} startups ({len(new_startups)} new) in {discovery_time:.2f} seconds")
        
        # Print the startup names
        for startup in new_startups:
            print(f"- {startup.get('Company Name', 'Unknown')}")
    
    # Summary
    print("\n=== Summary ===")
    print(f"Total unique startups discovered: {len(all_startups)}")
    print(f"Expanded queries: {len(expanded_queries)}")
    print("\nUnique startups:")
    for startup in all_startups:
        print(f"- {startup.get('Company Name', 'Unknown')}")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    test_query_expansion_integration()
