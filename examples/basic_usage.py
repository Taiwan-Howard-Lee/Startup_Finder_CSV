"""
Basic usage examples for Startup Intelligence Finder.
"""

import os
import sys

# Add parent directory to path to import startup_finder
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Check if environment is set up
try:
    from setup_env import setup_environment, check_dependencies

    # Check dependencies
    if not check_dependencies():
        print("\nPlease install the missing dependencies before running this example.")
        sys.exit(1)

    # Set up environment if needed
    if not setup_environment():
        print("\nEnvironment setup failed. Please set up your environment before running this example.")
        sys.exit(1)
except ImportError:
    print("\nWarning: setup_env.py not found. Make sure you have set the GEMINI_API_KEY environment variable.")

from startup_finder import StartupFinder


def basic_search_example():
    """Basic search example."""
    print("=== Basic Search Example ===")

    # Initialize with mock data for testing
    finder = StartupFinder(use_mock_data=True)

    # Simple search
    results = finder.search(
        query="AI startups in healthcare",
        fields=["Founders", "Funding Information", "Technology Stack", "Product Description"]
    )

    # Display results
    print(f"Found {len(results)} results:")
    print(results.head())

    # Export to CSV
    csv_path = results.to_csv("healthcare_ai_startups.csv")
    print(f"Results exported to CSV: {csv_path}")


def advanced_search_example():
    """Advanced search with custom configuration."""
    print("\n=== Advanced Search Example ===")

    # Initialize with mock data for testing
    finder = StartupFinder(use_mock_data=True)

    # Custom configuration
    config = {
        "max_results": 10,
        "min_confidence": 0.7,
        "include_sources": True,
        "export_format": "json"
    }

    # Advanced search
    results = finder.search(
        query="sustainable energy startups with female founders",
        fields=["Founders", "Funding Information", "Technology Stack",
                "Product Description", "Business Model"],
        config=config
    )

    # Display results
    print(f"Found {len(results)} results:")
    print(results.head())

    # Export to JSON
    json_path = results.to_json("sustainable_energy_startups.json")
    print(f"Results exported to JSON: {json_path}")


def field_exploration_example():
    """Example showing available fields."""
    print("\n=== Field Exploration Example ===")

    # Initialize
    finder = StartupFinder(use_mock_data=True)

    # Get available fields
    available_fields = finder.get_available_fields()
    default_fields = finder.get_default_fields()

    print("Default search fields:")
    for field in default_fields:
        print(f"- {field}")

    print("\nAll available fields:")
    for field in available_fields:
        print(f"- {field}")


if __name__ == "__main__":
    # Run examples
    basic_search_example()
    advanced_search_example()
    field_exploration_example()
