"""
Test the startup name extraction functionality.
"""

import os
import sys
import logging

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import setup_env

from src.processor.crawler import GeminiDataSource

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_startup_extraction():
    """Test the extraction of startup names from a mock response."""
    print("\n=== Testing Startup Name Extraction ===\n")
    
    # Create a GeminiDataSource instance
    gemini_source = GeminiDataSource()
    
    # Create a mock response class
    class MockResponse:
        def __init__(self, text):
            self.text = text
    
    # Test case 1: Normal response with multiple startup names
    print("Test Case 1: Normal response with multiple startup names")
    mock_response_1 = MockResponse("OpenAI, Google, Microsoft, Anthropic, Meta, DeepMind, Cohere, AI21 Labs, Stability AI, Hugging Face")
    gemini_source.api_client.flash_model.generate_content = lambda _: mock_response_1
    
    startup_names = gemini_source.extract_startup_names("Test Title", "Test Snippet", "https://example.com")
    
    print(f"Extracted {len(startup_names)} startup names:")
    for i, name in enumerate(startup_names):
        print(f"{i+1}. {name}")
    
    # Test case 2: Response with some short names and common words
    print("\nTest Case 2: Response with some short names and common words")
    mock_response_2 = MockResponse("AI, The, And, For, Inc, Ltd, X, Go, Meta, OpenAI")
    gemini_source.api_client.flash_model.generate_content = lambda _: mock_response_2
    
    startup_names = gemini_source.extract_startup_names("Test Title", "Test Snippet", "https://example.com")
    
    print(f"Extracted {len(startup_names)} startup names:")
    for i, name in enumerate(startup_names):
        print(f"{i+1}. {name}")
    
    # Test case 3: Empty response
    print("\nTest Case 3: Empty response")
    mock_response_3 = MockResponse("")
    gemini_source.api_client.flash_model.generate_content = lambda _: mock_response_3
    
    startup_names = gemini_source.extract_startup_names("Test Title", "Test Snippet", "https://example.com")
    
    print(f"Extracted {len(startup_names)} startup names:")
    for i, name in enumerate(startup_names):
        print(f"{i+1}. {name}")
    
    # Test case 4: "No startups found" response
    print("\nTest Case 4: 'No startups found' response")
    mock_response_4 = MockResponse("No startups found")
    gemini_source.api_client.flash_model.generate_content = lambda _: mock_response_4
    
    startup_names = gemini_source.extract_startup_names("Test Title", "Test Snippet", "https://example.com")
    
    print(f"Extracted {len(startup_names)} startup names:")
    for i, name in enumerate(startup_names):
        print(f"{i+1}. {name}")
    
    print("\n=== Startup Name Extraction Test Complete ===")

if __name__ == "__main__":
    # Ensure environment is set up
    setup_env.setup_environment(test_apis=False)
    
    # Run the test
    test_startup_extraction()
