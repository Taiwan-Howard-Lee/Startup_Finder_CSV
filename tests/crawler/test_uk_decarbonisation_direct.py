"""
Test script specifically for finding decarbonisation startups in the UK using direct extraction.
"""

import os
import time
import logging
import sys
import json
import re
from typing import Dict, List, Any

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.processor.crawler import StartupCrawler, WebCrawler

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def extract_startup_names_from_article(html_content, soup):
    """Extract startup names from article content."""
    startup_names = []
    
    # Look for common patterns in articles listing startups
    # Pattern 1: Company name followed by description
    company_patterns = [
        r'([A-Z][a-zA-Z0-9\-\s]+)(?:\s*[-–:]\s*|\s*is\s+a\s+|\s*,\s+a\s+)([^\.]+(?:startup|company|technology|solution|platform))',
        r'([A-Z][a-zA-Z0-9\-\s]+)(?:\s+was\s+founded\s+in\s+\d{4})',
        r'<h[2-4][^>]*>([A-Z][a-zA-Z0-9\-\s]+)</h[2-4]>',
        r'<strong>([A-Z][a-zA-Z0-9\-\s]+)</strong>'
    ]
    
    for pattern in company_patterns:
        matches = re.finditer(pattern, html_content, re.IGNORECASE)
        for match in matches:
            company_name = match.group(1).strip()
            # Filter out common non-company phrases
            if len(company_name) > 3 and not any(x in company_name.lower() for x in ['the ', 'and ', 'top ', 'best ', 'these ', 'some ', 'many ', 'most ']):
                if company_name not in startup_names:
                    startup_names.append(company_name)
    
    # Look for list items that might contain company names
    if soup:
        list_items = soup.find_all('li')
        for item in list_items:
            text = item.get_text().strip()
            # Check if the list item starts with a potential company name
            if text and text[0].isupper():
                # Extract the first part that might be a company name
                potential_name = text.split(':')[0].split(' - ')[0].split(',')[0].strip()
                if len(potential_name) > 3 and potential_name not in startup_names:
                    startup_names.append(potential_name)
    
    return startup_names

def test_uk_decarbonisation_startups_direct():
    """Test finding decarbonisation startups in the UK with direct extraction."""
    # Check if API keys are set
    if not os.environ.get("GOOGLE_SEARCH_API_KEY") or not os.environ.get("GOOGLE_CX_ID"):
        logger.error("Please set GOOGLE_SEARCH_API_KEY and GOOGLE_CX_ID environment variables")
        return None
    
    # Create a crawler with parallel processing
    crawler = StartupCrawler(max_workers=5)
    web_crawler = WebCrawler(max_workers=5)
    
    # Test queries - using multiple variations to improve results
    queries = [
        "list of decarbonisation startups in UK",
        "top carbon capture startups in United Kingdom",
        "best net zero startups UK 2023",
        "climate tech startups in Britain list"
    ]
    
    all_startup_names = []
    
    # Process each query
    for query in queries:
        logger.info(f"Processing query: {query}")
        
        # Measure time
        start_time = time.time()
        
        # Search for articles about UK decarbonisation startups
        logger.info(f"Searching for articles about: {query}")
        search_results = crawler.google_search.search(query, max_results=5)
        
        logger.info(f"Found {len(search_results)} search results")
        
        # Extract URLs to fetch
        urls_to_fetch = []
        for result in search_results:
            url = result.get("url", "")
            if url:
                urls_to_fetch.append(url)
        
        # Fetch webpages in parallel
        logger.info(f"Fetching {len(urls_to_fetch)} webpages")
        webpage_results = web_crawler.fetch_webpages_parallel(urls_to_fetch)
        
        # Extract startup names from each webpage
        startup_names_from_query = []
        for url, (raw_html, soup) in webpage_results.items():
            if not raw_html or not soup:
                continue
            
            logger.info(f"Extracting startup names from: {url}")
            startup_names = extract_startup_names_from_article(raw_html, soup)
            
            if startup_names:
                logger.info(f"Found {len(startup_names)} potential startup names")
                for name in startup_names:
                    logger.info(f"  {name}")
                startup_names_from_query.extend(startup_names)
        
        # Add to all startup names
        all_startup_names.extend(startup_names_from_query)
        
        # Calculate elapsed time
        elapsed_time = time.time() - start_time
        logger.info(f"Query processed in {elapsed_time:.2f} seconds")
    
    # Remove duplicates and filter out non-company names
    unique_startup_names = []
    seen_names = set()
    
    for name in all_startup_names:
        normalized_name = name.lower().strip()
        if normalized_name and normalized_name not in seen_names:
            seen_names.add(normalized_name)
            unique_startup_names.append(name)
    
    logger.info(f"Found {len(unique_startup_names)} unique startup names across all queries")
    
    # Enrich data for each startup
    enriched_startups = []
    if unique_startup_names:
        logger.info(f"Enriching data for {len(unique_startup_names)} startups")
        
        # Create startup info list
        startup_info_list = []
        for name in unique_startup_names:
            startup_info_list.append({"Company Name": name})
        
        # Enrich startup data
        enriched_startups = crawler.enrich_startup_data(startup_info_list, max_results_per_startup=3)
        
        # Log results
        logger.info(f"Enriched {len(enriched_startups)} startups")
        for startup in enriched_startups:
            logger.info(f"Startup: {startup.get('Company Name', 'Unknown')}")
            for key, value in startup.items():
                if key != "Company Name":
                    logger.info(f"  {key}: {value}")
    
    # Save results to a JSON file
    output_file = os.path.join("data", "uk_decarbonisation_startups_direct.json")
    with open(output_file, "w") as f:
        json.dump(enriched_startups, f, indent=2)
    
    logger.info(f"Results saved to {output_file}")
    
    # Generate CSV file
    generate_csv_from_results(enriched_startups)
    
    return enriched_startups

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
    output_file = os.path.join("data", "uk_decarbonisation_startups_direct.csv")
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
    logger.info("Starting UK decarbonisation startups direct extraction test")
    startups = test_uk_decarbonisation_startups_direct()
    
    if startups:
        logger.info(f"Test completed successfully with {len(startups)} startups found")
    else:
        logger.error("Test failed")
