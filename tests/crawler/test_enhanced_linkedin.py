"""
Test script for the enhanced LinkedIn and company website data collection.
"""

import os
import time
import logging
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.processor.crawler import StartupCrawler
from src.processor.linkedin_extractor import LinkedInExtractor
from src.processor.website_extractor import WebsiteExtractor

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_linkedin_extraction():
    """Test LinkedIn data extraction."""
    # Create a sample HTML content
    linkedin_html = """
    <html>
    <head><title>Carbon Clean | LinkedIn</title></head>
    <body>
        <h1>Carbon Clean</h1>
        <p>Carbon capture technology company</p>
        <div>
            <dt>Industry</dt>
            <dd>Environmental Services</dd>
            <dt>Company size</dt>
            <dd>201-500 employees</dd>
            <dt>Headquarters</dt>
            <dd>London, United Kingdom</dd>
            <dt>Founded</dt>
            <dd>2009</dd>
        </div>
        <p class="description">Carbon Clean is a global leader in carbon capture solutions for hard-to-abate industries.</p>
        <div>The company has raised $150 million in funding.</div>
    </body>
    </html>
    """

    # Create a BeautifulSoup object
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(linkedin_html, "html.parser")

    # Extract LinkedIn data
    company_name = "Carbon Clean"
    url = "https://www.linkedin.com/company/carbon-clean-solutions/"

    # Test the LinkedIn extractor
    linkedin_data = LinkedInExtractor.extract_data(company_name, url, linkedin_html, soup)

    # Log results
    logger.info(f"LinkedIn data for {company_name}:")
    for key, value in linkedin_data.items():
        logger.info(f"  {key}: {value}")

    return linkedin_data

def test_website_extraction():
    """Test company website data extraction."""
    # Create a sample HTML content
    website_html = """
    <html>
    <head>
        <title>Carbon Clean - Carbon Capture Technology</title>
        <meta name="description" content="Carbon Clean is a global leader in carbon capture solutions for hard-to-abate industries." />
    </head>
    <body>
        <h1>Carbon Clean</h1>
        <div class="about-us">
            <p>Founded in 2009, Carbon Clean is headquartered in London, UK.</p>
            <p>Contact us at info@carbonclean.com</p>
        </div>
        <div class="products">
            <h2>Our Solutions</h2>
            <p>CycloneCC: A revolutionary modular carbon capture technology that is significantly smaller and lower cost.</p>
        </div>
        <div class="team">
            <h2>Our Team</h2>
            <p>Led by CEO Aniruddha Sharma and CTO Prateek Bumb, who founded the company in 2009.</p>
        </div>
    </body>
    </html>
    """

    # Create a BeautifulSoup object
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(website_html, "html.parser")

    # Extract website data
    company_name = "Carbon Clean"
    url = "https://www.carbonclean.com/"

    # Test the website extractor
    website_data = WebsiteExtractor.extract_data(company_name, url, website_html, soup)

    # Log results
    logger.info(f"Website data for {company_name}:")
    for key, value in website_data.items():
        logger.info(f"  {key}: {value}")

    return website_data

def test_linkedin_enrichment():
    """Test the enhanced LinkedIn and company website data collection."""
    # Create a crawler with parallel processing
    crawler = StartupCrawler(max_workers=5)

    # Test startup names
    startup_names = ["Carbon Clean", "Artemis Technologies", "Notpla"]

    # Measure time
    start_time = time.time()

    # Create startup info list
    startup_info_list = []
    for name in startup_names:
        startup_info_list.append({"Company Name": name})

    # Run the enrichment phase
    logger.info(f"Starting enrichment phase for {len(startup_info_list)} startups")
    enriched_startups = crawler.enrich_startup_data(startup_info_list, max_results_per_startup=2)

    # Log results
    logger.info(f"Enriched {len(enriched_startups)} startups")
    for startup in enriched_startups:
        logger.info(f"Startup: {startup.get('Company Name', 'Unknown')}")
        for key, value in startup.items():
            if key != "Company Name":
                logger.info(f"  {key}: {value}")

    # Calculate elapsed time
    elapsed_time = time.time() - start_time
    logger.info(f"Test completed in {elapsed_time:.2f} seconds")

    return enriched_startups

if __name__ == "__main__":
    # Run the LinkedIn extractor test
    logger.info("=== Testing LinkedIn Extractor ===")
    linkedin_data = test_linkedin_extraction()

    # Run the website extractor test
    logger.info("\n=== Testing Website Extractor ===")
    website_data = test_website_extraction()

    # Run the enrichment test if API keys are set
    if os.environ.get("GOOGLE_SEARCH_API_KEY") and os.environ.get("GOOGLE_CX_ID"):
        logger.info("\n=== Testing LinkedIn Enrichment ===")
        enriched_startups = test_linkedin_enrichment()
    else:
        logger.info("\nSkipping enrichment test - API keys not set")
        logger.info("Please set GOOGLE_SEARCH_API_KEY and GOOGLE_CX_ID environment variables to run the enrichment test")
