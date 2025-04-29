"""
LinkedIn data extractor for the Startup Finder project.
"""

import logging
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup
from src.utils.api_client import GeminiAPIClient

# Set up logging
logger = logging.getLogger(__name__)

class LinkedInExtractor:
    """
    Extracts data from LinkedIn company pages using LLM.
    """

    @staticmethod
    def extract_data(company_name: str, url: str, raw_html: str, soup: BeautifulSoup, api_client: Optional[GeminiAPIClient] = None) -> Dict[str, Any]:
        """
        Extract data from a LinkedIn company page using Gemini LLM.

        Args:
            company_name: Name of the company.
            url: URL of the LinkedIn page.
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
                "Company Description",
                "Company Size",
                "Industry",
                "Founded Year",
                "Location",
                "Founders",
                "Founder LinkedIn Profiles",
                "CEO/Leadership",
                "Funding",
                "Products/Services",
                "Technology Stack",
                "Competitors",
                "Market Focus",
                "Social Media Links",
                "Latest News",
                "Investors",
                "Growth Metrics"
            ]

            # Get text content from the soup for better processing
            # This is more reliable than using raw HTML
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

                # Add main content
                main_content = soup.find_all(['p', 'div', 'section', 'article'])
                for element in main_content:
                    if element.get_text().strip():
                        text_content += element.get_text().strip() + "\n"

                # If we couldn't extract meaningful text, fall back to raw HTML
                if len(text_content) < 100:
                    text_content = raw_html
            else:
                text_content = raw_html

            # Use the LLM to extract structured data
            linkedin_data = api_client.extract_structured_data(
                company_name=company_name,
                source_type="LinkedIn",
                content=text_content,
                fields=fields_to_extract
            )

            logger.info(f"Extracted LinkedIn data for {company_name} using LLM: {list(linkedin_data.keys())}")
            return linkedin_data

        except Exception as e:
            logger.error(f"Error extracting LinkedIn data from {url}: {e}")
            return {}
