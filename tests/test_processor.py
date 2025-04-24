"""
Tests for the processor module.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.processor.crawler import Crawler, MockDataSource
from src.processor.ranker import Ranker


class TestCrawler(unittest.TestCase):
    """Tests for the Crawler class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.crawler = Crawler(use_mock_data=True)
    
    def test_search_with_mock_data(self):
        """Test search with mock data."""
        queries = ["ai healthcare"]
        results = self.crawler.search(queries)
        
        # Should return results
        self.assertGreater(len(results), 0)
        
        # Results should have expected fields
        first_result = results[0]
        self.assertIn("Company Name", first_result)
        self.assertIn("Founded Year", first_result)
        self.assertIn("Location", first_result)
        self.assertIn("Website", first_result)
    
    def test_search_with_multiple_queries(self):
        """Test search with multiple queries."""
        queries = ["ai healthcare", "fintech blockchain"]
        results = self.crawler.search(queries)
        
        # Should return results
        self.assertGreater(len(results), 0)
        
        # Should include results from both queries
        company_names = [result.get("Company Name") for result in results]
        self.assertIn("HealthAI", company_names)
        self.assertIn("BlockPay", company_names)
    
    def test_search_with_max_results(self):
        """Test search with max_results limit."""
        queries = ["ai healthcare", "fintech blockchain", "sustainable energy"]
        max_results = 2
        results = self.crawler.search(queries, max_results=max_results)
        
        # Should respect max_results limit
        self.assertLessEqual(len(results), max_results)


class TestRanker(unittest.TestCase):
    """Tests for the Ranker class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.ranker = Ranker()
        
        # Sample startup data for testing
        self.startup_data = {
            "Company Name": "HealthAI",
            "Founded Year": "2021",
            "Location": "Boston, MA",
            "Website": "healthai.com",
            "Founders": "Jane Smith, PhD",
            "Funding Information": "Series A $5M",
            "Technology Stack": "Python, TensorFlow",
            "Product Description": "AI-powered diagnostic tools for healthcare providers"
        }
        
        self.query = "AI healthcare startups"
    
    def test_calculate_content_relevance(self):
        """Test content relevance calculation."""
        score = self.ranker.calculate_content_relevance(self.startup_data, self.query)
        
        # Score should be between 0 and 1
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)
        
        # Score should be higher for relevant startup
        irrelevant_query = "blockchain fintech"
        irrelevant_score = self.ranker.calculate_content_relevance(self.startup_data, irrelevant_query)
        self.assertGreater(score, irrelevant_score)
    
    def test_calculate_information_quality(self):
        """Test information quality calculation."""
        score = self.ranker.calculate_information_quality(self.startup_data)
        
        # Score should be between 0 and 1
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)
        
        # Score should be lower for incomplete data
        incomplete_data = {
            "Company Name": "HealthAI",
            "Founded Year": "Unknown",
            "Location": "Unknown",
            "Website": "healthai.com"
        }
        incomplete_score = self.ranker.calculate_information_quality(incomplete_data)
        self.assertGreater(score, incomplete_score)
    
    def test_calculate_startup_relevance(self):
        """Test startup relevance calculation."""
        score = self.ranker.calculate_startup_relevance(self.startup_data, self.query)
        
        # Score should be between 0 and 1
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)
    
    def test_calculate_overall_score(self):
        """Test overall score calculation."""
        score = self.ranker.calculate_overall_score(self.startup_data, self.query)
        
        # Score should be between 0 and 1
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)
    
    def test_rank_results(self):
        """Test result ranking."""
        # Create sample results
        results = [
            self.startup_data,
            {
                "Company Name": "MedMind",
                "Founded Year": "2019",
                "Location": "San Francisco, CA",
                "Website": "medmind.ai",
                "Founders": "John Doe, Sarah Johnson",
                "Funding Information": "Seed $2M",
                "Technology Stack": "Python, PyTorch, AWS",
                "Product Description": "AI assistant for medical professionals"
            },
            {
                "Company Name": "BlockPay",
                "Founded Year": "2020",
                "Location": "New York, NY",
                "Website": "blockpay.io",
                "Founders": "Michael Chen",
                "Funding Information": "Series B $15M",
                "Technology Stack": "Solidity, React, Node.js",
                "Product Description": "Blockchain-based payment processing"
            }
        ]
        
        ranked_results = self.ranker.rank_results(results, self.query)
        
        # Should return all results
        self.assertEqual(len(ranked_results), len(results))
        
        # Should add confidence scores
        self.assertIn("confidence", ranked_results[0])
        
        # Should rank relevant results higher
        # AI healthcare startups should rank higher than blockchain startups
        ai_companies = ["HealthAI", "MedMind"]
        blockchain_companies = ["BlockPay"]
        
        # Find positions
        positions = {}
        for i, result in enumerate(ranked_results):
            positions[result["Company Name"]] = i
        
        # Check if any AI company is ranked higher than any blockchain company
        ai_positions = [positions[company] for company in ai_companies if company in positions]
        blockchain_positions = [positions[company] for company in blockchain_companies if company in positions]
        
        if ai_positions and blockchain_positions:
            self.assertLess(min(ai_positions), min(blockchain_positions))
    
    def test_min_confidence_filter(self):
        """Test minimum confidence filtering."""
        # Create sample results
        results = [
            self.startup_data,
            {
                "Company Name": "BlockPay",
                "Founded Year": "2020",
                "Location": "New York, NY",
                "Website": "blockpay.io",
                "Founders": "Michael Chen",
                "Funding Information": "Series B $15M",
                "Technology Stack": "Solidity, React, Node.js",
                "Product Description": "Blockchain-based payment processing"
            }
        ]
        
        # Set a high min_confidence to filter out irrelevant results
        ranked_results = self.ranker.rank_results(results, self.query, min_confidence=0.9)
        
        # Should filter out irrelevant results
        self.assertLessEqual(len(ranked_results), len(results))


if __name__ == "__main__":
    unittest.main()
