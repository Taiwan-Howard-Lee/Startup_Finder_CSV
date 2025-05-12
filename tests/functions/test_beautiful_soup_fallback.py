"""
Test the Beautiful Soup fallback for all extractors.
"""

import os
import sys
import time
import logging
import asyncio
import requests
from bs4 import BeautifulSoup

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import setup_env

from src.processor.crawler import WebCrawler
from src.processor.website_extractor import WebsiteExtractor
from src.processor.linkedin_extractor import LinkedInExtractor
from src.processor.crunchbase_extractor import CrunchbaseExtractor

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_web_crawler_fallback():
    """Test the Beautiful Soup fallback in WebCrawler."""
    print("\n=== Testing WebCrawler Beautiful Soup Fallback ===\n")
    
    # Create a WebCrawler instance
    web_crawler = WebCrawler()
    
    # Test URL
    test_url = "https://openai.com"
    
    # Test the primary method
    print(f"1. Testing primary method for {test_url}")
    start_time = time.time()
    raw_html, soup = web_crawler.fetch_webpage(test_url)
    end_time = time.time()
    
    if raw_html and soup:
        print(f"Primary method succeeded in {end_time - start_time:.2f} seconds")
        print(f"Content length: {len(raw_html)} characters")
        print(f"Title: {soup.title.get_text() if soup.title else 'No title'}")
    else:
        print(f"Primary method failed in {end_time - start_time:.2f} seconds")
    
    # Now simulate a failure in the primary method to test the fallback
    print(f"\n2. Testing Beautiful Soup fallback (simulated primary method failure)")
    
    # Create a patched version of the session.get method that simulates a failure
    original_get = requests.Session.get
    
    def mock_get(*args, **kwargs):
        # This will simulate a failure in the primary method
        raise Exception("Simulated primary method failure")
    
    # Apply the patch
    requests.Session.get = mock_get
    
    # Run the fetch_webpage method with the patched session.get
    start_time = time.time()
    raw_html, soup = web_crawler.fetch_webpage(test_url)
    end_time = time.time()
    
    # Restore the original method
    requests.Session.get = original_get
    
    if raw_html and soup:
        print(f"Beautiful Soup fallback succeeded in {end_time - start_time:.2f} seconds")
        print(f"Content length: {len(raw_html)} characters")
        print(f"Title: {soup.title.get_text() if soup.title else 'No title'}")
    else:
        print(f"Beautiful Soup fallback failed in {end_time - start_time:.2f} seconds")
    
    print("\n=== WebCrawler Test Complete ===")

def test_website_extractor_fallback():
    """Test the Beautiful Soup fallback in WebsiteExtractor."""
    print("\n=== Testing WebsiteExtractor Beautiful Soup Fallback ===\n")
    
    # Test URL
    test_url = "https://openai.com"
    test_company = "OpenAI"
    
    # Test direct fetch
    print(f"1. Testing direct fetch with WebsiteExtractor for {test_url}")
    start_time = time.time()
    data = WebsiteExtractor.extract_data(company_name=test_company, url=test_url)
    end_time = time.time()
    
    if data:
        print(f"Direct fetch succeeded in {end_time - start_time:.2f} seconds")
        print(f"Extracted fields: {list(data.keys())}")
    else:
        print(f"Direct fetch failed in {end_time - start_time:.2f} seconds")
    
    print("\n=== WebsiteExtractor Test Complete ===")

def test_linkedin_extractor_fallback():
    """Test the Beautiful Soup fallback in LinkedInExtractor."""
    print("\n=== Testing LinkedInExtractor Beautiful Soup Fallback ===\n")
    
    # Test URL
    test_url = "https://www.linkedin.com/company/openai"
    test_company = "OpenAI"
    
    # Test direct fetch
    print(f"1. Testing direct fetch with LinkedInExtractor for {test_url}")
    start_time = time.time()
    data = LinkedInExtractor.extract_data(company_name=test_company, url=test_url)
    end_time = time.time()
    
    if data:
        print(f"Direct fetch succeeded in {end_time - start_time:.2f} seconds")
        print(f"Extracted fields: {list(data.keys())}")
    else:
        print(f"Direct fetch failed in {end_time - start_time:.2f} seconds")
    
    print("\n=== LinkedInExtractor Test Complete ===")

def test_crunchbase_extractor_fallback():
    """Test the Beautiful Soup fallback in CrunchbaseExtractor."""
    print("\n=== Testing CrunchbaseExtractor Beautiful Soup Fallback ===\n")
    
    # Test URL
    test_url = "https://www.crunchbase.com/organization/openai"
    test_company = "OpenAI"
    
    # Test direct fetch
    print(f"1. Testing direct fetch with CrunchbaseExtractor for {test_url}")
    start_time = time.time()
    data = CrunchbaseExtractor.extract_data(company_name=test_company, url=test_url)
    end_time = time.time()
    
    if data:
        print(f"Direct fetch succeeded in {end_time - start_time:.2f} seconds")
        print(f"Extracted fields: {list(data.keys())}")
    else:
        print(f"Direct fetch failed in {end_time - start_time:.2f} seconds")
    
    print("\n=== CrunchbaseExtractor Test Complete ===")

if __name__ == "__main__":
    # Ensure environment is set up
    setup_env.setup_environment(test_apis=False)
    
    # Run the tests
    test_web_crawler_fallback()
    test_website_extractor_fallback()
    test_linkedin_extractor_fallback()
    test_crunchbase_extractor_fallback()
    
    print("\n=== All Tests Complete ===")
