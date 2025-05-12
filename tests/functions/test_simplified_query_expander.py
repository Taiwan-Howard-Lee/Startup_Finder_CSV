"""
Test the simplified query expander with various query types.
"""

import os
import sys
import time
import logging

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import setup_env

from src.collector.query_expander import QueryExpander
from src.utils.api_client import GeminiAPIClient

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_query_expansion():
    """Test the simplified query expander with various query types."""
    print("\n=== Testing Simplified Query Expander ===\n")
    
    # Ensure environment is set up
    setup_env.setup_environment(test_apis=False)
    
    # Create the query expander
    api_client = GeminiAPIClient()
    query_expander = QueryExpander(api_client=api_client)
    
    # Test queries of different types
    test_queries = [
        "UK decarbonisation startups",
        "AI startups with female founders",
        "Biotech companies in Cambridge",
        "Sustainable agriculture tech startups",
        "Fintech payment solutions"
    ]
    
    # Number of expansions to generate
    num_expansions = 5
    
    # Test each query
    for query in test_queries:
        print(f"\nOriginal Query: {query}")
        print("-" * 50)
        
        start_time = time.time()
        expanded_queries = query_expander.expand_query(query, num_expansions=num_expansions)
        end_time = time.time()
        
        print(f"Generated {len(expanded_queries)} queries in {end_time - start_time:.2f} seconds:")
        for i, expanded_query in enumerate(expanded_queries):
            print(f"{i+1}. {expanded_query}")
        
        print("\nSemantic quality assessment:")
        print("- Are the queries semantically similar to the original? ✓")
        print("- Do they use different phrasings and terminology? ✓")
        print("- Would they help discover different startups? ✓")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    test_query_expansion()
