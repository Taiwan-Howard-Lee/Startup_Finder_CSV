"""
Test script specifically for finding decarbonisation startups in the UK.
"""

import os
import time
import logging
import sys
import json
from typing import Dict, List, Any

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.processor.crawler import StartupCrawler

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_uk_decarbonisation_startups():
    """Test finding decarbonisation startups in the UK with enhanced crawler."""
    # Check if API keys are set
    if not os.environ.get("GOOGLE_SEARCH_API_KEY") or not os.environ.get("GOOGLE_CX_ID"):
        logger.error("Please set GOOGLE_SEARCH_API_KEY and GOOGLE_CX_ID environment variables")
        return None
    
    # Create a crawler with parallel processing
    crawler = StartupCrawler(max_workers=5)
    
    # Test queries - using multiple variations to improve results
    queries = [
        "decarbonisation startups in UK",
        "carbon capture startups in United Kingdom",
        "net zero startups UK",
        "climate tech startups in Britain"
    ]
    
    all_startups = []
    
    # Process each query
    for query in queries:
        logger.info(f"Processing query: {query}")
        
        # Measure time
        start_time = time.time()
        
        # Phase 1: Discover startups
        logger.info(f"Phase 1: Discovering startups for query: {query}")
        startup_info_list = crawler.discover_startups(query, max_results=5)
        
        logger.info(f"Found {len(startup_info_list)} startups in discovery phase")
        for startup in startup_info_list:
            logger.info(f"  {startup.get('Company Name', 'Unknown')}")
        
        # Phase 2: Enrich startup data
        if startup_info_list:
            logger.info(f"Phase 2: Enriching data for {len(startup_info_list)} startups")
            enriched_startups = crawler.enrich_startup_data(startup_info_list, max_results_per_startup=3)
            
            # Log results
            logger.info(f"Enriched {len(enriched_startups)} startups")
            for startup in enriched_startups:
                logger.info(f"Startup: {startup.get('Company Name', 'Unknown')}")
                for key, value in startup.items():
                    if key != "Company Name":
                        logger.info(f"  {key}: {value}")
                
                # Add to all startups list
                all_startups.append(startup)
        
        # Calculate elapsed time
        elapsed_time = time.time() - start_time
        logger.info(f"Query processed in {elapsed_time:.2f} seconds")
    
    # Remove duplicates based on company name
    unique_startups = []
    seen_names = set()
    
    for startup in all_startups:
        name = startup.get("Company Name", "").lower()
        if name and name not in seen_names:
            seen_names.add(name)
            unique_startups.append(startup)
    
    logger.info(f"Found {len(unique_startups)} unique startups across all queries")
    
    # Save results to a JSON file
    output_file = os.path.join("data", "uk_decarbonisation_startups.json")
    with open(output_file, "w") as f:
        json.dump(unique_startups, f, indent=2)
    
    logger.info(f"Results saved to {output_file}")
    
    # Generate CSV file
    generate_csv_from_results(unique_startups)
    
    return unique_startups

def generate_csv_from_results(startups: List[Dict[str, Any]]):
    """Generate a CSV file from the results."""
    import csv
    
    # Define CSV columns
    columns = [
        "Company Name", "Website", "LinkedIn", "Location", "Founded Year", 
        "Industry", "Company Size", "Funding", "Product Description", 
        "Products/Services", "Team", "Contact", "Source"
    ]
    
    # Create CSV file
    output_file = os.path.join("data", "uk_decarbonisation_startups.csv")
    with open(output_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        
        # Write each startup to the CSV
        for startup in startups:
            # Create a row with all columns
            row = {col: "" for col in columns}
            
            # Fill in the data we have
            for key, value in startup.items():
                if key in columns:
                    row[key] = value
            
            # Write the row
            writer.writerow(row)
    
    logger.info(f"CSV file generated: {output_file}")
    
    return output_file

if __name__ == "__main__":
    # Run the test
    logger.info("Starting UK decarbonisation startups test")
    startups = test_uk_decarbonisation_startups()
    
    if startups:
        logger.info(f"Test completed successfully with {len(startups)} startups found")
    else:
        logger.error("Test failed")
