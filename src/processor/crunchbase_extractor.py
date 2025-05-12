"""
Crunchbase data extractor for the Startup Finder project.

This module provides functions to extract data about startups from Crunchbase
using Google Search as a proxy to avoid scraping restrictions, leveraging LLM for extraction.
"""

import logging
import requests
from typing import Dict, Any, Optional, List, Tuple
from bs4 import BeautifulSoup
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from src.utils.api_client import GeminiAPIClient

# Set up logging
logger = logging.getLogger(__name__)

class CrunchbaseExtractor:
    """
    Extracts data from Crunchbase company pages using Google Search as a proxy and LLM for extraction.
    """

    @staticmethod
    def fetch_webpage(url: str) -> Tuple[Optional[str], Optional[BeautifulSoup]]:
        """
        Fetch Crunchbase page content using Beautiful Soup.

        Args:
            url: URL of the Crunchbase page to fetch.

        Returns:
            Tuple of (raw_html, soup) or (None, None) if fetch failed.
        """
        try:
            # Create a session with retry capability
            session = requests.Session()
            retry_strategy = Retry(
                total=3,
                backoff_factor=0.1,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["GET", "HEAD"]
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            session.mount("http://", adapter)
            session.mount("https://", adapter)

            # Set headers to mimic a browser - Crunchbase may have anti-scraping measures
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            }

            # Make the request
            response = session.get(url, headers=headers, timeout=15, verify=False)
            response.raise_for_status()

            # Parse the HTML
            soup = BeautifulSoup(response.text, "lxml")

            logger.info(f"Successfully fetched Crunchbase page {url} with Beautiful Soup")
            return response.text, soup

        except Exception as e:
            logger.error(f"Failed to fetch Crunchbase page {url} with Beautiful Soup: {e}")
            return None, None

    @staticmethod
    def extract_data(company_name: str, url: str, raw_html: Optional[str] = None, soup: Optional[BeautifulSoup] = None, api_client: Optional[GeminiAPIClient] = None) -> Dict[str, Any]:
        """
        Extract data from a Crunchbase company page using Gemini LLM.

        Args:
            company_name: Name of the company.
            url: URL of the Crunchbase page.
            raw_html: Raw HTML content (optional).
            soup: BeautifulSoup object (optional).
            api_client: Optional GeminiAPIClient instance.

        Returns:
            Dictionary of extracted data.
        """
        try:
            # Initialize API client if not provided
            if api_client is None:
                api_client = GeminiAPIClient()

            # If raw_html or soup is not provided, try to fetch the webpage
            if not raw_html or not soup:
                logger.info(f"No HTML content provided for Crunchbase page {url}, trying to fetch with Beautiful Soup")
                raw_html, soup = CrunchbaseExtractor.fetch_webpage(url)

                if not raw_html or not soup:
                    logger.error(f"Failed to fetch Crunchbase page {url} with Beautiful Soup")
                    return {}

            # Define the fields we want to extract
            fields_to_extract = [
                "Funding",
                "Founded Year",
                "Location",
                "Founders",
                "Founder LinkedIn Profiles",
                "CEO/Leadership",
                "Company Description",
                "Industry",
                "Company Size",
                "Funding Rounds",
                "Investors",
                "Technology Stack",
                "Competitors",
                "Market Focus",
                "Social Media Links",
                "Latest News",
                "Growth Metrics"
            ]

            # Get text content from the soup for better processing
            if soup:
                # Extract text from the most relevant parts of the page
                text_content = ""

                # Add the title
                if soup.title:
                    text_content += f"Title: {soup.title.get_text()}\n\n"

                # Add meta descriptions
                meta_desc = soup.find('meta', attrs={'name': 'description'})
                if meta_desc and 'content' in meta_desc.attrs:
                    text_content += f"Meta Description: {meta_desc['content']}\n\n"

                # Extract text from main content sections
                main_content = soup.find_all(['p', 'div', 'section', 'h1', 'h2', 'h3'])
                for element in main_content:
                    if element.get_text().strip():
                        text_content += element.get_text().strip() + "\n"

                # If we couldn't extract meaningful text, fall back to raw HTML
                if len(text_content) < 100 and raw_html:
                    text_content = raw_html
            elif raw_html:
                text_content = raw_html
            else:
                logger.error(f"No content available for Crunchbase page {url}")
                return {}

            # Use the LLM to extract structured data
            crunchbase_data = api_client.extract_structured_data(
                company_name=company_name,
                source_type="Crunchbase",
                content=text_content,
                fields=fields_to_extract
            )

            logger.info(f"Extracted Crunchbase data for {company_name} using LLM: {list(crunchbase_data.keys())}")
            return crunchbase_data

        except Exception as e:
            logger.error(f"Error extracting Crunchbase data from {url}: {e}")
            return {}

    @staticmethod
    def search_crunchbase_data(google_search, company_name: str, max_results: int = 3, api_client: Optional[GeminiAPIClient] = None) -> Dict[str, Any]:
        """
        Search for Crunchbase data using Google Search and extract with LLM.

        Args:
            google_search: GoogleSearchClient instance.
            company_name: Name of the company.
            max_results: Maximum number of search results to process.
            api_client: Optional GeminiAPIClient instance.

        Returns:
            Dictionary of extracted data.
        """
        try:
            # Initialize API client if not provided
            if api_client is None:
                api_client = GeminiAPIClient()

            # Create a specific query for Crunchbase
            crunchbase_query = f"site:crunchbase.com {company_name} company"

            # Search for Crunchbase information
            search_results = google_search.search(crunchbase_query, max_results=max_results)

            if not search_results:
                return {}

            # Combine all snippets into a single text for better context
            combined_text = f"Crunchbase information for {company_name}:\n\n"

            for result in search_results:
                title = result.get("title", "")
                snippet = result.get("snippet", "")
                url = result.get("url", "")

                combined_text += f"Title: {title}\n"
                combined_text += f"URL: {url}\n"
                combined_text += f"Snippet: {snippet}\n\n"

            # Define the fields we want to extract
            fields_to_extract = [
                "Funding",
                "Founded Year",
                "Location",
                "Founders",
                "Founder LinkedIn Profiles",
                "CEO/Leadership",
                "Industry",
                "Company Size",
                "Funding Rounds",
                "Investors",
                "Technology Stack",
                "Competitors",
                "Market Focus",
                "Social Media Links",
                "Latest News",
                "Growth Metrics"
            ]

            # Use the LLM to extract structured data
            crunchbase_data = api_client.extract_structured_data(
                company_name=company_name,
                source_type="Crunchbase Search Results",
                content=combined_text,
                fields=fields_to_extract
            )

            logger.info(f"Extracted Crunchbase data for {company_name} from Google Search using LLM: {list(crunchbase_data.keys())}")
            return crunchbase_data

        except Exception as e:
            logger.error(f"Error searching Crunchbase data for {company_name}: {e}")
            return {}
