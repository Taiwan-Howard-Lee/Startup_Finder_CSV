#!/usr/bin/env python3
"""
Test script to verify the query expander fix.
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.collector.query_expander import QueryExpander
from src.utils.api_client import GeminiAPIClient

def test_query_expander():
    """Test the query expander with different numbers of expansions."""

    print("Testing Query Expander Fix")
    print("=" * 50)

    try:
        # Initialize the query expander
        gemini_client = GeminiAPIClient()
        query_expander = QueryExpander(api_client=gemini_client)

        test_query = "AI startups"

        # Test different numbers of expansions
        test_cases = [1, 3, 5, 10, 20]

        for num_expansions in test_cases:
            print(f"\nTesting with {num_expansions} expansions:")
            print("-" * 30)

            expanded_queries = query_expander.expand_query(test_query, num_expansions=num_expansions)

            print(f"Requested: {num_expansions} new expansions")
            print(f"Expected total: {num_expansions + 1} queries (original + new)")
            print(f"Actual total: {len(expanded_queries)} queries")
            print(f"New expansions generated: {len(expanded_queries) - 1}")

            print("\nGenerated queries:")
            for i, query in enumerate(expanded_queries):
                marker = "(original)" if i == 0 else "(new)"
                print(f"  {i+1}. {query} {marker}")

            # Verify the count is correct
            expected_total = num_expansions + 1
            if len(expanded_queries) == expected_total:
                print(f"✅ SUCCESS: Got expected {expected_total} total queries")
            else:
                print(f"❌ FAILED: Expected {expected_total} total queries, got {len(expanded_queries)}")

            print()

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_query_expander()
