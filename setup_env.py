"""
Environment setup script for Startup Intelligence Finder.

This script helps set up the environment for the Startup Intelligence Finder,
including prompting for API keys if they're not already set.
"""

import os
import sys
import getpass
import json
import requests

# Try to import google.generativeai for testing Gemini API
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


def test_gemini_api_key(api_key):
    """
    Test if the Gemini API key is valid.

    Args:
        api_key: The API key to test.

    Returns:
        bool: True if the API key is valid, False otherwise.
    """
    if not GEMINI_AVAILABLE:
        print("Warning: google.generativeai package not installed. Cannot test Gemini API key.")
        return False

    try:
        # Configure the Gemini API with the provided key
        genai.configure(api_key=api_key)

        # Try a simple model call with the flash model
        model = genai.GenerativeModel('gemini-2.5-flash-preview-04-17')
        response = model.generate_content("Hello, world!")

        # If we get here, the API key is valid
        return True
    except Exception as e:
        print(f"Error testing Gemini API key: {e}")
        return False


def test_google_search_api(api_key, cx_id):
    """
    Test if the Google Search API key and CX ID are valid.

    Args:
        api_key: The API key to test.
        cx_id: The Custom Search Engine ID to test.

    Returns:
        bool: True if the API key and CX ID are valid, False otherwise.
    """
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
            return True
        else:
            error_message = response.json().get("error", {}).get("message", "Unknown error")
            print(f"Google Search API error: {error_message}")
            return False
    except Exception as e:
        print(f"Error testing Google Search API: {e}")
        return False


def setup_environment(test_apis=True):
    """
    Set up the environment for Startup Intelligence Finder.

    This function checks if the required API keys are set in environment variables,
    and if not, prompts the user to enter them. It can also test the API keys to
    ensure they are valid.

    Args:
        test_apis: Whether to test the API keys after setting them.

    Returns:
        bool: True if setup was successful, False otherwise.
    """
    print("\n=== Startup Intelligence Finder Environment Setup ===")

    # Check for Gemini API key
    gemini_api_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_api_key:
        print("\nGemini API key not found in environment variables.")
        print("You can get a Gemini API key from: https://ai.google.dev/")
        print("\nInstructions to get a Gemini API key:")
        print("1. Go to https://ai.google.dev/")
        print("2. Click on 'Get API key'")
        print("3. Sign in with your Google account")
        print("4. Create a new project or select an existing one")
        print("5. Enable the Gemini API")
        print("6. Copy the API key")

        try:
            # Prompt for API key (using getpass to hide input)
            gemini_api_key = getpass.getpass("Enter your Gemini API key (press Enter to skip): ")

            if gemini_api_key:
                # Set the environment variable for this session
                os.environ["GEMINI_API_KEY"] = gemini_api_key
                print("Gemini API key set for this session.")

                # Test the API key if requested
                if test_apis and GEMINI_AVAILABLE:
                    print("Testing Gemini API key...")
                    if test_gemini_api_key(gemini_api_key):
                        print("✅ Gemini API key is valid!")
                    else:
                        print("❌ Gemini API key is invalid or has issues.")
            else:
                print("Gemini API key skipped.")

        except KeyboardInterrupt:
            print("\nSetup cancelled.")
            return False
    else:
        print("\nGemini API key found in environment variables.")

        # Test the API key if requested
        if test_apis and GEMINI_AVAILABLE:
            print("Testing Gemini API key...")
            if test_gemini_api_key(gemini_api_key):
                print("✅ Gemini API key is valid!")
            else:
                print("❌ Gemini API key is invalid or has issues.")

    # Check for Google Search API key
    google_search_api_key = os.environ.get("GOOGLE_SEARCH_API_KEY")
    if not google_search_api_key:
        print("\nGoogle Search API key not found in environment variables.")
        print("You can get a Google Search API key from: https://developers.google.com/custom-search/v1/overview")
        print("\nInstructions to get a Google Search API key:")
        print("1. Go to https://developers.google.com/custom-search/v1/overview")
        print("2. Click on 'Get a Key'")
        print("3. Sign in with your Google account")
        print("4. Create a new project or select an existing one")
        print("5. Copy the API key")

        try:
            # Prompt for API key
            google_search_api_key = getpass.getpass("Enter your Google Search API key (press Enter to skip): ")

            if google_search_api_key:
                # Set the environment variable for this session
                os.environ["GOOGLE_SEARCH_API_KEY"] = google_search_api_key
                print("Google Search API key set for this session.")
            else:
                print("Google Search API key skipped.")

        except KeyboardInterrupt:
            print("\nSetup cancelled.")
            return False
    else:
        print("\nGoogle Search API key found in environment variables.")

    # Check for Google Custom Search Engine ID
    google_cx_id = os.environ.get("GOOGLE_CX_ID")
    if not google_cx_id:
        print("\nGoogle Custom Search Engine ID not found in environment variables.")
        print("You can create a Custom Search Engine at: https://programmablesearchengine.google.com/")
        print("\nInstructions to get a Custom Search Engine ID:")
        print("1. Go to https://programmablesearchengine.google.com/")
        print("2. Click on 'Add' to create a new search engine")
        print("3. Enter a name for your search engine")
        print("4. Select 'Search the entire web' or specify sites to search")
        print("5. Click 'Create'")
        print("6. Click on 'Control Panel' for your new search engine")
        print("7. Copy the 'Search engine ID' (cx value)")

        try:
            # Prompt for CX ID
            google_cx_id = input("Enter your Google Custom Search Engine ID (press Enter to skip): ")

            if google_cx_id:
                # Set the environment variable for this session
                os.environ["GOOGLE_CX_ID"] = google_cx_id
                print("Google Custom Search Engine ID set for this session.")

                # Test the Google Search API if both keys are available
                if test_apis and google_search_api_key:
                    print("Testing Google Search API...")
                    if test_google_search_api(google_search_api_key, google_cx_id):
                        print("✅ Google Search API is working!")
                    else:
                        print("❌ Google Search API is not working. Check your API key and CX ID.")
            else:
                print("Google Custom Search Engine ID skipped.")

        except KeyboardInterrupt:
            print("\nSetup cancelled.")
            return False
    else:
        print("\nGoogle Custom Search Engine ID found in environment variables.")

        # Test the Google Search API if both keys are available
        if test_apis and google_search_api_key:
            print("Testing Google Search API...")
            if test_google_search_api(google_search_api_key, google_cx_id):
                print("✅ Google Search API is working!")
            else:
                print("❌ Google Search API is not working. Check your API key and CX ID.")

    # Check if we have at least one API key
    if not (gemini_api_key or (google_search_api_key and google_cx_id)):
        print("\nWarning: No API keys provided. Some functionality may be limited.")

    print("\nEnvironment setup complete.")
    return True


def check_dependencies():
    """
    Check if all required dependencies are installed.

    Returns:
        bool: True if all dependencies are installed, False otherwise.
    """
    # Only check for the packages we actually need for the setup script
    required_packages = [
        "requests"
    ]

    # Optional packages for testing APIs
    optional_packages = [
        "google.generativeai"
    ]

    missing_required = []
    missing_optional = []

    # Check required packages
    for package in required_packages:
        try:
            if "." in package:
                # For packages with submodules
                main_package = package.split(".")[0]
                __import__(main_package)
                # Try to import the specific submodule
                try:
                    __import__(package)
                except ImportError:
                    missing_required.append(package)
            else:
                __import__(package)
        except ImportError:
            missing_required.append(package)

    # Check optional packages
    for package in optional_packages:
        try:
            if "." in package:
                # For packages with submodules
                main_package = package.split(".")[0]
                __import__(main_package)
                # Try to import the specific submodule
                try:
                    __import__(package)
                except ImportError:
                    missing_optional.append(package)
            else:
                __import__(package)
        except ImportError:
            missing_optional.append(package)

    # Report missing required packages
    if missing_required:
        print("\n=== Missing Required Dependencies ===")
        print("The following required packages are not installed:")
        for package in missing_required:
            print(f"- {package}")

        print("\nYou can install them with:")
        print(f"pip install {' '.join(missing_required)}")
        return False

    # Report missing optional packages
    if missing_optional:
        print("\n=== Missing Optional Dependencies ===")
        print("The following optional packages are not installed:")
        for package in missing_optional:
            print(f"- {package}")

        print("\nSome functionality may be limited. You can install them with:")
        print(f"pip install {' '.join(missing_optional)}")
        print("\nContinuing with setup...")

    return True


def save_api_keys_to_file(filename=".env"):
    """
    Save the API keys to a .env file for future use.

    Args:
        filename: The name of the file to save the API keys to.

    Returns:
        bool: True if the API keys were saved successfully, False otherwise.
    """
    try:
        with open(filename, "w") as f:
            if os.environ.get("GEMINI_API_KEY"):
                f.write(f"GEMINI_API_KEY={os.environ.get('GEMINI_API_KEY')}\n")
            if os.environ.get("GOOGLE_SEARCH_API_KEY"):
                f.write(f"GOOGLE_SEARCH_API_KEY={os.environ.get('GOOGLE_SEARCH_API_KEY')}\n")
            if os.environ.get("GOOGLE_CX_ID"):
                f.write(f"GOOGLE_CX_ID={os.environ.get('GOOGLE_CX_ID')}\n")
        print(f"\nAPI keys saved to {filename}")
        print(f"In the future, you can load these keys with: source {filename}")
        return True
    except Exception as e:
        print(f"Error saving API keys to file: {e}")
        return False


if __name__ == "__main__":
    # Check dependencies
    if not check_dependencies():
        print("\nPlease install the missing dependencies and run this script again.")
        sys.exit(1)

    # Set up environment
    if setup_environment(test_apis=True):
        print("\nEnvironment setup complete. You can now use the Startup Intelligence Finder.")

        # Ask if the user wants to save the API keys to a file
        save_keys = input("\nWould you like to save your API keys to a .env file for future use? (y/n): ")
        if save_keys.lower() == "y":
            save_api_keys_to_file()
    else:
        print("\nEnvironment setup failed. Please try again.")
        sys.exit(1)
