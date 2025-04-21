"""
Startup Intelligence Finder - CSV Generator

This script runs the startup crawler and generates a CSV file with the results,
without storing any intermediate data.
"""

import os
import sys
import csv
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


def generate_csv_from_startups(enriched_data: List[Dict[str, Any]], output_file: str):
    """
    Generate a CSV file from the enriched startup data.
    
    Args:
        enriched_data: List of enriched startup dictionaries.
        output_file: Path to the output CSV file.
    """
    # Define the fields we want to include in the CSV
    fields = [
        "Company Name", 
        "Website", 
        "Location", 
        "Founded Year", 
        "Product Description", 
        "Source URL"
    ]
    
    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fields)
            
            # Write the header
            writer.writeheader()
            
            # Write the data
            for startup in enriched_data:
                # Create a row with only the fields we want
                row = {
                    "Company Name": startup.get("Company Name", ""),
                    "Website": startup.get("Website", ""),
                    "Location": startup.get("Location", ""),
                    "Founded Year": startup.get("Founded Year", ""),
                    "Product Description": startup.get("Product Description", ""),
                    "Source URL": startup.get("Original URL", "")
                }
                writer.writerow(row)
                
        print(f"CSV file generated: {output_file}")
        return True
    except Exception as e:
        print(f"Error generating CSV file: {e}")
        return False


def run_startup_finder():
    """Run the startup finder and generate a CSV file with the results."""
    print("\n" + "=" * 80)
    print("STARTUP INTELLIGENCE FINDER - CSV GENERATOR")
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
    
    # Get output file name
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    default_filename = f"startups_{timestamp}.csv"
    output_file = input(f"\nOutput CSV file name (default: {default_filename}): ").strip() or default_filename
    
    # Add .csv extension if not provided
    if not output_file.endswith('.csv'):
        output_file += '.csv'
    
    # Create a crawler
    crawler = StartupCrawler()
    
    # Phase 1: Discover startup names with LLM filtering
    print("\n" + "=" * 80)
    print("PHASE 1: STARTUP DISCOVERY")
    print("=" * 80)
    print(f"Searching for: {query}")
    print(f"Processing up to {max_results} search results")
    print("This may take a few minutes...")
    
    start_time = time.time()
    startup_info_list = crawler.discover_startups(query, max_results=max_results)
    phase1_time = time.time() - start_time
    
    print(f"\nPhase 1 completed in {phase1_time:.2f} seconds")
    print(f"Found {len(startup_info_list)} startups")
    
    if not startup_info_list:
        print("\nNo startups found. Exiting.")
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
    
    print(f"\nPhase 2 completed in {phase2_time:.2f} seconds")
    
    # Generate CSV file
    print("\n" + "=" * 80)
    print("GENERATING CSV FILE")
    print("=" * 80)
    
    success = generate_csv_from_startups(enriched_results, output_file)
    
    if success:
        # Summary
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Search query: {query}")
        print(f"Total time: {phase1_time + phase2_time:.2f} seconds")
        print(f"Startups found: {len(startup_info_list)}")
        print(f"CSV file generated: {output_file}")
    else:
        print("\nFailed to generate CSV file.")
    
    print("\n" + "=" * 80)
    print("PROCESS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    run_startup_finder()
