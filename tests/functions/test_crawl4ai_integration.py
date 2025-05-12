"""
Test the integration of Crawl4AI with the startup discovery process.
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

from src.processor.crawler import GeminiDataSource
from src.utils.api_client import GeminiAPIClient

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_crawl4ai_integration():
    """Test the integration of Crawl4AI with the startup discovery process."""
    print("\n=== Testing Crawl4AI Integration ===\n")

    # Ensure environment is set up
    setup_env.setup_environment(test_apis=False)

    # Create the Gemini data source
    api_client = GeminiAPIClient()
    gemini_data_source = GeminiDataSource(api_client=api_client)

    # Test URL with known startup mentions
    test_url = "https://builtin.com/artificial-intelligence/ai-companies-roundup"
    test_title = "Top AI Companies & Startups to Know in 2024"
    test_snippet = "Here are the top AI companies and startups to know in 2024, including OpenAI, Anthropic, and more."
    test_query = "AI startups"

    print(f"Testing startup extraction from: {test_url}")
    print(f"Original query: {test_query}")
    print("-" * 50)

    # Extract startup names using the enhanced method
    start_time = time.time()
    try:
        # Test the Gemini API directly first
        print("\nTesting Gemini API directly...")
        try:
            response = gemini_data_source.api_client.flash_model.generate_content("List 5 popular AI startups")
            print(f"Direct Gemini API test successful. Response: {response.text[:200]}...")
        except Exception as api_e:
            print(f"Direct Gemini API test failed: {api_e}")
            print(f"API key: {gemini_data_source.api_client.api_key[:5]}...{gemini_data_source.api_client.api_key[-5:]}")
            print(f"Model name: {gemini_data_source.api_client.flash_model.model_name}")

        # Now try the actual extraction
        print("\nTesting startup name extraction...")

        # Test with normal extraction first
        print("1. Testing with Crawl4AI (should succeed):")
        startup_names = gemini_data_source.extract_startup_names(
            title=test_title,
            snippet=test_snippet,
            url=test_url,
            original_query=test_query
        )

        # Now test with a simulated Crawl4AI failure to test Beautiful Soup fallback
        print("\n2. Testing with Crawl4AI failure (should fall back to Beautiful Soup):")

        # Create a patched version of the method that simulates Crawl4AI failure
        original_run = asyncio.run

        def mock_run(_):
            # This will simulate a failure in Crawl4AI
            return None

        # Apply the patch
        asyncio.run = mock_run

        # Run the extraction with the patched method
        fallback_names = gemini_data_source.extract_startup_names(
            title=test_title,
            snippet=test_snippet,
            url=test_url,
            original_query=test_query
        )

        # Restore the original method
        asyncio.run = original_run
        end_time = time.time()

        # Display results from normal extraction
        if startup_names:
            print(f"\nCrawl4AI extraction results: {len(startup_names)} startup names found in {end_time - start_time:.2f} seconds:")
            for i, name in enumerate(startup_names):
                print(f"{i+1}. {name}")
        else:
            print(f"\nCrawl4AI extraction: No startup names found in {end_time - start_time:.2f} seconds.")

        # Display results from fallback extraction
        if fallback_names:
            print(f"\nBeautiful Soup fallback results: {len(fallback_names)} startup names found:")
            for i, name in enumerate(fallback_names):
                print(f"{i+1}. {name}")
        else:
            print(f"\nBeautiful Soup fallback: No startup names found.")
    except Exception as e:
        end_time = time.time()
        print(f"\nError extracting startup names: {e}")
        import traceback
        print(f"Error traceback: {traceback.format_exc()}")
        print(f"Time taken: {end_time - start_time:.2f} seconds")

    # Note about pattern-based extraction
    print("\nNote: Pattern-based extraction has been completely removed from the codebase.")
    print("The system now relies exclusively on Gemini AI for startup name extraction.")

    print("\n=== Test Complete ===")

if __name__ == "__main__":
    test_crawl4ai_integration()
