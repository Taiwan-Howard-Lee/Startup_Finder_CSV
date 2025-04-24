"""
Website data extractor for the Startup Finder project.
"""

import logging
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup
from src.utils.api_client import GeminiAPIClient

# Set up logging
logger = logging.getLogger(__name__)

class WebsiteExtractor:
    """
    Extracts data from company websites using LLM.
    """

    @staticmethod
    def extract_data(company_name: str, url: str, raw_html: str, soup: BeautifulSoup, api_client: Optional[GeminiAPIClient] = None) -> Dict[str, Any]:
        """
        Extract data from a company's official website using Gemini LLM.

        Args:
            company_name: Name of the company.
            url: URL of the website.
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
                "Contact",
                "Founded Year",
                "Location",
                "Products/Services",
                "Team",
                "Founders",
                "Industry",
                "Social Media"
            ]

            # Get text content from the soup for better processing
            if soup:
                # Extract text from the most relevant parts of the page
                text_content = ""

                # Add the title
                if soup.title:
                    text_content += f"Title: {soup.title.get_text()}\n\n"

                # Add meta descriptions which often contain valuable information
                meta_desc = soup.find('meta', attrs={'name': 'description'})
                if meta_desc and 'content' in meta_desc.attrs:
                    text_content += f"Meta Description: {meta_desc['content']}\n\n"

                og_desc = soup.find('meta', attrs={'property': 'og:description'})
                if og_desc and 'content' in og_desc.attrs:
                    text_content += f"OG Description: {og_desc['content']}\n\n"

                # Extract text from about, contact, and team pages which often contain location and founding info
                about_sections = soup.find_all(['section', 'div'], class_=lambda c: c and any(x in str(c).lower() for x in ['about', 'company', 'team', 'contact']))
                for section in about_sections:
                    text_content += section.get_text().strip() + "\n\n"

                # Extract text from main content
                main_content = soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                for element in main_content:
                    if element.get_text().strip():
                        text_content += element.get_text().strip() + "\n"

                # Extract social media links
                social_links = []
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    if any(platform in href for platform in ['twitter.com', 'facebook.com', 'linkedin.com', 'instagram.com', 'youtube.com']):
                        social_links.append(f"Social Media Link: {href}")

                if social_links:
                    text_content += "\n" + "\n".join(social_links)

                # If we couldn't extract meaningful text, fall back to raw HTML
                if len(text_content) < 100:
                    text_content = raw_html
            else:
                text_content = raw_html

            # Use the LLM to extract structured data
            website_data = api_client.extract_structured_data(
                company_name=company_name,
                source_type="Website",
                content=text_content,
                fields=fields_to_extract
            )

            logger.info(f"Extracted website data for {company_name} using LLM: {list(website_data.keys())}")
            return website_data

        except Exception as e:
            logger.error(f"Error extracting website data from {url}: {e}")
            return {}
