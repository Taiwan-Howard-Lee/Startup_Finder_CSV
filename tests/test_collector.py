"""
Tests for the collector module.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.collector.input_handler import InputHandler
from src.collector.query_expander import QueryExpander
from src.utils.api_client import GeminiAPIClient


class TestInputHandler(unittest.TestCase):
    """Tests for the InputHandler class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.input_handler = InputHandler()
    
    def test_validate_query(self):
        """Test query validation."""
        # Valid query
        valid_query = "AI startups in healthcare"
        self.assertEqual(self.input_handler.validate_query(valid_query), valid_query)
        
        # Empty query
        with self.assertRaises(ValueError):
            self.input_handler.validate_query("")
        
        # Too short query
        with self.assertRaises(ValueError):
            self.input_handler.validate_query("AI")
    
    def test_validate_fields(self):
        """Test field validation."""
        # Default fields
        default_fields = self.input_handler.validate_fields(None)
        self.assertEqual(len(default_fields), 4)
        self.assertIn("Company Name", default_fields)
        
        # Custom fields
        custom_fields = ["Founders", "Funding Information"]
        validated_fields = self.input_handler.validate_fields(custom_fields)
        self.assertIn("Founders", validated_fields)
        self.assertIn("Funding Information", validated_fields)
        
        # Basic fields should always be included
        self.assertIn("Company Name", validated_fields)
        self.assertIn("Website", validated_fields)
        
        # Invalid field
        with self.assertRaises(ValueError):
            self.input_handler.validate_fields(["Invalid Field"])
    
    def test_validate_config(self):
        """Test configuration validation."""
        # Default config
        default_config = self.input_handler.validate_config(None)
        self.assertEqual(default_config["max_results"], 50)
        self.assertEqual(default_config["min_confidence"], 0.8)
        
        # Custom config
        custom_config = {
            "max_results": 10,
            "min_confidence": 0.5
        }
        validated_config = self.input_handler.validate_config(custom_config)
        self.assertEqual(validated_config["max_results"], 10)
        self.assertEqual(validated_config["min_confidence"], 0.5)
        
        # Invalid max_results
        with self.assertRaises(ValueError):
            self.input_handler.validate_config({"max_results": -1})
        
        # Invalid min_confidence
        with self.assertRaises(ValueError):
            self.input_handler.validate_config({"min_confidence": 1.5})
    
    def test_process_input(self):
        """Test input processing."""
        # Basic input
        processed = self.input_handler.process_input("AI startups")
        self.assertEqual(processed["query"], "AI startups")
        self.assertEqual(len(processed["fields"]), 4)
        self.assertEqual(processed["config"]["max_results"], 50)


class TestQueryExpander(unittest.TestCase):
    """Tests for the QueryExpander class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock the API client
        self.mock_api_client = MagicMock(spec=GeminiAPIClient)
        self.mock_api_client.expand_query.return_value = [
            "AI healthcare startups",
            "medical artificial intelligence companies",
            "health tech AI firms"
        ]
        
        self.query_expander = QueryExpander(api_client=self.mock_api_client)
    
    def test_expand_query(self):
        """Test query expansion."""
        query = "AI startups in healthcare"
        expanded = self.query_expander.expand_query(query)
        
        # Should include original query
        self.assertIn(query, expanded)
        
        # Should have additional expansions
        self.assertGreater(len(expanded), 1)
        
        # API client should have been called
        self.mock_api_client.expand_query.assert_called_once()
    
    def test_get_search_keywords(self):
        """Test keyword extraction."""
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
    
    def test_generate_search_combinations(self):
        """Test search combination generation."""
        query = "AI healthcare startups"
        combinations = self.query_expander.generate_search_combinations(query)
        
        # Should include expanded queries
        self.assertIn(query, combinations)
        
        # Should include keyword combinations
        self.assertIn("ai healthcare", combinations)
        
        # Should have multiple combinations
        self.assertGreater(len(combinations), 1)


if __name__ == "__main__":
    unittest.main()
