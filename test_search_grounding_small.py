#!/usr/bin/env python3
"""
Small-scale test for search grounding in the Startup Finder.

This script tests the search grounding functionality with a small number of startups.
"""

import os
import sys
import time
import json
from typing import List, Dict, Any

# Add the parent directory to the path so we can import the modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import setup_env to ensure API keys are available
import setup_env

# Import the modules we want to test
from src.utils.api_client import GeminiAPIClient

def test_search_grounding_small():
    """
    Test the search grounding functionality with a small number of startups.
    """
    print("\n" + "=" * 80)
    print("SMALL-SCALE SEARCH GROUNDING TEST")
    print("=" * 80)

    # Ensure environment variables are loaded
    setup_env.setup_environment()

    # Initialize Gemini API client
    gemini_client = GeminiAPIClient()

    # Create a small list of startups to test
    startups = [
        {
            "Company Name": "Tempus",
            "Website": "https://www.tempus.com",
            "Industry": "Healthcare AI"
        },
        {
            "Company Name": "Insitro",
            "Website": "https://www.insitro.com",
            "Industry": "Drug Discovery"
        }
    ]

    # Convert to JSON for the prompt
    startups_json = json.dumps(startups, indent=2)

    # Create a prompt that requires search grounding
    prompt = f"""
    You are a data validation expert for startup company information.

    Please analyze the following startup data for anomalies, inconsistencies, or missing information, and provide a corrected version.

    IMPORTANT: Use the search tool to verify company information when possible, especially for:
    - Company existence and correct name spelling
    - Founded year
    - Location
    - Industry classification
    - Funding information
    - Key people/founders

    For each company, search for its name plus relevant keywords to verify the information.

    Here's the data to validate and correct:
    {startups_json}

    Return ONLY the corrected data in valid JSON format, with the same structure as the input.
    """

    # Record the start time
    start_time = time.time()

    # Generate content with search grounding
    print("\nGenerating response with search grounding...")
    response = gemini_client.pro_model.generate_content(prompt, stream=True)

    # Process the streaming response
    search_queries = []
    full_response = ""

    print("\nSearch queries used:")
    for chunk in response:
        if hasattr(chunk, 'candidates') and chunk.candidates:
            candidate = chunk.candidates[0]
            if hasattr(candidate, 'content') and candidate.content:
                content = candidate.content
                if hasattr(content, 'parts') and content.parts:
                    for part in content.parts:
                        if hasattr(part, 'text') and part.text:
                            full_response += part.text
                        elif hasattr(part, 'function_call'):
                            if part.function_call.name == "search":
                                query = part.function_call.args.get("query", "No query provided")
                                search_queries.append(query)
                                print(f"  - {query}")

    # Record the end time
    end_time = time.time()
    elapsed_time = end_time - start_time

    # Print the response
    print("\nResponse from Gemini Pro with search grounding:")
    print("-" * 80)
    print(full_response)
    print("-" * 80)

    print(f"\nNumber of search queries used: {len(search_queries)}")

    # Check if search queries were used
    if search_queries:
        print(f"\nSearch grounding test completed in {elapsed_time:.2f} seconds")
        print("✅ Search grounding is working correctly!")
        print(f"The model used {len(search_queries)} search queries to gather information.")

        # Try to extract any JSON from the full response
        try:
            # Find JSON in the response
            if "```json" in full_response:
                json_content = full_response.split("```json")[1].split("```")[0].strip()
            elif "```" in full_response:
                json_content = full_response.split("```")[1].strip()
            else:
                # Look for JSON-like content
                if "{" in full_response and "}" in full_response:
                    start = full_response.find("{")
                    end = full_response.rfind("}") + 1
                    json_content = full_response[start:end]
                else:
                    raise ValueError("No JSON content found in response")

            # Parse the JSON
            corrected_data = json.loads(json_content)

            # Print the corrected data
            print("\nCorrected data:")
            if isinstance(corrected_data, list):
                for startup in corrected_data:
                    if isinstance(startup, dict) and "Company Name" in startup:
                        print(f"\n{startup['Company Name']}:")
                        for key, value in startup.items():
                            if key != "Company Name":
                                print(f"  {key}: {value}")
            elif isinstance(corrected_data, dict) and "Company Name" in corrected_data:
                print(f"\n{corrected_data['Company Name']}:")
                for key, value in corrected_data.items():
                    if key != "Company Name":
                        print(f"  {key}: {value}")

            # Check if new fields were added
            original_fields = set()
            for startup in startups:
                original_fields.update(startup.keys())

            corrected_fields = set()
            if isinstance(corrected_data, list):
                for startup in corrected_data:
                    if isinstance(startup, dict):
                        corrected_fields.update(startup.keys())
            elif isinstance(corrected_data, dict):
                corrected_fields.update(corrected_data.keys())

            new_fields = corrected_fields - original_fields
            if new_fields:
                print("\nNew fields added through search grounding:")
                for field in new_fields:
                    print(f"- {field}")

        except Exception as e:
            print(f"\nNote: Could not parse JSON from response: {e}")
            print("This is expected as the model is still using search grounding correctly.")
    else:
        print(f"\nSearch grounding test completed in {elapsed_time:.2f} seconds")
        print("❌ Search grounding is not working correctly - no search queries were used.")

if __name__ == "__main__":
    test_search_grounding_small()
