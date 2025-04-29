#!/usr/bin/env python3
"""
Test for Search Grounding capacity in the Startup Finder.

This script tests the Search Grounding capacity by creating a sample startup
and validating it with Gemini Pro, tracking the number of search queries used.
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

def test_search_grounding_capacity():
    """
    Test the Search Grounding capacity of Gemini Pro.
    """
    print("\n" + "=" * 80)
    print("TESTING SEARCH GROUNDING CAPACITY")
    print("=" * 80)
    
    # Ensure environment variables are loaded
    setup_env.setup_environment()
    
    # Initialize Gemini API client
    gemini_client = GeminiAPIClient()
    pro_model = gemini_client.pro_model
    
    # Create a sample startup
    startup = {
        "Company Name": "Carbon Clean",
        "Website": "https://carbonclean.com",
        "Location": "London, UK",
        "Industry": "Carbon Capture"
    }
    
    # Convert to JSON for the prompt
    startup_json = json.dumps([startup], indent=2)
    
    # Create prompts with different levels of search instructions
    prompts = [
        # Basic prompt with minimal search instructions
        f"""
        You are a data validation expert for startup company information.
        
        Please analyze the following startup data for anomalies, inconsistencies, or missing information, and provide a corrected version.
        
        Use the search tool to verify company information when possible.
        
        Here's the data to validate and correct:
        {startup_json}
        
        Return ONLY the corrected data in valid JSON format, with the same structure as the input.
        """,
        
        # Enhanced prompt with moderate search instructions
        f"""
        You are a data validation expert for startup company information.
        
        Please analyze the following startup data for anomalies, inconsistencies, or missing information, and provide a corrected version.
        
        IMPORTANT: Use the search tool to verify company information when possible, especially for:
        - Company existence and correct name spelling
        - Founded year
        - Location
        - Industry classification
        
        For each company, search for its name plus relevant keywords to verify the information.
        
        Here's the data to validate and correct:
        {startup_json}
        
        Return ONLY the corrected data in valid JSON format, with the same structure as the input.
        """,
        
        # Maximized prompt with extensive search instructions
        f"""
        You are a data validation expert for startup company information.
        
        Please analyze the following startup data for anomalies, inconsistencies, or missing information, and provide a corrected version.
        
        IMPORTANT: Use the search tool extensively to verify company information. For EACH company, perform multiple searches to verify:
        - Company existence and correct name spelling (search for the company name)
        - Founded year (search for "when was [company] founded")
        - Location (search for "[company] headquarters location")
        - Industry classification (search for "[company] industry sector")
        - Funding information (search for "[company] funding rounds investment")
        - Key people/founders (search for "[company] founders CEO leadership team")
        - Company size (search for "[company] number of employees")
        - Products and services (search for "[company] products services offerings")
        
        For each company, perform at least 5-8 different searches to thoroughly verify all information. Be thorough and comprehensive in your verification.
        
        Here's the data to validate and correct:
        {startup_json}
        
        Return ONLY the corrected data in valid JSON format, with the same structure as the input.
        """
    ]
    
    for i, prompt in enumerate(prompts):
        print(f"\nTesting prompt {i+1} ({'Basic' if i == 0 else 'Enhanced' if i == 1 else 'Maximized'})...")
        
        # Measure the time it takes to validate
        start_time = time.time()
        
        # Get response from Gemini Pro with search grounding
        response = pro_model.generate_content(prompt, stream=True)
        
        # Process the streaming response
        search_queries = []
        full_response = ""
        
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
                                    print(f"  Search query: {query}")
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        print(f"Validation completed in {elapsed_time:.2f} seconds")
        print(f"Number of search queries used: {len(search_queries)}")
        
        # Try to extract the JSON from the response
        try:
            # Find JSON in the response
            if "```json" in full_response:
                json_content = full_response.split("```json")[1].split("```")[0].strip()
            elif "```" in full_response:
                json_content = full_response.split("```")[1].strip()
            else:
                json_content = full_response.strip()
            
            # Parse the JSON
            corrected_data = json.loads(json_content)
            
            # Print the number of fields found
            for startup in corrected_data:
                company_name = startup.get("Company Name", "Unknown")
                field_count = len(startup)
                print(f"  {company_name}: {field_count} fields found")
        except Exception as e:
            print(f"  Error parsing response: {e}")
    
    print("\nSearch Grounding capacity test completed.")

if __name__ == "__main__":
    test_search_grounding_capacity()
