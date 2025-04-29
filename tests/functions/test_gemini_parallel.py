#!/usr/bin/env python3
"""
Test for parallel processing of Gemini API calls.

This script tests the parallel processing capabilities for Gemini API calls
by comparing the performance of sequential vs. parallel query expansion.
"""

import time
import os
import sys
import logging
from typing import List, Dict, Any

# Add the parent directory to the path so we can import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Import setup_env to ensure API keys are available
import setup_env

# Import the modules we want to test
from src.collector.query_expander import QueryExpander
from src.utils.api_client import GeminiAPIClient
from src.utils.batch_processor import GeminiAPIBatchProcessor

def test_sequential_vs_parallel_query_expansion():
    """
    Test the performance difference between sequential and parallel query expansion.
    """
    print("\n" + "=" * 80)
    print("TESTING SEQUENTIAL VS PARALLEL QUERY EXPANSION")
    print("=" * 80)
    
    # Ensure environment variables are loaded
    setup_env.setup_environment()
    
    # Initialize the API client and query expander
    gemini_client = GeminiAPIClient()
    query_expander = QueryExpander(api_client=gemini_client)
    
    # Test queries
    queries = [
        "AI startups in healthcare",
        "Fintech companies in Singapore",
        "Renewable energy startups in Europe",
        "Cybersecurity companies in London",
        "Biotech startups in Boston"
    ]
    
    # Number of expansions to generate
    num_expansions = 10
    
    # Test sequential expansion
    print("\nTesting sequential query expansion...")
    sequential_start_time = time.time()
    
    sequential_results = {}
    for query in queries:
        print(f"\nExpanding query: {query}")
        expansions = query_expander.expand_query(query, num_expansions=num_expansions)
        sequential_results[query] = expansions
        print(f"Generated {len(expansions)-1} expansions")
    
    sequential_end_time = time.time()
    sequential_elapsed_time = sequential_end_time - sequential_start_time
    
    print(f"\nSequential expansion completed in {sequential_elapsed_time:.2f} seconds")
    print(f"Average time per query: {sequential_elapsed_time / len(queries):.2f} seconds")
    
    # Test parallel expansion using batch processor directly
    print("\nTesting parallel query expansion using batch processor...")
    parallel_start_time = time.time()
    
    # Define the processing function
    def process_query(api_client, query, num_expansions):
        return {
            "query": query,
            "expansions": query_expander.expand_query(query, num_expansions=num_expansions)
        }
    
    # Create batch processor
    batch_processor = GeminiAPIBatchProcessor(max_workers=30)
    
    # Process the batch
    batch_results = batch_processor.process_batch(
        gemini_client, queries, process_query, num_expansions
    )
    
    # Convert to dictionary
    parallel_results = {}
    for result in batch_results:
        if isinstance(result, dict) and "query" in result and "expansions" in result:
            parallel_results[result["query"]] = result["expansions"]
    
    parallel_end_time = time.time()
    parallel_elapsed_time = parallel_end_time - parallel_start_time
    
    print(f"\nParallel expansion completed in {parallel_elapsed_time:.2f} seconds")
    print(f"Average time per query: {parallel_elapsed_time / len(queries):.2f} seconds")
    
    # Test parallel expansion using the new expand_queries_batch method
    print("\nTesting parallel query expansion using expand_queries_batch method...")
    batch_start_time = time.time()
    
    batch_results = gemini_client.expand_queries_batch(queries, num_expansions=num_expansions)
    
    batch_end_time = time.time()
    batch_elapsed_time = batch_end_time - batch_start_time
    
    print(f"\nBatch expansion completed in {batch_elapsed_time:.2f} seconds")
    print(f"Average time per query: {batch_elapsed_time / len(queries):.2f} seconds")
    
    # Test parallel expansion using the new expand_query_parallel method
    print("\nTesting parallel query expansion using expand_query_parallel method...")
    parallel_method_start_time = time.time()
    
    parallel_method_results = {}
    for query in queries:
        print(f"\nExpanding query: {query}")
        expansions = query_expander.expand_query_parallel(query, num_expansions=num_expansions)
        parallel_method_results[query] = expansions
        print(f"Generated {len(expansions)-1} expansions")
    
    parallel_method_end_time = time.time()
    parallel_method_elapsed_time = parallel_method_end_time - parallel_method_start_time
    
    print(f"\nParallel method expansion completed in {parallel_method_elapsed_time:.2f} seconds")
    print(f"Average time per query: {parallel_method_elapsed_time / len(queries):.2f} seconds")
    
    # Compare results
    print("\nPerformance comparison:")
    print(f"Sequential: {sequential_elapsed_time:.2f} seconds")
    print(f"Parallel (batch processor): {parallel_elapsed_time:.2f} seconds")
    print(f"Parallel (expand_queries_batch): {batch_elapsed_time:.2f} seconds")
    print(f"Parallel (expand_query_parallel): {parallel_method_elapsed_time:.2f} seconds")
    
    # Calculate speedup
    sequential_batch_speedup = sequential_elapsed_time / batch_elapsed_time
    print(f"\nSpeedup using batch processing: {sequential_batch_speedup:.2f}x")
    
    print("\nParallel processing test completed.")

def test_validate_startups_batch():
    """
    Test the validate_startups_batch method.
    """
    print("\n" + "=" * 80)
    print("TESTING VALIDATE STARTUPS BATCH")
    print("=" * 80)
    
    # Ensure environment variables are loaded
    setup_env.setup_environment()
    
    # Initialize the API client
    gemini_client = GeminiAPIClient()
    
    # Create sample startup data
    startups = [
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
            "Industry": "Enhanced Mineralization"
        },
        {
            "Company Name": "Verdox",
            "Website": "https://verdox.com",
            "Location": "Massachusetts, USA",
            "Industry": "Electrochemical Carbon Capture"
        }
    ]
    
    # Test sequential validation
    print("\nTesting sequential validation...")
    sequential_start_time = time.time()
    
    sequential_results = []
    for startup in startups:
        print(f"\nValidating: {startup['Company Name']}")
        # Create a prompt for Gemini Pro
        prompt = f"""
        You are a data validation expert for startup company information.
        
        Please analyze the following startup data for anomalies, inconsistencies, or missing information, and provide a corrected version.
        
        {startup}
        
        Return ONLY the corrected data in valid JSON format, with the same structure as the input.
        """
        
        # Get response from Gemini Pro
        response = gemini_client.pro_model.generate_content(prompt)
        
        # Extract JSON from response
        try:
            # Find JSON in the response
            response_text = response.text
            if "```json" in response_text:
                json_content = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                json_content = response_text.split("```")[1].strip()
            else:
                json_content = response_text.strip()
                
            # Parse the JSON
            import json
            validated_startup = json.loads(json_content)
            sequential_results.append(validated_startup)
        except Exception as e:
            print(f"Error parsing response: {e}")
            sequential_results.append(startup)  # Use original on error
    
    sequential_end_time = time.time()
    sequential_elapsed_time = sequential_end_time - sequential_start_time
    
    print(f"\nSequential validation completed in {sequential_elapsed_time:.2f} seconds")
    print(f"Average time per startup: {sequential_elapsed_time / len(startups):.2f} seconds")
    
    # Test parallel validation
    print("\nTesting parallel validation...")
    parallel_start_time = time.time()
    
    # Use the validate_startups_batch method
    query = "carbon capture startups"
    parallel_results = gemini_client.validate_startups_batch(startups, query)
    
    parallel_end_time = time.time()
    parallel_elapsed_time = parallel_end_time - parallel_start_time
    
    print(f"\nParallel validation completed in {parallel_elapsed_time:.2f} seconds")
    print(f"Average time per startup: {parallel_elapsed_time / len(startups):.2f} seconds")
    
    # Compare results
    print("\nPerformance comparison:")
    print(f"Sequential: {sequential_elapsed_time:.2f} seconds")
    print(f"Parallel: {parallel_elapsed_time:.2f} seconds")
    
    # Calculate speedup
    speedup = sequential_elapsed_time / parallel_elapsed_time
    print(f"\nSpeedup using parallel processing: {speedup:.2f}x")
    
    print("\nValidation test completed.")

if __name__ == "__main__":
    test_sequential_vs_parallel_query_expansion()
    test_validate_startups_batch()
