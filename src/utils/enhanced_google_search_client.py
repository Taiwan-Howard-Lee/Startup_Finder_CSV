#!/usr/bin/env python3
"""
Enhanced Google Search API Client with API Key Rotation.

This module provides an improved wrapper around Google's Custom Search API
that supports rotating between multiple API keys and CX IDs to avoid rate limits.
"""

import time
import logging
import requests
from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup

from src.utils.api_key_manager import APIKeyManager

# Set up logging
logger = logging.getLogger(__name__)

class EnhancedGoogleSearchClient:
    """
    An enhanced client for interacting with Google's Custom Search API.

    This class handles authentication, request formatting, and response parsing
    for the Google Custom Search API, with support for multiple API keys and CX IDs.
    """

    def __init__(self, key_manager: Optional[APIKeyManager] = None):
        """
        Initialize the Enhanced Google Search API client.

        Args:
            key_manager: An instance of APIKeyManager for handling API keys and CX IDs.
                        If not provided, a new instance will be created.

        Raises:
            ValueError: If no API keys or CX IDs are available.
        """
        # Initialize the key manager
        self.key_manager = key_manager or APIKeyManager()

        # API endpoint
        self.search_url = "https://www.googleapis.com/customsearch/v1"

        # Rate limiting parameters
        self.request_delay = 1.0  # seconds between requests
        self.last_request_time = 0

        # Retry parameters
        self.max_retries = 3
        self.retry_delay = 2.0  # seconds

        logger.info("Enhanced Google Search client initialized with API key rotation")

    def _respect_rate_limits(self) -> None:
        """Ensure we don't exceed Google's rate limits."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time

        if time_since_last_request < self.request_delay:
            sleep_time = self.request_delay - time_since_last_request
            logger.debug(f"Rate limiting: Sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def search(self, query: str, num_results: int = 10, max_results: int = None, start_index: int = 0) -> List[Dict[str, str]]:
        """
        Search for information using Google Custom Search with API key rotation.

        Args:
            query: Search query.
            num_results: Number of results to return (max 10 per request, but we'll make multiple requests).
            max_results: Alias for num_results for compatibility with StartupCrawler.
            start_index: Starting index for search results (for pagination/batching).

        Returns:
            List of search result dictionaries.

        Raises:
            Exception: If there's an error communicating with the Google Search API.
        """
        # For compatibility with StartupCrawler
        if max_results is not None:
            num_results = max_results

        results = []

        # Google Search API only allows 10 results per request
        # If more results are requested, we need to make multiple requests
        # Increase the maximum to 100 results (10 pages of 10 results)
        # Use the provided start_index as the base, then paginate from there
        for page_start in range(start_index + 1, min(start_index + num_results + 1, 101), 10):
            # Respect rate limits
            self._respect_rate_limits()

            # Get the next API key and CX ID
            api_key, cx_id = self.key_manager.get_next_key_pair()

            # Prepare request parameters
            params = {
                "key": api_key,
                "cx": cx_id,
                "q": query,
                "start": page_start,
                "num": min(10, num_results - len(results))
            }

            # Try the request with retries
            for retry in range(self.max_retries):
                try:
                    # Make the request
                    response = requests.get(self.search_url, params=params, timeout=10)

                    # Check for rate limit or quota errors
                    if response.status_code == 429 or response.status_code == 403:
                        self.key_manager.report_error(api_key, cx_id, response.status_code)

                        # If we have more retries, try with a different key
                        if retry < self.max_retries - 1:
                            logger.warning(f"API error {response.status_code}. Retrying with different key...")
                            api_key, cx_id = self.key_manager.get_next_key_pair()
                            params["key"] = api_key
                            params["cx"] = cx_id
                            time.sleep(self.retry_delay * (2 ** retry))  # Exponential backoff
                            continue
                        else:
                            logger.error(f"Failed after {self.max_retries} retries")
                            break

                    # For other errors, raise the exception
                    response.raise_for_status()

                    # Parse the response
                    data = response.json()

                    # Extract search results
                    if "items" in data:
                        for item in data["items"]:
                            result = {
                                "title": item.get("title", ""),
                                "link": item.get("link", ""),
                                "snippet": item.get("snippet", ""),
                                "source": "Google Search"
                            }
                            results.append(result)

                    # Success, break the retry loop
                    break

                except requests.exceptions.RequestException as e:
                    logger.warning(f"Request error: {e}")

                    # If we have more retries, try again
                    if retry < self.max_retries - 1:
                        logger.info(f"Retrying ({retry+1}/{self.max_retries})...")
                        time.sleep(self.retry_delay * (2 ** retry))  # Exponential backoff
                    else:
                        logger.error(f"Failed after {self.max_retries} retries")

                except Exception as e:
                    logger.error(f"Error searching Google: {e}")
                    break

            # Check if we have enough results
            if len(results) >= num_results:
                break

        return results[:num_results]

    def extract_startup_info(self, url: str) -> Optional[Dict[str, str]]:
        """
        Extract startup information from a webpage.

        Args:
            url: URL of the webpage to extract information from.

        Returns:
            Dictionary containing startup information, or None if extraction failed.

        Raises:
            Exception: If there's an error accessing or parsing the webpage.
        """
        try:
            # Respect rate limits
            self._respect_rate_limits()

            # Make the request
            headers = {
                "User-Agent": "StartupFinder/1.0 (https://github.com/yourusername/startup-finder)"
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            # Parse the HTML
            soup = BeautifulSoup(response.text, "lxml")

            # Extract basic information
            title = soup.title.text.strip() if soup.title else ""

            # Extract company name from title
            company_name = title.split("-")[0].strip() if "-" in title else title

            # Initialize startup info
            startup_info = {
                "Company Name": company_name,
                "Website": url,
                "Source": "Web Extraction"
            }

            # Extract more information if available
            # This is a simplified version - in a real implementation, you would
            # use more sophisticated extraction techniques

            # Look for common elements that might contain useful information
            description_elements = soup.select("meta[name='description'], meta[property='og:description']")
            if description_elements:
                startup_info["Product Description"] = description_elements[0].get("content", "")

            # Return the extracted information
            return startup_info

        except Exception as e:
            logger.error(f"Error extracting info from {url}: {e}")
            return None

    def search_startups(self, query: str, num_results: int = 10) -> List[Dict[str, str]]:
        """
        Search for startups and extract information.

        Args:
            query: Search query.
            num_results: Number of startups to find.

        Returns:
            List of startup information dictionaries.

        Raises:
            Exception: If there's an error with the search or extraction process.
        """
        # Add startup-specific terms to the query
        startup_query = f"{query} startup company"

        # Search for startups
        search_results = self.search(startup_query, num_results * 3)  # Get more results than needed to ensure quality

        startup_info_list = []

        # Extract information from each result
        for result in search_results:
            url = result.get("link", "")

            # Skip if URL is empty
            if not url:
                continue

            # Extract startup information
            startup_info = self.extract_startup_info(url)

            if startup_info:
                # Add snippet from search result if no product description was found
                if "Product Description" not in startup_info and "snippet" in result:
                    startup_info["Product Description"] = result.get("snippet", "")

                # Add to list
                startup_info_list.append(startup_info)

                # Check if we have enough results
                if len(startup_info_list) >= num_results:
                    break

        return startup_info_list

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics for API keys and CX IDs."""
        return self.key_manager.get_usage_stats()
