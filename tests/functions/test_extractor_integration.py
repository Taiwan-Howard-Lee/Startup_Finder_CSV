"""
Test the integration of all extractors.
"""

import os
import sys
import time
import logging

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import setup_env

from src.processor.crawler import StartupCrawler
from src.processor.website_extractor import WebsiteExtractor
from src.processor.linkedin_extractor import LinkedInExtractor
from src.processor.crunchbase_extractor import CrunchbaseExtractor

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_startup_crawler():
    """Test the StartupCrawler with all extractors."""
    print("\n=== Testing StartupCrawler Integration ===\n")
    
    # Create a StartupCrawler instance
    crawler = StartupCrawler(max_workers=3)
    
    # Test query
    test_query = "AI startups in UK"
    
    # Run the search
    print(f"Searching for: {test_query}")
    start_time = time.time()
    results = crawler.search(query=test_query, max_results=3)
    end_time = time.time()
    
    # Display results
    print(f"\nFound {len(results)} startups in {end_time - start_time:.2f} seconds:")
    for i, result in enumerate(results):
        print(f"\n{i+1}. {result.get('Company Name', 'Unknown')}")
        print(f"   Website: {result.get('Website', 'N/A')}")
        print(f"   LinkedIn: {result.get('LinkedIn', 'N/A')}")
        print(f"   Location: {result.get('Location', 'N/A')}")
        print(f"   Founded Year: {result.get('Founded Year', 'N/A')}")
        print(f"   Description: {result.get('Company Description', 'N/A')[:100]}...")
        
        # Show all other fields
        other_fields = [k for k in result.keys() if k not in ['Company Name', 'Website', 'LinkedIn', 'Location', 'Founded Year', 'Company Description']]
        if other_fields:
            print(f"   Other fields: {', '.join(other_fields)}")
    
    print("\n=== StartupCrawler Test Complete ===")

def test_website_extractor():
    """Test the WebsiteExtractor."""
    print("\n=== Testing WebsiteExtractor ===\n")
    
    # Test URL
    test_url = "https://openai.com"
    test_company = "OpenAI"
    
    # Extract data
    print(f"Extracting data from {test_url}")
    start_time = time.time()
    data = WebsiteExtractor.extract_data(company_name=test_company, url=test_url)
    end_time = time.time()
    
    # Display results
    if data:
        print(f"\nExtracted {len(data)} fields in {end_time - start_time:.2f} seconds:")
        for key, value in data.items():
            if isinstance(value, str):
                print(f"{key}: {value[:100]}...")
            else:
                print(f"{key}: {value}")
    else:
        print(f"\nNo data extracted in {end_time - start_time:.2f} seconds.")
    
    print("\n=== WebsiteExtractor Test Complete ===")

def test_linkedin_extractor():
    """Test the LinkedInExtractor."""
    print("\n=== Testing LinkedInExtractor ===\n")
    
    # Test URL
    test_url = "https://www.linkedin.com/company/openai"
    test_company = "OpenAI"
    
    # Extract data
    print(f"Extracting data from {test_url}")
    start_time = time.time()
    data = LinkedInExtractor.extract_data(company_name=test_company, url=test_url)
    end_time = time.time()
    
    # Display results
    if data:
        print(f"\nExtracted {len(data)} fields in {end_time - start_time:.2f} seconds:")
        for key, value in data.items():
            if isinstance(value, str):
                print(f"{key}: {value[:100]}...")
            else:
                print(f"{key}: {value}")
    else:
        print(f"\nNo data extracted in {end_time - start_time:.2f} seconds.")
    
    print("\n=== LinkedInExtractor Test Complete ===")

def test_crunchbase_extractor():
    """Test the CrunchbaseExtractor."""
    print("\n=== Testing CrunchbaseExtractor ===\n")
    
    # Create a StartupCrawler instance to get access to the GoogleSearchDataSource
    crawler = StartupCrawler(max_workers=1)
    
    # Test company
    test_company = "OpenAI"
    
    # Extract data using search
    print(f"Searching for Crunchbase data for {test_company}")
    start_time = time.time()
    data = CrunchbaseExtractor.search_crunchbase_data(
        google_search=crawler.google_search,
        company_name=test_company,
        max_results=3
    )
    end_time = time.time()
    
    # Display results
    if data:
        print(f"\nExtracted {len(data)} fields in {end_time - start_time:.2f} seconds:")
        for key, value in data.items():
            if isinstance(value, str):
                print(f"{key}: {value[:100]}...")
            else:
                print(f"{key}: {value}")
    else:
        print(f"\nNo data extracted in {end_time - start_time:.2f} seconds.")
    
    print("\n=== CrunchbaseExtractor Test Complete ===")

if __name__ == "__main__":
    # Ensure environment is set up
    setup_env.setup_environment(test_apis=False)
    
    # Run the tests
    test_website_extractor()
    test_linkedin_extractor()
    test_crunchbase_extractor()
    test_startup_crawler()
    
    print("\n=== All Tests Complete ===")
