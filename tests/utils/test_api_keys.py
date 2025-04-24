"""
Test API Keys for Startup Intelligence Finder.

This script tests the API keys for the Gemini API and Google Search API.
"""

import os
import sys
import json
import requests

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Try to import google.generativeai for testing Gemini API
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("Warning: google.generativeai package not installed. Cannot test Gemini API key.")


def load_env_file(env_file=".env"):
    """
    Load environment variables from .env file.

    Args:
        env_file: Path to the .env file.
    """
    try:
        with open(env_file, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                key, value = line.split("=", 1)
                os.environ[key] = value

        print(f"Loaded environment variables from {env_file}")
    except Exception as e:
        print(f"Error loading environment variables: {e}")


def test_gemini_api():
    """
    Test the Gemini API key.

    Returns:
        bool: True if the API key is valid, False otherwise.
    """
    if not GEMINI_AVAILABLE:
        print("Cannot test Gemini API key: google.generativeai package not installed.")
        return False

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Gemini API key not found in environment variables.")
        return False

    print(f"Testing Gemini API key: {api_key[:5]}...{api_key[-5:]}")

    try:
        # Configure the Gemini API with the provided key
        genai.configure(api_key=api_key)

        # Try a simple model call with the flash model
        model = genai.GenerativeModel('gemini-2.5-flash-preview-04-17')
        response = model.generate_content("Hello, world! Please respond with a single word.")

        # Print the response
        print(f"Gemini API response: {response.text}")

        # If we get here, the API key is valid
        print("✅ Gemini API key is valid!")
        return True
    except Exception as e:
        print(f"❌ Error testing Gemini API key: {e}")
        return False


def test_google_search_api():
    """
    Test the Google Search API key and CX ID.

    Returns:
        bool: True if the API key and CX ID are valid, False otherwise.
    """
    api_key = os.environ.get("GOOGLE_SEARCH_API_KEY")
    cx_id = os.environ.get("GOOGLE_CX_ID")

    if not api_key:
        print("Google Search API key not found in environment variables.")
        return False

    if not cx_id:
        print("Google Custom Search Engine ID not found in environment variables.")
        return False

    print(f"Testing Google Search API key: {api_key[:5]}...{api_key[-5:]} and CX ID: {cx_id}")

    try:
        # Prepare the API URL
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": api_key,
            "cx": cx_id,
            "q": "test query",  # Simple test query
            "num": 1  # Just get one result to minimize API usage
        }

        # Make the request
        response = requests.get(url, params=params)

        # Check if the request was successful
        if response.status_code == 200:
            # Print some information from the response
            data = response.json()
            if "items" in data and len(data["items"]) > 0:
                first_result = data["items"][0]
                print(f"First search result: {first_result.get('title', 'No title')}")
                print(f"URL: {first_result.get('link', 'No link')}")

            print("✅ Google Search API is working!")
            return True
        else:
            error_message = response.json().get("error", {}).get("message", "Unknown error")
            print(f"❌ Google Search API error: {error_message}")
            return False
    except Exception as e:
        print(f"❌ Error testing Google Search API: {e}")
        return False


if __name__ == "__main__":
    # Load environment variables from .env file
    load_env_file()

    print("\n=== Testing API Keys ===\n")

    # Test Gemini API key
    print("Testing Gemini API key...")
    gemini_result = test_gemini_api()

    print("\nTesting Google Search API...")
    google_result = test_google_search_api()

    print("\n=== Test Results ===")
    print(f"Gemini API: {'✅ Valid' if gemini_result else '❌ Invalid'}")
    print(f"Google Search API: {'✅ Valid' if google_result else '❌ Invalid'}")

    if not (gemini_result or google_result):
        print("\nNeither API key is valid. Please check your API keys and try again.")
        sys.exit(1)
    elif not gemini_result:
        print("\nGemini API key is invalid. Some functionality may be limited.")
    elif not google_result:
        print("\nGoogle Search API key is invalid. Some functionality may be limited.")
    else:
        print("\nAll API keys are valid! You're ready to use the Startup Intelligence Finder.")
