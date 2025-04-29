"""
Google Search API Client for Startup Intelligence Finder.

This module provides a wrapper around Google's Custom Search API for finding
startup information on the web.
"""

import os
import json
import time
import re
from typing import Dict, List, Optional, Union

import requests
from bs4 import BeautifulSoup


class GoogleSearchClient:
    """
    A client for interacting with Google's Custom Search API.

    This class handles authentication, request formatting, and response parsing
    for the Google Custom Search API, which is used to find startup information.
    """

    def __init__(self, api_key: Optional[str] = None, cx_id: Optional[str] = None):
        """
        Initialize the Google Search API client.

        Args:
            api_key: The API key for Google Search. If not provided, will look for
                    GOOGLE_SEARCH_API_KEY environment variable.
            cx_id: The Custom Search Engine ID. If not provided, will look for
                  GOOGLE_CX_ID environment variable.

        Raises:
            ValueError: If no API key or CX ID is provided and none is found in environment.
        """
        self.api_key = api_key or os.environ.get("GOOGLE_SEARCH_API_KEY")
        self.cx_id = cx_id or os.environ.get("GOOGLE_CX_ID")

        if not self.api_key or not self.cx_id:
            # Try to import and run setup_environment if available
            try:
                import importlib.util

                # Check if setup_env.py exists in the parent directory
                setup_env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "setup_env.py")

                if os.path.exists(setup_env_path):
                    # Import setup_env.py
                    spec = importlib.util.spec_from_file_location("setup_env", setup_env_path)
                    setup_env = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(setup_env)

                    # Run setup_environment
                    if setup_env.setup_environment():
                        # Try to get the API key and CX ID again
                        self.api_key = os.environ.get("GOOGLE_SEARCH_API_KEY")
                        self.cx_id = os.environ.get("GOOGLE_CX_ID")
            except Exception as e:
                # If anything goes wrong, just continue to the error
                print(f"Error importing setup_env.py: {e}")

        # Check if we have the required credentials
        if not self.api_key:
            raise ValueError(
                "No Google Search API key provided. Either pass api_key parameter, "
                "set GOOGLE_SEARCH_API_KEY environment variable, or run setup_env.py first."
            )

        if not self.cx_id:
            raise ValueError(
                "No Custom Search Engine ID provided. Either pass cx_id parameter, "
                "set GOOGLE_CX_ID environment variable, or run setup_env.py first."
            )

        # API endpoint
        self.search_url = "https://www.googleapis.com/customsearch/v1"

        # Rate limiting parameters
        self.request_delay = 1.0  # seconds between requests
        self.last_request_time = 0

    def _respect_rate_limits(self):
        """
        Ensure we respect rate limits by adding delays between requests.

        This method adds a delay between API requests to avoid hitting rate limits.
        """
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time

        if time_since_last_request < self.request_delay:
            # Sleep to respect rate limit
            sleep_time = self.request_delay - time_since_last_request
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def search(self, query: str, num_results: int = 20) -> List[Dict[str, str]]:
        """
        Search for information using Google Custom Search.

        Args:
            query: Search query.
            num_results: Number of results to return (max 10 per request, but we'll make multiple requests).

        Returns:
            List of search result dictionaries.

        Raises:
            Exception: If there's an error communicating with the Google Search API.
        """
        results = []

        # Google Search API only allows 10 results per request
        # If more results are requested, we need to make multiple requests
        # Increase the maximum to 100 results (10 pages of 10 results)
        for start_index in range(1, min(num_results + 1, 101), 10):
            # Respect rate limits
            self._respect_rate_limits()

            # Prepare request parameters
            params = {
                "key": self.api_key,
                "cx": self.cx_id,
                "q": query,
                "start": start_index,
                "num": min(10, num_results - len(results))
            }

            try:
                # Make the request
                response = requests.get(self.search_url, params=params)
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

                # Check if we have enough results
                if len(results) >= num_results:
                    break

            except Exception as e:
                print(f"Error searching Google: {e}")
                break

        return results[:num_results]

    def extract_startup_info(self, url: str) -> Optional[Dict[str, str]]:
        """
        Extract startup information from a webpage.

        Args:
            url: URL of the webpage.

        Returns:
            Dictionary of startup information, or None if extraction failed.

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

            # Try to extract more information
            # This is a simplified implementation
            # In a real-world scenario, this would use more sophisticated extraction

            # Look for common patterns in the text
            text = soup.get_text()

            # Try to find founding year
            year_patterns = [
                r"[Ff]ounded in (\d{4})",
                r"[Ee]stablished in (\d{4})",
                r"[Ss]ince (\d{4})"
            ]

            for pattern in year_patterns:
                match = re.search(pattern, text)
                if match:
                    startup_info["Founded Year"] = match.group(1)
                    break

            # Try to find location
            location_patterns = [
                r"[Hh]eadquartered in ([^\.]+)",
                r"[Bb]ased in ([^\.]+)",
                r"[Ll]ocated in ([^\.]+)"
            ]

            for pattern in location_patterns:
                match = re.search(pattern, text)
                if match:
                    startup_info["Location"] = match.group(1).strip()
                    break

            # Try to find founders
            founder_patterns = [
                r"[Ff]ounder[s]?:?\s+([^\.]+)",
                r"[Ff]ounded by ([^\.]+)"
            ]

            for pattern in founder_patterns:
                match = re.search(pattern, text)
                if match:
                    startup_info["Founders"] = match.group(1).strip()
                    break

            # Try to find funding information
            funding_patterns = [
                r"[Rr]aised ([^\.]+)",
                r"[Ff]unding:?\s+([^\.]+)",
                r"[Ii]nvestment:?\s+([^\.]+)"
            ]

            for pattern in funding_patterns:
                match = re.search(pattern, text)
                if match:
                    startup_info["Funding Information"] = match.group(1).strip()
                    break

            # Try to find product description
            # Look for meta description
            meta_desc = soup.find("meta", attrs={"name": "description"})
            if meta_desc and "content" in meta_desc.attrs:
                startup_info["Product Description"] = meta_desc["content"].strip()

            return startup_info

        except Exception as e:
            print(f"Error extracting info from {url}: {e}")
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
