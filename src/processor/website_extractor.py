"""
Website data extractor for the Startup Finder project.
"""

import logging
import requests
from typing import Dict, Any, Optional, Tuple
from bs4 import BeautifulSoup
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from src.utils.api_client import GeminiAPIClient

# Set up logging
logger = logging.getLogger(__name__)

class WebsiteExtractor:
    """
    Extracts data from company websites using LLM.
    """

    @staticmethod
    def fetch_webpage(url: str) -> Tuple[Optional[str], Optional[BeautifulSoup]]:
        """
        Fetch webpage content using Beautiful Soup.

        Args:
            url: URL of the webpage to fetch.

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

            # Set headers to mimic a browser
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

            logger.info(f"Successfully fetched {url} with Beautiful Soup")
            return response.text, soup

        except Exception as e:
            logger.error(f"Failed to fetch {url} with Beautiful Soup: {e}")
            return None, None

    @staticmethod
    def extract_data(company_name: str, url: str, raw_html: Optional[str] = None, soup: Optional[BeautifulSoup] = None, api_client: Optional[GeminiAPIClient] = None) -> Dict[str, Any]:
        """
        Extract data from a company's official website using Gemini LLM.

        Args:
            company_name: Name of the company.
            url: URL of the website.
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
                logger.info(f"No HTML content provided for {url}, trying to fetch with Beautiful Soup")
                raw_html, soup = WebsiteExtractor.fetch_webpage(url)

                if not raw_html or not soup:
                    logger.error(f"Failed to fetch {url} with Beautiful Soup")
                    return {}

            # Define the fields we want to extract
            fields_to_extract = [
                "Company Description",
                "Contact",
                "Founded Year",
                "Location",
                "Products/Services",
                "Team",
                "Founders",
                "Founder LinkedIn Profiles",
                "CEO/Leadership",
                "Industry",
                "Technology Stack",
                "Competitors",
                "Market Focus",
                "Social Media Links",
                "Latest News",
                "Investors",
                "Growth Metrics"
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
                if len(text_content) < 100 and raw_html:
                    text_content = raw_html
            elif raw_html:
                text_content = raw_html
            else:
                logger.error(f"No content available for {url}")
                return {}

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
