#!/usr/bin/env python3
"""
Example script demonstrating how to use search grounding with Gemini Pro.

This script shows how to use the search grounding capability of Gemini Pro
to retrieve real-time information from the web.
"""

import os
import sys
import time

# Add the parent directory to the path so we can import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import setup_env to ensure API keys are available
import setup_env

# Import the necessary modules
from src.utils.api_client import GeminiAPIClient
from google.generativeai import types

def search_grounding_example():
    """
    Example of using search grounding with Gemini Pro.
    """
    print("\n" + "=" * 80)
    print("SEARCH GROUNDING EXAMPLE")
    print("=" * 80)
    
    # Ensure environment variables are loaded
    setup_env.setup_environment()
    
    # Initialize Gemini API client
    gemini_client = GeminiAPIClient()
    pro_model = gemini_client.pro_model
    
    # Create a prompt that requires real-time information
    prompt = """
    What are the latest developments in nature-based solutions for carbon capture?
    Focus on recent startups and innovations in this space.
    Include specific examples of companies working on this technology.
    """
    
    print("\nPrompt:")
    print(prompt)
    
    # Record the start time
    start_time = time.time()
    
    # Configure the generation to use search grounding
    generation_config = types.GenerateContentConfig(
        tools=[types.Tool(google_search=types.GoogleSearch())],
        response_mime_type="text/plain",
    )
    
    # Generate content with search grounding
    print("\nGenerating response with search grounding...")
    response = pro_model.generate_content(
        prompt,
        generation_config=generation_config
    )
    
    # Record the end time
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    # Print the response
    print("\nResponse from Gemini Pro with search grounding:")
    print("-" * 80)
    print(response.text)
    print("-" * 80)
    
    print(f"\nResponse generated in {elapsed_time:.2f} seconds")
    
    print("\nSearch grounding example completed.")

if __name__ == "__main__":
    search_grounding_example()
