"""
Test script for the two-phase crawling strategy in the Startup Intelligence Finder.
"""

import os
import sys
import unittest

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import setup_env

from src.processor.crawler import StartupCrawler


class TestTwoPhaseCrawler(unittest.TestCase):
    """Tests for the two-phase crawling strategy."""

    def setUp(self):
        """Set up test fixtures."""
        # Ensure environment is set up
        setup_env.setup_environment(test_apis=False)

        # Create a crawler for testing
        self.crawler = StartupCrawler(max_workers=2)

    def test_discover_startups(self):
        """Test the first phase: discovering startup names."""
        query = "ai healthcare startups"
        startup_info_list = self.crawler.discover_startups(query, max_results=5)

        # Check if startup names were discovered
        self.assertIsNotNone(startup_info_list)

        # Print discovered startup names
        print("\nDiscovered startup names:")
        for startup in startup_info_list:
            print(f"- {startup.get('Company Name', 'Unknown')}")

    def test_enrich_startup_data(self):
        """Test the second phase: enriching startup data."""
        # Create startup info list with basic information
        startup_info_list = [
            {"Company Name": "HealthAI"},
            {"Company Name": "MedMind"},
            {"Company Name": "BlockPay"}
        ]

        enriched_data = self.crawler.enrich_startup_data(startup_info_list)

        # Check if data was enriched
        self.assertIsNotNone(enriched_data)

        # Print enriched data
        print("\nEnriched startup data:")
        for data in enriched_data:
            print(f"\n{data.get('Company Name', 'Unknown')}:")
            for key, value in data.items():
                if key != "Company Name":
                    print(f"  {key}: {value}")

    def test_full_search(self):
        """Test the complete two-phase search process."""
        query = "ai healthcare startups"
        results = self.crawler.search(query, max_results=5)

        # Check if results were found
        self.assertIsNotNone(results)

        # Print search results
        print("\nFull search results:")
        for result in results:
            print(f"\n{result.get('Company Name', 'Unknown')}:")
            for key, value in result.items():
                if key != "Company Name":
                    print(f"  {key}: {value}")


if __name__ == "__main__":
    unittest.main()
