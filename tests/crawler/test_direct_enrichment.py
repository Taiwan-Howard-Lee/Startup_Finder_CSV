"""
Test script for directly testing the enhanced enrichment method.
"""

import os
import time
import logging
import sys
import re
from typing import Dict, Any, List
from bs4 import BeautifulSoup

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.processor.linkedin_extractor import LinkedInExtractor
from src.processor.website_extractor import WebsiteExtractor

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MockGoogleSearch:
    """Mock Google Search API for testing."""

    def search(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Mock search method."""
        logger.info(f"Mock Google Search: {query}")

        if "official website" in query:
            if "Carbon Clean" in query:
                return [{"url": "https://www.carbonclean.com/", "title": "Carbon Clean: Carbon Capture Technology", "snippet": "Carbon Clean is a global leader in carbon capture solutions."}]
            elif "Artemis Technologies" in query:
                return [{"url": "https://www.artemistechnologies.co.uk/", "title": "Artemis Technologies", "snippet": "Artemis Technologies is a global leader in green maritime innovation."}]
            elif "Notpla" in query:
                return [{"url": "https://www.notpla.com/", "title": "Notpla - Packaging made from Seaweed", "snippet": "Notpla is a sustainable packaging company."}]

        if "site:linkedin.com/company/" in query:
            if "Carbon Clean" in query:
                return [{"url": "https://www.linkedin.com/company/carbon-clean-solutions/", "title": "Carbon Clean | LinkedIn", "snippet": "Carbon Clean | 5,000+ followers on LinkedIn. Leading the race in carbon capture technology."}]
            elif "Artemis Technologies" in query:
                return [{"url": "https://www.linkedin.com/company/artemis-technologies/", "title": "Artemis Technologies | LinkedIn", "snippet": "Artemis Technologies | 2,000+ followers on LinkedIn. Decarbonising maritime."}]
            elif "Notpla" in query:
                return [{"url": "https://www.linkedin.com/company/notpla/", "title": "Notpla | LinkedIn", "snippet": "Notpla | 3,000+ followers on LinkedIn. Packaging made from seaweed."}]

        return []

class MockWebCrawler:
    """Mock Web Crawler for testing."""

    def fetch_webpages_parallel(self, urls: List[str]) -> Dict[str, Any]:
        """Mock fetch webpages method."""
        logger.info(f"Mock fetching webpages: {urls}")

        results = {}

        for url in urls:
            if "carbonclean.com" in url:
                html = """
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
                soup = BeautifulSoup(html, "html.parser")
                results[url] = (html, soup)

            elif "linkedin.com/company/carbon-clean" in url:
                html = """
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
                soup = BeautifulSoup(html, "html.parser")
                results[url] = (html, soup)

            elif "artemistechnologies.co.uk" in url:
                html = """
                <html>
                <head>
                    <title>Artemis Technologies - Maritime Innovation</title>
                    <meta name="description" content="Artemis Technologies is a global leader in green maritime innovation." />
                </head>
                <body>
                    <h1>Artemis Technologies</h1>
                    <div class="about-us">
                        <p>Founded in 2017, Artemis Technologies is based in Belfast, Northern Ireland.</p>
                        <p>Contact us at info@artemistechnologies.co.uk</p>
                    </div>
                </body>
                </html>
                """
                soup = BeautifulSoup(html, "html.parser")
                results[url] = (html, soup)

            elif "notpla.com" in url:
                html = """
                <html>
                <head>
                    <title>Notpla - Packaging made from Seaweed</title>
                    <meta name="description" content="Notpla is a sustainable packaging company." />
                </head>
                <body>
                    <h1>Notpla</h1>
                    <div class="about-us">
                        <p>Founded in 2014, Notpla is based in London, UK.</p>
                    </div>
                </body>
                </html>
                """
                soup = BeautifulSoup(html, "html.parser")
                results[url] = (html, soup)

        return results

class MockStartupCrawler:
    """Mock Startup Crawler for testing."""

    def __init__(self):
        """Initialize the mock crawler."""
        self.google_search = MockGoogleSearch()
        self.web_crawler = MockWebCrawler()

    def _enrich_single_startup(self, startup_info: Dict[str, Any], max_results_per_startup: int) -> Dict[str, Any]:
        """
        Enrich data for a single startup.

        Args:
            startup_info: Dictionary containing basic startup information.
            max_results_per_startup: Maximum number of results to collect.

        Returns:
            Enriched startup data dictionary.
        """
        name = startup_info.get("Company Name", "")
        if not name:
            return None

        logger.info(f"Enriching data for: {name}")

        # Start with the basic info we already have
        merged_data = startup_info.copy()

        # Step 1: Search specifically for the official website
        website_url = None
        try:
            website_query = f"\"{name}\" official website"
            logger.info(f"Searching for official website: {website_query}")
            website_results = self.google_search.search(website_query, max_results=2)

            if website_results:
                for result in website_results:
                    candidate_url = result.get("url", "")
                    # Check if URL likely belongs to the company
                    if candidate_url and name.lower().replace(" ", "") in candidate_url.lower().replace(" ", ""):
                        if "linkedin.com" not in candidate_url and "facebook.com" not in candidate_url and "twitter.com" not in candidate_url:
                            website_url = candidate_url
                            merged_data["Website"] = website_url
                            logger.info(f"Found official website: {website_url}")
                            break
        except Exception as e:
            logger.error(f"Error finding official website for {name}: {e}")

        # Step 2: Search specifically for LinkedIn profile
        linkedin_url = None
        try:
            linkedin_query = f"site:linkedin.com/company/ \"{name}\""
            logger.info(f"Searching for LinkedIn profile: {linkedin_query}")
            linkedin_results = self.google_search.search(linkedin_query, max_results=2)

            if linkedin_results:
                for result in linkedin_results:
                    candidate_url = result.get("url", "")
                    if candidate_url and "linkedin.com/company/" in candidate_url:
                        linkedin_url = candidate_url
                        merged_data["LinkedIn"] = linkedin_url
                        logger.info(f"Found LinkedIn profile: {linkedin_url}")
                        break
        except Exception as e:
            logger.error(f"Error finding LinkedIn profile for {name}: {e}")

        # Step 3: Fetch and process the official website and LinkedIn profile in parallel
        urls_to_fetch = []
        if website_url:
            urls_to_fetch.append(website_url)
        if linkedin_url:
            urls_to_fetch.append(linkedin_url)

        if urls_to_fetch:
            # Fetch webpages in parallel
            webpage_results = self.web_crawler.fetch_webpages_parallel(urls_to_fetch)

            # Process official website
            if website_url and website_url in webpage_results:
                raw_html, soup = webpage_results[website_url]
                if raw_html and soup:
                    website_data = WebsiteExtractor.extract_data(name, website_url, raw_html, soup)
                    # Merge website data, but don't overwrite existing data
                    for key, value in website_data.items():
                        if key not in merged_data or not merged_data[key]:
                            merged_data[key] = value

            # Process LinkedIn profile
            if linkedin_url and linkedin_url in webpage_results:
                raw_html, soup = webpage_results[linkedin_url]
                if raw_html and soup:
                    linkedin_data = LinkedInExtractor.extract_data(name, linkedin_url, raw_html, soup)
                    # Merge LinkedIn data, but don't overwrite existing data
                    for key, value in linkedin_data.items():
                        if key not in merged_data or not merged_data[key]:
                            merged_data[key] = value

        return merged_data

def test_direct_enrichment():
    """Test the enhanced enrichment method directly."""
    # Create a mock crawler
    crawler = MockStartupCrawler()

    # Test startup names
    startup_names = ["Carbon Clean", "Artemis Technologies", "Notpla"]

    # Measure time
    start_time = time.time()

    # Create startup info list
    startup_info_list = []
    for name in startup_names:
        startup_info_list.append({"Company Name": name})

    # Run the enrichment phase
    logger.info(f"Starting direct enrichment test for {len(startup_info_list)} startups")

    enriched_startups = []
    for startup_info in startup_info_list:
        enriched_data = crawler._enrich_single_startup(startup_info, max_results_per_startup=2)
        if enriched_data:
            enriched_startups.append(enriched_data)

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
    # Run the direct enrichment test
    test_direct_enrichment()
