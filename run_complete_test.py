"""
Complete test script for the Startup Intelligence Finder.

This script runs a complete test of the startup crawler with LLM-based filtering:
1. Allows the user to enter any search query
2. Discovers startup names using the two-phase approach
3. Uses the Gemini Pro model to filter out non-startup names
4. Enriches the data for discovered startups
5. Saves the results to JSON files
"""

import os
import sys
import json
import time
from typing import Dict, Any, List

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import setup_env to ensure API keys are available
import setup_env

from src.processor.crawler import StartupCrawler


def load_env_from_file():
    """Load environment variables from .env file."""
    try:
        with open(".env", "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                    
                key, value = line.split("=", 1)
                os.environ[key] = value
                
        print(f"Loaded API keys from .env file")
    except Exception as e:
        print(f"Error loading environment variables: {e}")


def pretty_print_startup_list(startup_list: List[Dict[str, Any]]):
    """
    Pretty print a list of startups.
    
    Args:
        startup_list: List of startup dictionaries.
    """
    print("\n" + "=" * 80)
    print(f"DISCOVERED STARTUPS ({len(startup_list)})")
    print("=" * 80)
    
    for i, startup in enumerate(startup_list, 1):
        print(f"{i}. {startup.get('Company Name', 'Unknown')}")
        
        # Print where it was found
        if "Found In" in startup:
            print(f"   - Found in: {startup['Found In']}")
        
        # Print original URL
        if "Original URL" in startup:
            print(f"   - Source URL: {startup['Original URL']}")
        
        # Print basic info if available
        for field in ["Website", "Location", "Founded Year"]:
            if field in startup and startup[field]:
                print(f"   - {field}: {startup[field]}")
        
        print("-" * 80)


def pretty_print_enriched_data(enriched_data: List[Dict[str, Any]]):
    """
    Pretty print enriched startup data.
    
    Args:
        enriched_data: List of enriched startup dictionaries.
    """
    print("\n" + "=" * 80)
    print(f"ENRICHED STARTUP DATA ({len(enriched_data)})")
    print("=" * 80)
    
    for i, startup in enumerate(enriched_data, 1):
        print(f"{i}. {startup.get('Company Name', 'Unknown')}")
        
        # Print all available fields
        for field, value in startup.items():
            if field != "Company Name":
                # Format the value for display
                if isinstance(value, str) and len(value) > 100:
                    value = value[:97] + "..."
                print(f"   - {field}: {value}")
        
        print("-" * 80)


def save_results_to_file(data: List[Dict[str, Any]], filename: str):
    """
    Save results to a JSON file with a timestamp.
    
    Args:
        data: Data to save.
        filename: Base filename.
    
    Returns:
        Full filename with timestamp.
    """
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    full_filename = f"{filename}_{timestamp}.json"
    
    try:
        with open(full_filename, "w") as f:
            json.dump(data, f, indent=2)
        print(f"Results saved to {full_filename}")
        return full_filename
    except Exception as e:
        print(f"Error saving results: {e}")
        return None


def run_complete_test():
    """Run a complete test of the startup crawler with LLM-based filtering."""
    print("\n" + "=" * 80)
    print("STARTUP INTELLIGENCE FINDER - COMPLETE TEST")
    print("=" * 80)
    
    # Load environment variables from .env file
    load_env_from_file()
    
    # Ensure environment is set up
    setup_env.setup_environment(test_apis=False)
    
    # Get search query from user
    print("\nEnter a search query to find startups. Examples:")
    print("- top ai startups 2024")
    print("- fintech startups in singapore")
    print("- healthcare ai companies")
    print("- cybersecurity startups")
    query = input("\nYour search query: ").strip()
    
    if not query:
        print("No query provided. Exiting.")
        return
    
    # Get number of results from user
    try:
        max_results = int(input("\nMaximum number of search results to process (1-10, default: 5): ").strip() or "5")
        max_results = max(1, min(10, max_results))  # Ensure between 1 and 10
    except ValueError:
        print("Invalid input. Using default value of 5.")
        max_results = 5
    
    # Create a crawler
    crawler = StartupCrawler()
    
    # Phase 1: Discover startup names with LLM filtering
    print("\n" + "=" * 80)
    print("PHASE 1: STARTUP DISCOVERY WITH LLM FILTERING")
    print("=" * 80)
    print(f"Searching for: {query}")
    print(f"Processing up to {max_results} search results")
    print("This may take a few minutes...")
    
    start_time = time.time()
    startup_info_list = crawler.discover_startups(query, max_results=max_results)
    phase1_time = time.time() - start_time
    
    # Display the intermediate results
    pretty_print_startup_list(startup_info_list)
    
    # Save the intermediate results to a file
    discovery_filename = save_results_to_file(startup_info_list, "startup_discovery")
    
    print(f"\nPhase 1 completed in {phase1_time:.2f} seconds")
    print(f"Found {len(startup_info_list)} startups")
    
    if not startup_info_list:
        print("\nNo startups found. Exiting.")
        return
    
    # Ask user if they want to continue to Phase 2
    continue_to_phase2 = input("\nContinue to Phase 2 (Enrichment)? (y/n): ").strip().lower()
    if continue_to_phase2 != "y":
        print("Exiting after Phase 1.")
        return
    
    # Phase 2: Enrich startup data
    print("\n" + "=" * 80)
    print("PHASE 2: DATA ENRICHMENT")
    print("=" * 80)
    print(f"Enriching data for {len(startup_info_list)} startups")
    print("This may take a few minutes...")
    
    start_time = time.time()
    enriched_results = crawler.enrich_startup_data(startup_info_list)
    phase2_time = time.time() - start_time
    
    # Display the enriched results
    pretty_print_enriched_data(enriched_results)
    
    # Save the final results to a file
    enriched_filename = save_results_to_file(enriched_results, "enriched_startups")
    
    print(f"\nPhase 2 completed in {phase2_time:.2f} seconds")
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Search query: {query}")
    print(f"Phase 1 (Discovery) time: {phase1_time:.2f} seconds")
    print(f"Phase 2 (Enrichment) time: {phase2_time:.2f} seconds")
    print(f"Total time: {phase1_time + phase2_time:.2f} seconds")
    print(f"Startups found: {len(startup_info_list)}")
    print(f"Discovery results saved to: {discovery_filename}")
    print(f"Enriched results saved to: {enriched_filename}")
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    run_complete_test()
