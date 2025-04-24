"""
Complete test script for finding decarbonisation startups in the UK.
This script uses a more comprehensive approach to extract startup names from articles.
"""

import os
import time
import logging
import sys
import json
import csv
import re
from typing import Dict, List, Any
from bs4 import BeautifulSoup

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.processor.crawler import StartupCrawler, WebCrawler

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def extract_startup_names_from_html(html_content, soup):
    """Extract startup names from HTML content using various methods."""
    startup_names = []
    
    # Method 1: Look for company names in lists
    if soup:
        # Find all list items
        list_items = soup.find_all('li')
        for item in list_items:
            text = item.get_text().strip()
            # Check if the list item starts with a potential company name
            if text and text[0].isupper():
                # Extract the first part that might be a company name
                potential_name = text.split(':')[0].split(' - ')[0].split(',')[0].strip()
                if len(potential_name) > 3 and potential_name not in startup_names:
                    startup_names.append(potential_name)
        
        # Find all headings that might contain company names
        headings = soup.find_all(['h2', 'h3', 'h4'])
        for heading in headings:
            text = heading.get_text().strip()
            if text and text[0].isupper() and len(text) < 50:  # Avoid long headings
                potential_name = text.split(':')[0].split(' - ')[0].split(',')[0].strip()
                if len(potential_name) > 3 and potential_name not in startup_names:
                    startup_names.append(potential_name)
        
        # Find all bold text that might be company names
        bold_texts = soup.find_all(['strong', 'b'])
        for bold in bold_texts:
            text = bold.get_text().strip()
            if text and text[0].isupper() and len(text) < 50:
                potential_name = text.split(':')[0].split(' - ')[0].split(',')[0].strip()
                if len(potential_name) > 3 and potential_name not in startup_names:
                    startup_names.append(potential_name)
    
    # Method 2: Use regex patterns to find potential company names
    if html_content:
        # Pattern for company names followed by descriptions
        company_patterns = [
            r'([A-Z][a-zA-Z0-9\-\s]+)(?:\s*[-–:]\s*|\s*is\s+a\s+|\s*,\s+a\s+)([^\.]+(?:startup|company|technology|solution|platform|carbon|climate|energy))',
            r'([A-Z][a-zA-Z0-9\-\s]+)(?:\s+was\s+founded\s+in\s+\d{4})',
            r'([A-Z][a-zA-Z0-9\-\s]+)(?:\s+is\s+based\s+in\s+(?:the\s+)?(?:UK|United Kingdom|London|Edinburgh|Glasgow|Manchester|Birmingham))',
            r'([A-Z][a-zA-Z0-9\-\s]+)(?:\s+is\s+a\s+(?:UK|British)\s+(?:startup|company))',
            r'([A-Z][a-zA-Z0-9\-\s]+)(?:\s+has\s+developed\s+a\s+)'
        ]
        
        for pattern in company_patterns:
            matches = re.finditer(pattern, html_content, re.IGNORECASE)
            for match in matches:
                company_name = match.group(1).strip()
                # Filter out common non-company phrases
                if len(company_name) > 3 and not any(x.lower() in company_name.lower() for x in ['the ', 'and ', 'top ', 'best ', 'these ', 'some ', 'many ', 'most ', 'other ', 'all ', 'our ']):
                    if company_name not in startup_names:
                        startup_names.append(company_name)
    
    # Filter out common words that are not company names
    filtered_names = []
    common_words = [
        "The", "This", "That", "These", "Those", "Their", "And", "But", "For",
        "About", "Home", "Menu", "Search", "Top", "Australia", "April", "March",
        "Country", "Technology", "Application", "Contact", "Privacy", "Terms",
        "Copyright", "All", "Rights", "Reserved", "Follow", "Share", "Like",
        "Comment", "Subscribe", "Newsletter", "Sign", "Login", "Register",
        "Create", "Account", "Profile", "Settings", "Help", "Support", "FAQ",
        "Carbon", "Climate", "Energy", "Green", "Clean", "Sustainable", "Renewable",
        "Company", "Business", "Startup", "Enterprise", "Venture", "Innovation"
    ]
    
    for name in startup_names:
        if name not in common_words and len(name.split()) < 5:  # Avoid long phrases
            filtered_names.append(name)
    
    return filtered_names

def test_uk_decarbonisation_complete():
    """Complete test for finding decarbonisation startups in the UK."""
    # Check if API keys are set
    if not os.environ.get("GOOGLE_SEARCH_API_KEY") or not os.environ.get("GOOGLE_CX_ID"):
        logger.error("Please set GOOGLE_SEARCH_API_KEY and GOOGLE_CX_ID environment variables")
        return None
    
    # Create crawlers
    startup_crawler = StartupCrawler(max_workers=5)
    web_crawler = WebCrawler(max_workers=5)
    
    # Define search queries for finding lists of startups
    queries = [
        "list of decarbonisation startups in UK",
        "top carbon capture startups in United Kingdom",
        "net zero startups UK 2023",
        "climate tech startups in Britain list",
        "UK startups fighting climate change",
        "British cleantech companies list",
        "UK green energy startups",
        "carbon removal startups UK",
        "UK sustainable technology companies"
    ]
    
    all_startup_names = []
    
    # Phase 1: Extract startup names from articles about UK decarbonisation startups
    logger.info("Phase 1: Extracting startup names from articles")
    
    for query in queries:
        logger.info(f"Processing query: {query}")
        
        # Search for articles about UK decarbonisation startups
        search_results = startup_crawler.google_search.search(query, max_results=5)
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
        for url, (raw_html, soup) in webpage_results.items():
            if not raw_html or not soup:
                continue
            
            logger.info(f"Extracting startup names from: {url}")
            
            # Extract startup names using our custom function
            startup_names = extract_startup_names_from_html(raw_html, soup)
            
            if startup_names:
                logger.info(f"Found {len(startup_names)} potential startup names")
                for name in startup_names:
                    logger.info(f"  {name}")
                all_startup_names.extend(startup_names)
    
    # Remove duplicates and normalize
    unique_startup_names = []
    seen_names = set()
    
    for name in all_startup_names:
        normalized_name = name.strip().lower()
        if normalized_name and normalized_name not in seen_names:
            seen_names.add(normalized_name)
            unique_startup_names.append(name.strip())
    
    logger.info(f"Found {len(unique_startup_names)} unique potential startup names")
    
    # Phase 2: Use Gemini to filter the startup names
    logger.info("Phase 2: Filtering startup names using Gemini")
    
    # Create batches of 10 names to avoid exceeding token limits
    batch_size = 10
    filtered_names = []
    
    for i in range(0, len(unique_startup_names), batch_size):
        batch = unique_startup_names[i:i+batch_size]
        
        # Create a prompt for Gemini to filter the names
        names_str = "\n".join([f"- {name}" for name in batch])
        prompt = f"""
        I have extracted the following potential startup names from articles about decarbonisation, carbon capture, and climate tech startups in the UK:
        
        {names_str}
        
        Please analyze this list and identify which ones are ACTUAL LEGITIMATE STARTUPS or COMPANIES based in the UK that are related to decarbonisation, carbon capture, or climate tech.
        
        Return ONLY the names of LEGITIMATE UK-BASED STARTUPS that are RELEVANT to decarbonisation or climate tech as a comma-separated list.
        If none of them appear to be legitimate UK startups in this field, return "No relevant startups found".
        """
        
        try:
            # Use the Pro model for more complex reasoning
            response = startup_crawler.gemini.api_client.pro_model.generate_content(prompt)
            
            # Extract filtered startup names from response
            if response.text and "No relevant startups found" not in response.text:
                # Split by commas and clean up
                batch_filtered = [name.strip() for name in response.text.split(',')]
                filtered_names.extend(batch_filtered)
                
                logger.info(f"Gemini filtered batch: {len(batch)} -> {len(batch_filtered)}")
                for name in batch_filtered:
                    logger.info(f"  Verified startup: {name}")
        except Exception as e:
            logger.error(f"Error filtering startup names with Gemini: {e}")
    
    logger.info(f"After filtering, found {len(filtered_names)} verified startups")
    
    # Phase 3: Enrich the startup data
    logger.info("Phase 3: Enriching startup data")
    
    # Create startup info list
    startup_info_list = []
    for name in filtered_names:
        startup_info_list.append({"Company Name": name})
    
    # Enrich the startup data
    if startup_info_list:
        enriched_startups = startup_crawler.enrich_startup_data(startup_info_list)
        
        # Log results
        logger.info(f"Enriched {len(enriched_startups)} startups")
        for startup in enriched_startups:
            logger.info(f"Startup: {startup.get('Company Name', 'Unknown')}")
            for key, value in startup.items():
                if key != "Company Name":
                    logger.info(f"  {key}: {value}")
        
        # Save results to JSON file
        output_file = os.path.join("data", "uk_decarbonisation_complete.json")
        with open(output_file, "w") as f:
            json.dump(enriched_startups, f, indent=2)
        
        logger.info(f"Results saved to {output_file}")
        
        # Generate CSV file
        generate_csv_from_results(enriched_startups)
        
        return enriched_startups
    else:
        logger.warning("No startups found to enrich")
        return []

def generate_csv_from_results(startups: List[Dict[str, Any]]):
    """Generate a CSV file from the results."""
    # Define CSV columns
    columns = [
        "Company Name", "Website", "LinkedIn", "Location", "Founded Year", 
        "Industry", "Company Size", "Funding", "Product Description", 
        "Products/Services", "Team", "Contact", "Source"
    ]
    
    # Create CSV file
    output_file = os.path.join("data", "uk_decarbonisation_complete.csv")
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
    logger.info("Starting complete UK decarbonisation startups test")
    startups = test_uk_decarbonisation_complete()
    
    if startups and len(startups) > 0:
        logger.info(f"Test completed successfully with {len(startups)} startups found")
    else:
        logger.warning("Test completed but no startups were found")
