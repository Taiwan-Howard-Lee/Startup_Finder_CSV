"""
Script to check if the Gemini API key is valid.
"""

import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import setup_env

# Set up the environment
setup_env.setup_environment()

try:
    # Import the Google Generative AI library
    import google.generativeai as genai

    # Get the API key from environment variables
    api_key = os.environ.get('GEMINI_API_KEY')

    if not api_key:
        print("Error: GEMINI_API_KEY environment variable is not set.")
        sys.exit(1)

    # Configure the Gemini API
    genai.configure(api_key=api_key)

    # Try to use a model
    print(f"Testing API key: {api_key[:5]}...{api_key[-5:]}")

    # Try with gemini-1.5-flash
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content('Hello, are you working?')
        print("\ngemini-1.5-flash test:")
        print(f"Response: {response.text}")
        print("✅ API key is valid for gemini-1.5-flash")
    except Exception as e:
        print(f"❌ Error with gemini-1.5-flash: {e}")

    # Try with gemini-1.5-pro
    try:
        model = genai.GenerativeModel('gemini-1.5-pro')
        response = model.generate_content('Hello, are you working?')
        print("\ngemini-1.5-pro test:")
        print(f"Response: {response.text}")
        print("✅ API key is valid for gemini-1.5-pro")
    except Exception as e:
        print(f"❌ Error with gemini-1.5-pro: {e}")

    # Try with gemini-2.0-flash-lite
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-lite')
        response = model.generate_content('Hello, are you working?')
        print("\ngemini-2.0-flash-lite test:")
        print(f"Response: {response.text}")
        print("✅ API key is valid for gemini-2.0-flash-lite")
    except Exception as e:
        print(f"❌ Error with gemini-2.0-flash-lite: {e}")

    # Try with gemini-2.0-pro
    try:
        model = genai.GenerativeModel('gemini-2.0-pro')
        response = model.generate_content('Hello, are you working?')
        print("\ngemini-2.0-pro test:")
        print(f"Response: {response.text}")
        print("✅ API key is valid for gemini-2.0-pro")
    except Exception as e:
        print(f"❌ Error with gemini-2.0-pro: {e}")

except ImportError:
    print("Error: google-generativeai package is not installed.")
    print("Install it with: pip install google-generativeai")
    sys.exit(1)
except Exception as e:
    print(f"Unexpected error: {e}")
    sys.exit(1)
