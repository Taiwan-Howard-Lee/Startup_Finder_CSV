"""
Test script for the improved crawler with LLM-based filtering.

This script demonstrates how the Gemini Pro model is used to filter
startup names based on relevance to the original query.
"""

import os
import sys
import json
from typing import Dict, Any, List

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

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
    print("\n" + "=" * 60)
    print(f"DISCOVERED STARTUPS ({len(startup_list)})")
    print("=" * 60)

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

        print("-" * 60)


def pretty_print_enriched_data(enriched_data: List[Dict[str, Any]]):
    """
    Pretty print enriched startup data.

    Args:
        enriched_data: List of enriched startup dictionaries.
    """
    print("\n" + "=" * 60)
    print(f"ENRICHED STARTUP DATA ({len(enriched_data)})")
    print("=" * 60)

    for i, startup in enumerate(enriched_data, 1):
        print(f"{i}. {startup.get('Company Name', 'Unknown')}")

        # Print all available fields
        for field, value in startup.items():
            if field != "Company Name":
                # Format the value for display
                if isinstance(value, str) and len(value) > 100:
                    value = value[:97] + "..."
                print(f"   - {field}: {value}")

        print("-" * 60)


def main():
    """Run a test of the improved crawler with LLM-based filtering."""
    # Load environment variables from .env file
    load_env_from_file()

    # Ensure environment is set up
    setup_env.setup_environment(test_apis=False)

    print("\n===== LLM FILTERING TEST =====")

    # Get search query from user
    query = input("\nEnter search query: ").strip()
    if not query:
        print("No query provided. Exiting.")
        return

    # Create a crawler
    crawler = StartupCrawler()

    # Phase 1: Discover startup names with LLM filtering
    print("\n===== PHASE 1: STARTUP DISCOVERY WITH LLM FILTERING =====")
    startup_info_list = crawler.discover_startups(query, max_results=5)

    # Display the intermediate results
    pretty_print_startup_list(startup_info_list)

    # Save the intermediate results to a file
    with open(os.path.join("data", "llm_filtered_startups.json"), "w") as f:
        json.dump(startup_info_list, f, indent=2)
    print(f"\nIntermediate results saved to llm_filtered_startups.json")

    # Ask user if they want to continue to Phase 2
    continue_to_phase2 = input("\nContinue to Phase 2 (Enrichment)? (y/n): ").strip().lower()
    if continue_to_phase2 != "y":
        print("Exiting after Phase 1.")
        return

    # Phase 2: Enrich startup data
    print("\n===== PHASE 2: DATA ENRICHMENT =====")
    enriched_results = crawler.enrich_startup_data(startup_info_list)

    # Display the enriched results
    pretty_print_enriched_data(enriched_results)

    # Save the final results to a file
    with open(os.path.join("data", "llm_filtered_enriched_data.json"), "w") as f:
        json.dump(enriched_results, f, indent=2)
    print(f"\nEnriched results saved to llm_filtered_enriched_data.json")

    print("\n===== LLM FILTERING TEST COMPLETE =====")


if __name__ == "__main__":
    main()
