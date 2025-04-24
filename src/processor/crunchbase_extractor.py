"""
Crunchbase data extractor for the Startup Finder project.

This module provides functions to extract data about startups from Crunchbase
using Google Search as a proxy to avoid scraping restrictions, leveraging LLM for extraction.
"""

import logging
from typing import Dict, Any, Optional, List
from bs4 import BeautifulSoup
from src.utils.api_client import GeminiAPIClient

# Set up logging
logger = logging.getLogger(__name__)

class CrunchbaseExtractor:
    """
    Extracts data from Crunchbase company pages using Google Search as a proxy and LLM for extraction.
    """

    @staticmethod
    def extract_data(company_name: str, url: str, raw_html: str, soup: BeautifulSoup, api_client: Optional[GeminiAPIClient] = None) -> Dict[str, Any]:
        """
        Extract data from a Crunchbase company page using Gemini LLM.

        Args:
            company_name: Name of the company.
            url: URL of the Crunchbase page.
            raw_html: Raw HTML content.
            soup: BeautifulSoup object.
            api_client: Optional GeminiAPIClient instance.

        Returns:
            Dictionary of extracted data.
        """
        try:
            # Initialize API client if not provided
            if api_client is None:
                api_client = GeminiAPIClient()

            # Define the fields we want to extract
            fields_to_extract = [
                "Funding",
                "Founded Year",
                "Location",
                "Founders",
                "Company Description",
                "Industry",
                "Company Size",
                "Funding Rounds",
                "Investors"
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
                if len(text_content) < 100:
                    text_content = raw_html
            else:
                text_content = raw_html

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
                "Industry",
                "Company Size",
                "Funding Rounds",
                "Investors"
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
