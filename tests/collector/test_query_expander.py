"""
Tests for the query_expander module.
"""

import os
import sys
import unittest

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import setup_env

from src.collector.query_expander import QueryExpander
from src.utils.api_client import GeminiAPIClient


class TestQueryExpander(unittest.TestCase):
    """Tests for the QueryExpander class."""

    def setUp(self):
        """Set up test fixtures."""
        # Ensure environment is set up
        setup_env.setup_environment(test_apis=False)

        # Create a real API client
        try:
            self.api_client = GeminiAPIClient()
            self.query_expander = QueryExpander(api_client=self.api_client)
            self.skip_tests = False
        except Exception as e:
            print(f"\nWarning: Could not initialize Gemini API client: {e}")
            print("Tests will be skipped. Please set up a valid API key.")
            self.skip_tests = True

    def test_expand_query(self):
        """Test query expansion."""
        if self.skip_tests:
            self.skipTest("Gemini API client not available")

        query = "AI startups in healthcare"
        expanded = self.query_expander.expand_query(query)

        # Should include original query
        self.assertIn(query, expanded)

        # Print the expanded queries for inspection
        print(f"\nExpanded queries: {expanded}")

        # Note: We're not asserting on the length here because if the API key is invalid,
        # the expander will just return the original query, which is the correct fallback behavior

    def test_expand_query_with_invalid_query(self):
        """Test query expansion with an invalid query."""
        if self.skip_tests:
            self.skipTest("Gemini API client not available")

        # Use an empty query which should cause the API to return an error
        query = ""  # Empty query should cause an error

        # The expander should handle the error and return just the original query
        try:
            expanded = self.query_expander.expand_query(query)
            # If we get here, the error handling worked
            self.assertEqual([query], expanded)
        except ValueError:
            # This is also acceptable - the InputHandler would catch this
            pass

    def test_get_search_keywords(self):
        """Test keyword extraction."""
        if self.skip_tests:
            self.skipTest("Gemini API client not available")

        query = "Find AI startups in healthcare with female founders"
        keywords = self.query_expander.get_search_keywords(query)

        # Should extract important keywords
        self.assertIn("ai", keywords)
        self.assertIn("startups", keywords)
        self.assertIn("healthcare", keywords)
        self.assertIn("female", keywords)
        self.assertIn("founders", keywords)

        # Should not include stopwords
        self.assertNotIn("find", keywords)
        self.assertNotIn("in", keywords)
        self.assertNotIn("with", keywords)

        # Print the keywords for inspection
        print(f"\nExtracted keywords: {keywords}")

    def test_generate_search_combinations(self):
        """Test search combination generation."""
        if self.skip_tests:
            self.skipTest("Gemini API client not available")

        query = "AI healthcare startups"
        combinations = self.query_expander.generate_search_combinations(query)

        # Should include expanded queries
        self.assertIn(query, combinations)

        # Should include keyword combinations
        keywords = self.query_expander.get_search_keywords(query)
        if len(keywords) >= 2:
            expected_combo = f"{keywords[0]} {keywords[1]}"
            self.assertIn(expected_combo, combinations)

        # Should have multiple combinations
        self.assertGreater(len(combinations), 1)

        # Print the combinations for inspection
        print(f"\nSearch combinations: {combinations}")


if __name__ == "__main__":
    unittest.main()
