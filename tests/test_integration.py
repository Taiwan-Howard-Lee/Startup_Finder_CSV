"""
Integration tests for Startup Intelligence Finder.
"""

import os
import sys
import unittest
from unittest.mock import patch

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from startup_finder import StartupFinder, SearchResults


class TestStartupFinderIntegration(unittest.TestCase):
    """Integration tests for StartupFinder."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Use mock data for testing
        self.finder = StartupFinder(use_mock_data=True)
    
    def test_basic_search_workflow(self):
        """Test the basic search workflow."""
        # Perform a search
        results = self.finder.search(
            query="AI startups in healthcare",
            fields=["Founders", "Funding Information", "Technology Stack"]
        )
        
        # Verify results
        self.assertIsInstance(results, SearchResults)
        self.assertGreater(len(results), 0)
        
        # Check that results have the requested fields
        first_result = results[0]
        self.assertIn("Founders", first_result)
        self.assertIn("Funding Information", first_result)
        self.assertIn("Technology Stack", first_result)
        
        # Check that results have confidence scores
        self.assertIn("confidence", first_result)
    
    def test_export_functionality(self):
        """Test the export functionality."""
        # Perform a search
        results = self.finder.search("AI startups")
        
        # Test CSV export
        csv_filename = "test_export.csv"
        csv_path = results.to_csv(csv_filename)
        self.assertTrue(os.path.exists(csv_path))
        
        # Test JSON export
        json_filename = "test_export.json"
        json_path = results.to_json(json_filename)
        self.assertTrue(os.path.exists(json_path))
        
        # Clean up test files
        try:
            os.remove(csv_path)
            os.remove(json_path)
        except:
            pass
    
    def test_end_to_end_workflow(self):
        """Test the end-to-end workflow with custom configuration."""
        # Custom configuration
        config = {
            "max_results": 5,
            "min_confidence": 0.5,
            "export_format": "json"
        }
        
        # Perform a search with custom configuration
        results = self.finder.search(
            query="fintech blockchain startups",
            fields=["Founders", "Funding Information", "Technology Stack", 
                   "Product Description", "Business Model"],
            config=config
        )
        
        # Verify results
        self.assertIsInstance(results, SearchResults)
        self.assertLessEqual(len(results), config["max_results"])
        
        # Check that all results have confidence above the threshold
        for result in results:
            self.assertGreaterEqual(result["confidence"], config["min_confidence"])
        
        # Convert to DataFrame
        df = results.to_dataframe()
        self.assertEqual(len(df), len(results))
        
        # Test head and tail methods
        head_df = results.head(2)
        self.assertLessEqual(len(head_df), 2)
        
        tail_df = results.tail(2)
        self.assertLessEqual(len(tail_df), 2)


if __name__ == "__main__":
    unittest.main()
