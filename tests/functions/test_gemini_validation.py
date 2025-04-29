#!/usr/bin/env python3
"""
Test for Gemini validation batch size in the Startup Finder.

This script tests the Gemini validation batch size by creating sample startup data
and validating it with different batch sizes.
"""

import time
import os
import sys
import json
from typing import List, Dict, Any

# Add the parent directory to the path so we can import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import setup_env to ensure API keys are available
import setup_env

# Import the modules we want to test
from src.utils.api_client import GeminiAPIClient

def validate_batch(batch, query, batch_size):
    """
    Validate a batch of startup data using Gemini Pro.
    
    Args:
        batch: List of startup dictionaries to validate
        query: The original search query
        batch_size: Size of the batch
        
    Returns:
        Tuple of (validated_data, elapsed_time)
    """
    # Initialize Gemini API client
    gemini_client = GeminiAPIClient()
    pro_model = gemini_client.pro_model
    
    # Convert batch to JSON for the prompt
    batch_json = json.dumps(batch, indent=2)
    
    # Create a prompt for Gemini Pro
    prompt = f"""
    You are a data validation expert for startup company information. I have a dataset of startups related to the query: "{query}".

    Please analyze the following startup data for anomalies, inconsistencies, or missing information, and provide a corrected version.
    
    IMPORTANT: Use the search tool extensively to verify company information. For EACH company, perform multiple searches to verify:
    - Company existence and correct name spelling (search for the company name)
    - Founded year (search for "when was [company] founded")
    - Location (search for "[company] headquarters location")
    - Industry classification (search for "[company] industry sector")
    
    For each company, perform at least 2-3 different searches to thoroughly verify the information.
    
    Here's the data to validate and correct:
    {batch_json}
    
    Return ONLY the corrected data in valid JSON format, with the same structure as the input.
    Do not include any explanations or notes outside the JSON structure.
    """
    
    # Measure the time it takes to validate
    start_time = time.time()
    
    # Get response from Gemini Pro with search grounding
    response = pro_model.generate_content(prompt)
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    # Extract the corrected data
    try:
        # Find JSON in the response
        response_text = response.text
        
        # Extract JSON content (assuming it's the entire response or contained within triple backticks)
        if "```json" in response_text:
            json_content = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            json_content = response_text.split("```")[1].strip()
        else:
            json_content = response_text.strip()
        
        # Parse the JSON
        corrected_batch = json.loads(json_content)
        
        return corrected_batch, elapsed_time
    except Exception as e:
        print(f"Error parsing Gemini Pro response: {e}")
        return None, elapsed_time

def test_gemini_validation_batch_size():
    """
    Test the Gemini validation batch size.
    """
    print("\n" + "=" * 80)
    print("TESTING GEMINI VALIDATION BATCH SIZE")
    print("=" * 80)
    
    # Ensure environment variables are loaded
    setup_env.setup_environment()
    
    # Create sample startup data
    sample_data = [
        {
            "Company Name": "Carbon Clean",
            "Website": "https://carbonclean.com",
            "Location": "London, UK",
            "Industry": "Carbon Capture"
        },
        {
            "Company Name": "Climeworks",
            "Website": "https://climeworks.com",
            "Location": "Zurich, Switzerland",
            "Industry": "Direct Air Capture"
        },
        {
            "Company Name": "Charm Industrial",
            "Website": "https://charmindustrial.com",
            "Location": "San Francisco, USA",
            "Industry": "Bio-oil Carbon Removal"
        },
        {
            "Company Name": "Heirloom Carbon",
            "Website": "https://heirloomcarbon.com",
            "Location": "California, USA",
            "Industry": "Direct Air Capture"
        },
        {
            "Company Name": "Verdox",
            "Website": "https://verdox.com",
            "Location": "Massachusetts, USA",
            "Industry": "Carbon Capture"
        },
        {
            "Company Name": "Mission Zero Technologies",
            "Website": "https://missionzero.tech",
            "Location": "London, UK",
            "Industry": "Carbon Capture"
        },
        {
            "Company Name": "Twelve",
            "Website": "https://twelve.co",
            "Location": "California, USA",
            "Industry": "Carbon Transformation"
        },
        {
            "Company Name": "Remora",
            "Website": "https://remoracarbon.com",
            "Location": "Michigan, USA",
            "Industry": "Carbon Capture for Trucks"
        },
        {
            "Company Name": "Captura",
            "Website": "https://capturacorp.com",
            "Location": "California, USA",
            "Industry": "Ocean-based Carbon Removal"
        },
        {
            "Company Name": "Carbfix",
            "Website": "https://carbfix.com",
            "Location": "Reykjavik, Iceland",
            "Industry": "Carbon Mineralization"
        }
    ]
    
    # Test with different batch sizes
    batch_sizes = [2, 5, 10]
    query = "decarbonisation startups"
    
    for batch_size in batch_sizes:
        print(f"\nTesting with batch size {batch_size}...")
        
        # Process a batch of the specified size
        batch = sample_data[:batch_size]
        
        # Validate the batch
        corrected_batch, elapsed_time = validate_batch(batch, query, batch_size)
        
        print(f"Validated {batch_size} startups in {elapsed_time:.2f} seconds")
        print(f"Average time per startup: {elapsed_time / batch_size:.2f} seconds")
        
        if corrected_batch:
            # Print the number of fields found for each startup
            for startup in corrected_batch:
                company_name = startup.get("Company Name", "Unknown")
                field_count = len(startup)
                print(f"  {company_name}: {field_count} fields found")
        else:
            print("  Error: Could not parse the response")
    
    print("\nGemini validation batch size test completed.")

if __name__ == "__main__":
    test_gemini_validation_batch_size()
