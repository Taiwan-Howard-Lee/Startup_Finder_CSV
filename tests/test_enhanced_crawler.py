#!/usr/bin/env python3
"""
Test script for the enhanced crawler to verify LinkedIn and Crunchbase data extraction.
"""

import logging
import os
import sys
from typing import Dict, Any

# Import setup_env to ensure API keys are available
import setup_env

# Import the enhanced crawler
from src.processor.enhanced_crawler import EnhancedStartupCrawler
from src.processor.crunchbase_extractor import CrunchbaseExtractor

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_linkedin_extraction():
    """Test LinkedIn data extraction using Google Search as a proxy."""
    print("\n=== Testing LinkedIn Data Extraction ===\n")
    
    # Create an enhanced crawler
    crawler = EnhancedStartupCrawler()
    
    # Test companies
    companies = [
        "OpenAI",
        "Anthropic",
        "Cohere",
        "Databricks",
        "Scale AI"
    ]
    
    for company in companies:
        print(f"\nExtracting LinkedIn data for: {company}")
        
        # Extract LinkedIn data
        data = {}
        data = crawler._extract_linkedin_data(company, data)
        
        # Print the results
        print(f"LinkedIn data for {company}:")
        for key, value in data.items():
            print(f"  {key}: {value}")

def test_crunchbase_extraction():
    """Test Crunchbase data extraction using Google Search as a proxy."""
    print("\n=== Testing Crunchbase Data Extraction ===\n")
    
    # Create an enhanced crawler
    crawler = EnhancedStartupCrawler()
    
    # Test companies
    companies = [
        "OpenAI",
        "Anthropic",
        "Cohere",
        "Databricks",
        "Scale AI"
    ]
    
    for company in companies:
        print(f"\nExtracting Crunchbase data for: {company}")
        
        # Extract Crunchbase data
        data = {}
        data = crawler._extract_crunchbase_data(company, data)
        
        # Print the results
        print(f"Crunchbase data for {company}:")
        for key, value in data.items():
            print(f"  {key}: {value}")

def test_direct_crunchbase_extraction():
    """Test direct Crunchbase data extraction from search results."""
    print("\n=== Testing Direct Crunchbase Data Extraction ===\n")
    
    # Create an enhanced crawler
    crawler = EnhancedStartupCrawler()
    
    # Test companies
    companies = [
        "OpenAI",
        "Anthropic",
        "Cohere",
        "Databricks",
        "Scale AI"
    ]
    
    for company in companies:
        print(f"\nExtracting direct Crunchbase data for: {company}")
        
        # Extract Crunchbase data directly from search results
        crunchbase_data = CrunchbaseExtractor.search_crunchbase_data(crawler.google_search, company, max_results=3)
        
        # Print the results
        print(f"Direct Crunchbase data for {company}:")
        for key, value in crunchbase_data.items():
            print(f"  {key}: {value}")

def main():
    """Main function to run the tests."""
    print("\n=== Enhanced Crawler Test ===\n")
    
    # Test LinkedIn extraction
    test_linkedin_extraction()
    
    # Test Crunchbase extraction
    test_crunchbase_extraction()
    
    # Test direct Crunchbase extraction
    test_direct_crunchbase_extraction()
    
    print("\n=== Test Complete ===\n")

if __name__ == "__main__":
    main()
