"""
Crawler for Startup Intelligence Finder.

This module implements a two-phase crawling strategy:
1. Phase 1 (Discovery): Find articles about startups and extract actual startup names
2. Phase 2 (Enrichment): Use the discovered startup names to gather detailed information
"""

import os
import re
import json
import time
from typing import Dict, List, Optional, Any, Tuple
import logging

import requests
from bs4 import BeautifulSoup

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataSource:
    """Base class for data sources."""

    def __init__(self, name: str):
        """
        Initialize a data source.

        Args:
            name: Name of the data source.
        """
        self.name = name

    def search(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search for information matching the query.

        Args:
            query: Search query.
            max_results: Maximum number of results to return.

        Returns:
            List of search result dictionaries.
        """
        raise NotImplementedError("Subclasses must implement search method")


class GoogleSearchDataSource(DataSource):
    """
    Data source using Google Search API to find information.
    """

    def __init__(self, api_key: Optional[str] = None, cx_id: Optional[str] = None):
        """
        Initialize the Google Search data source.

        Args:
            api_key: Google Search API key. If None, will look for GOOGLE_SEARCH_API_KEY
                   environment variable.
            cx_id: Google Custom Search Engine ID. If None, will look for GOOGLE_CX_ID
                 environment variable.
        """
        super().__init__("Google Search")

        # Get API key and CX ID from environment if not provided
        self.api_key = api_key or os.environ.get("GOOGLE_SEARCH_API_KEY")
        self.cx_id = cx_id or os.environ.get("GOOGLE_CX_ID")

        if not self.api_key:
            raise ValueError(
                "No Google Search API key provided. Either pass api_key parameter "
                "or set GOOGLE_SEARCH_API_KEY environment variable."
            )

        if not self.cx_id:
            raise ValueError(
                "No Custom Search Engine ID provided. Either pass cx_id parameter "
                "or set GOOGLE_CX_ID environment variable."
            )

        # API endpoint
        self.search_url = "https://www.googleapis.com/customsearch/v1"

        # Rate limiting parameters
        self.request_delay = 1.0  # seconds between requests
        self.last_request_time = 0

        logger.info(f"Initialized Google Search data source with API key: {self.api_key[:5]}...{self.api_key[-5:]}")

    def _respect_rate_limits(self):
        """Ensure we respect rate limits by adding delays between requests."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time

        if time_since_last_request < self.request_delay:
            # Sleep to respect rate limit
            sleep_time = self.request_delay - time_since_last_request
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def search(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search for information using Google Custom Search.

        Args:
            query: Search query.
            max_results: Maximum number of results to return.

        Returns:
            List of search result dictionaries.
        """
        results = []

        # Add startup-specific terms if not already in the query
        startup_terms = ["startup", "company", "business"]
        has_startup_term = any(term in query.lower() for term in startup_terms)

        # Only add startup terms if none are present
        if has_startup_term:
            search_query = query
        else:
            search_query = f"{query} startup company"

        logger.info(f"Searching Google for: {search_query}")

        # Google Search API only allows 10 results per request
        # If more results are requested, we need to make multiple requests
        for start_index in range(1, min(max_results + 1, 101), 10):
            # Respect rate limits
            self._respect_rate_limits()

            # Prepare request parameters
            params = {
                "key": self.api_key,
                "cx": self.cx_id,
                "q": search_query,
                "start": start_index,
                "num": min(10, max_results - len(results))
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
                            "url": item.get("link", ""),
                            "snippet": item.get("snippet", ""),
                            "source": "Google Search"
                        }
                        results.append(result)

                # Check if we have enough results
                if len(results) >= max_results:
                    break

            except Exception as e:
                logger.error(f"Error searching Google: {e}")
                break

        logger.info(f"Found {len(results)} results from Google Search")
        return results[:max_results]


class GeminiDataSource(DataSource):
    """
    Data source using Gemini API for extracting and validating information.
    """

    def __init__(self, api_client=None):
        """
        Initialize the Gemini data source.

        Args:
            api_client: Gemini API client. If None, will try to import from src.utils.api_client.
        """
        super().__init__("Gemini")

        # Import API client if not provided
        if api_client is None:
            try:
                from src.utils.api_client import GeminiAPIClient
                self.api_client = GeminiAPIClient()
            except ImportError:
                raise ImportError("Could not import GeminiAPIClient. Please provide an api_client.")
        else:
            self.api_client = api_client

        logger.info("Initialized Gemini data source")

    def extract_startup_names(self, title: str, snippet: str, url: str) -> List[str]:
        """
        Extract startup names from text using Gemini API.

        Args:
            title: Title of the article or webpage.
            snippet: Snippet or description of the content.
            url: URL of the webpage.

        Returns:
            List of startup names.
        """
        try:
            # Create a prompt for Gemini
            prompt = f"""
            Extract the names of actual startup companies from the following text.
            Return only the company names as a comma-separated list.
            Focus on real company names, not article titles or general terms.
            If no specific startup names are mentioned, return "No startups found".

            Title: {title}
            Description: {snippet}
            URL: {url}

            Look for names that appear in contexts like:
            - "X is a startup that..."
            - "Founded in [year], X is..."
            - Lists of companies or startups
            - Companies mentioned with their products or services

            Ignore names that are clearly UI elements, navigation links, or common terms.
            """

            # Get response from Gemini
            response = self.api_client.flash_model.generate_content(prompt)

            # Extract startup names from response
            if response.text and "No startups found" not in response.text:
                # Split by commas and clean up
                startup_names = [name.strip() for name in response.text.split(',')]

                # Filter out non-company names
                filtered_names = []
                for name in startup_names:
                    # Skip if it's too short or doesn't look like a company name
                    if len(name) < 3 or name in ["AI", "The", "And", "For", "Inc", "Ltd"]:
                        continue
                    filtered_names.append(name)

                logger.info(f"Gemini extracted {len(filtered_names)} startup names")
                return filtered_names
            else:
                logger.info("Gemini found no startup names")
                return []

        except Exception as e:
            logger.error(f"Error extracting startup names with Gemini: {e}")
            return []

    def validate_startup_names(self, names: List[str], url: str) -> List[str]:
        """
        Validate if names are actual startup companies based on context.

        Args:
            names: List of potential startup names to validate.
            url: URL of the webpage where the names were found.

        Returns:
            List of validated startup names.
        """
        if not names:
            return []

        try:
            # Create a context-aware prompt for Gemini
            names_str = ", ".join(names)

            # Create a prompt that asks the LLM to analyze the context
            prompt = f"""
            I have extracted the following potential startup company names from a webpage: {names_str}

            For each name, analyze if it appears in a context that suggests it's a real company or startup,
            not a UI element, navigation link, or common term.

            The webpage URL is: {url}

            Return ONLY the names that are likely real companies based on context, as a comma-separated list.
            If none of them appear to be real companies, return "No valid startups found".

            Be somewhat lenient in your filtering - include names that have reasonable evidence of being actual companies.
            For example, if a name appears in a list of startups or companies, or if it has a specific product or service associated with it, consider it valid.

            Example: If the webpage is about "Top 10 AI Startups" and mentions "OpenAI, Anthropic, Cohere" in a list, these should be included as valid startup names.
            However, terms like "SignUp", "ReadMore", "ContactUs" that are clearly UI elements should be excluded.
            """

            # Get response from Gemini
            response = self.api_client.flash_model.generate_content(prompt)

            # Extract validated startup names from response
            if response.text and "No valid startups found" not in response.text:
                # Split by commas and clean up
                validated_names = [name.strip() for name in response.text.split(',')]

                logger.info(f"Gemini validated {len(validated_names)} startup names")
                return validated_names
            else:
                logger.info("Gemini found no valid startup names")
                return []

        except Exception as e:
            logger.error(f"Error validating startup names with Gemini: {e}")
            return []

    def filter_relevant_startups(self, names: List[str], original_query: str) -> List[str]:
        """
        Use the Gemini Pro model to filter startup names based on relevance to the original query.

        Args:
            names: List of potential startup names to filter.
            original_query: The original search query.

        Returns:
            List of relevant startup names.
        """
        if not names:
            return []

        try:
            # Create a list of names for the prompt
            names_str = "\n".join([f"- {name}" for name in names])

            # Create a prompt for the Pro model to do deep thinking
            prompt = f"""
            I have a list of potential startup names that were extracted from search results for the query: "{original_query}"

            Here's the list of potential startup names:
            {names_str}

            Please analyze this list and identify which ones are ACTUAL LEGITIMATE STARTUPS or COMPANIES that are relevant to the query.

            Many of these names are not real startups but rather UI elements, website sections, or malformed extractions.
            For example, names like "StatesAnysphereAI" or "StatesMistral" are likely not real companies but malformed extractions where "States" was incorrectly included.

            For each name, consider:
            1. Is this a real company or startup that exists in the real world?
            2. Is it relevant to the query "{original_query}"?
            3. Does the name make sense as a company name (not a UI element or website section)?
            4. For names with prefixes like "States", "Kingdom", etc., consider if these are part of the actual company name or extraction errors.

            Return ONLY the names of LEGITIMATE STARTUPS that are RELEVANT to the query as a comma-separated list.
            If you're unsure about a name, err on the side of exclusion.
            If none of them appear to be legitimate startups relevant to the query, return "No relevant startups found".
            """

            # Use the Pro model for more complex reasoning
            response = self.api_client.pro_model.generate_content(prompt)

            # Extract filtered startup names from response
            if response.text and "No relevant startups found" not in response.text:
                # Split by commas and clean up
                filtered_names = [name.strip() for name in response.text.split(',')]

                logger.info(f"Gemini Pro filtered {len(filtered_names)} relevant startup names")
                return filtered_names
            else:
                logger.info("Gemini Pro found no relevant startup names")
                return []

        except Exception as e:
            logger.error(f"Error filtering relevant startups with Gemini Pro: {e}")
            return []

    def search(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        This method is not implemented for GeminiDataSource as it's used for
        extraction and validation, not for searching.
        """
        logger.warning("Search method not implemented for GeminiDataSource")
        return []


class WebCrawler:
    """
    Web crawler for extracting information from webpages.
    """

    def __init__(self, user_agent: Optional[str] = None):
        """
        Initialize the web crawler.

        Args:
            user_agent: User agent string for HTTP requests.
        """
        self.user_agent = user_agent or "StartupFinder/1.0"
        self.headers = {
            "User-Agent": self.user_agent
        }

        # Rate limiting parameters
        self.request_delay = 1.0  # seconds between requests
        self.last_request_time = 0

        logger.info("Initialized WebCrawler")

    def _respect_rate_limits(self):
        """Ensure we respect rate limits by adding delays between requests."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time

        if time_since_last_request < self.request_delay:
            # Sleep to respect rate limit
            sleep_time = self.request_delay - time_since_last_request
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def fetch_webpage(self, url: str) -> Tuple[Optional[str], Optional[BeautifulSoup]]:
        """
        Fetch a webpage and return its content.

        Args:
            url: URL of the webpage to fetch.

        Returns:
            Tuple of (raw_html, parsed_html) or (None, None) if fetch failed.
        """
        try:
            self._respect_rate_limits()

            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()

            # Parse the HTML
            soup = BeautifulSoup(response.text, "lxml")

            return response.text, soup

        except Exception as e:
            logger.error(f"Error fetching webpage {url}: {e}")
            return None, None

    def extract_startup_names_with_patterns(self, content: str) -> List[str]:
        """
        Extract startup names from content using regex patterns.

        Args:
            content: Text content to extract names from.

        Returns:
            List of potential startup names.
        """
        potential_names = []

        # Pattern 1: Names with domain extensions
        domain_pattern = r"([A-Z][A-Za-z0-9]+\.[a-z]{2,})\b"
        domain_matches = re.findall(domain_pattern, content)
        potential_names.extend(domain_matches)

        # Pattern 2: Names ending with AI, Labs, Technologies, etc.
        suffix_pattern = r"([A-Z][A-Za-z0-9]+\s+(?:AI|Labs|Technologies|Tech|Systems|Solutions))\b"
        suffix_matches = re.findall(suffix_pattern, content)
        potential_names.extend(suffix_matches)

        # Pattern 3: CamelCase names (common for startups)
        camelcase_pattern = r"\b([A-Z][a-z]+[A-Z][A-Za-z]*)\b"
        camelcase_matches = re.findall(camelcase_pattern, content)
        potential_names.extend(camelcase_matches)

        return potential_names

    def extract_startup_names_from_lists(self, soup: BeautifulSoup) -> List[str]:
        """
        Extract startup names from HTML list items.

        Args:
            soup: BeautifulSoup object of the parsed HTML.

        Returns:
            List of potential startup names.
        """
        potential_names = []

        # Extract from list items
        list_items = soup.find_all('li')
        for item in list_items:
            text = item.get_text().strip()

            # Look for CamelCase words that might be startup names
            matches = re.findall(r'\b([A-Z][a-z]+[A-Z][A-Za-z]*)\b', text)
            if matches:
                potential_names.extend(matches)

            # Look for names with domain extensions
            domain_matches = re.findall(r"([A-Z][A-Za-z0-9]+\.[a-z]{2,})\b", text)
            if domain_matches:
                potential_names.extend(domain_matches)

        return potential_names

    def filter_startup_names(self, names: List[str]) -> List[str]:
        """
        Filter out common words and non-startup names.

        Args:
            names: List of potential startup names.

        Returns:
            Filtered list of startup names.
        """
        # Common words to filter out
        common_words = [
            "The", "This", "That", "These", "Those", "Their", "And", "But", "For",
            "About", "Home", "Menu", "Search", "Top", "Australia", "April", "March",
            "Country", "Technology", "Application", "Contact", "Privacy", "Terms",
            "Copyright", "All", "Rights", "Reserved", "Follow", "Share", "Like",
            "Comment", "Subscribe", "Newsletter", "Sign", "Login", "Register",
            "Create", "Account", "Profile", "Settings", "Help", "Support", "FAQ",
            "Aussie", "Australian", "Tech", "Menu", "Country"
        ]

        filtered_names = []
        for name in names:
            # Skip if it's a common word or too short
            if name in common_words or len(name) < 3:
                continue

            # Skip if it's all uppercase (likely a heading)
            if name.isupper():
                continue

            # Skip if it contains newlines
            if "\n" in name:
                continue

            # Skip if it doesn't look like a company name
            if not re.match(r'^[A-Z][a-zA-Z0-9]*', name):
                continue

            # Add if not already in the list
            if name not in filtered_names:
                filtered_names.append(name)

        return filtered_names


class StartupCrawler:
    """
    Main crawler that implements the two-phase approach to startup data collection.
    """

    def __init__(self):
        """Initialize the startup crawler."""
        # Initialize data sources
        self.google_search = GoogleSearchDataSource()
        self.gemini = GeminiDataSource()
        self.web_crawler = WebCrawler()

        logger.info("Initialized StartupCrawler")

    def discover_startups(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Phase 1: Discover startup names based on the query.

        Args:
            query: Search query.
            max_results: Maximum number of startup names to discover.

        Returns:
            List of dictionaries containing startup names and basic information.
        """
        logger.info(f"Phase 1: Discovering startups for query: {query}")

        # Step 1: Search for articles about startups
        search_results = self.google_search.search(query, max_results=max_results)

        # Step 2: Extract startup names from search results
        all_validated_names = []
        startup_names_set = set()  # For quick lookup to avoid duplicates
        startup_info_map = {}  # Map of startup names to their source info

        for result in search_results:
            title = result.get("title", "")
            url = result.get("url", "")
            snippet = result.get("snippet", "")

            logger.info(f"Analyzing: {title}")

            # Skip if URL is empty
            if not url:
                continue

            # Method 1: Extract startup names using patterns
            raw_html, soup = self.web_crawler.fetch_webpage(url)
            if raw_html and soup:
                # Extract text content
                content = soup.get_text()

                # Extract startup names using patterns
                pattern_names = self.web_crawler.extract_startup_names_with_patterns(content)

                # Extract startup names from lists
                list_names = self.web_crawler.extract_startup_names_from_lists(soup)

                # Combine and filter names
                potential_names = self.web_crawler.filter_startup_names(pattern_names + list_names)

                logger.info(f"Found {len(potential_names)} potential startup names using patterns")

                # Method 2: Extract startup names using Gemini
                gemini_names = self.gemini.extract_startup_names(title, snippet, url)

                # Combine all names
                all_names = list(set(potential_names + gemini_names))

                # Method 3: Validate startup names using Gemini
                if all_names:
                    validated_names = self.gemini.validate_startup_names(all_names, url)

                    # Add validated names to our list
                    for name in validated_names:
                        if name and name not in startup_names_set:
                            startup_names_set.add(name)
                            all_validated_names.append(name)

                            # Store source info for this startup
                            startup_info_map[name] = {
                                "Source": "Google Search",
                                "Found In": title,
                                "Original URL": url
                            }

        # Step 3: Final filtering using Gemini Pro to identify legitimate startups relevant to the query
        logger.info(f"Performing final filtering of {len(all_validated_names)} startup names using Gemini Pro...")
        relevant_startups = self.gemini.filter_relevant_startups(all_validated_names, query)

        # Create the final list of startup info
        startup_info_list = []
        for name in relevant_startups:
            if name in startup_info_map:
                # Create basic info for this startup
                basic_info = {
                    "Company Name": name,
                    **startup_info_map[name]  # Unpack the stored source info
                }

                startup_info_list.append(basic_info)
                logger.info(f"Final relevant startup: {name}")

        # Log the number of startups found
        logger.info(f"Found {len(startup_info_list)} startups in discovery phase")

        return startup_info_list

    def enrich_startup_data(self, startup_info_list: List[Dict[str, Any]], max_results_per_startup: int = 3) -> List[Dict[str, Any]]:
        """
        Phase 2: Enrich startup data using the discovered startup names.

        Args:
            startup_info_list: List of dictionaries containing startup names and basic information.
            max_results_per_startup: Maximum number of results to collect per startup.

        Returns:
            List of enriched startup data dictionaries.
        """
        logger.info(f"Phase 2: Enriching data for {len(startup_info_list)} startups")

        enriched_results = []

        for startup_info in startup_info_list:
            name = startup_info.get("Company Name", "")
            if not name:
                continue

            logger.info(f"Enriching data for: {name}")

            # Create a specific query for this startup
            specific_query = f"\"{name}\" startup company information"

            # Search for specific information about this startup
            search_results = self.google_search.search(specific_query, max_results=max_results_per_startup)

            # Start with the basic info we already have
            merged_data = startup_info.copy()

            # Extract and merge information from search results
            for result in search_results:
                url = result.get("url", "")

                # Skip if URL is empty
                if not url:
                    continue

                # Fetch the webpage
                raw_html, soup = self.web_crawler.fetch_webpage(url)
                if not raw_html or not soup:
                    continue

                # Extract basic information
                try:
                    # Try to find location
                    location_patterns = [
                        r"(?:located|based|headquarters) in ([^\.]+)",
                        r"(?:HQ|Headquarters):\s*([^,\.]+(?:,\s*[A-Z]{2})?)"
                    ]

                    for pattern in location_patterns:
                        location_match = re.search(pattern, raw_html, re.IGNORECASE)
                        if location_match:
                            location = location_match.group(1).strip()
                            if "Location" not in merged_data or not merged_data["Location"]:
                                merged_data["Location"] = location
                            break

                    # Try to find founding year
                    year_pattern = r"(?:founded|established|started) in (\d{4})"
                    year_match = re.search(year_pattern, raw_html, re.IGNORECASE)
                    if year_match:
                        founded_year = year_match.group(1)
                        if "Founded Year" not in merged_data or not merged_data["Founded Year"]:
                            merged_data["Founded Year"] = founded_year

                    # Try to find website
                    if "Website" not in merged_data or not merged_data["Website"]:
                        # Use the company's URL if we found it
                        if url and name.lower() in url.lower():
                            merged_data["Website"] = url

                    # Try to find product description
                    if "Product Description" not in merged_data or not merged_data["Product Description"]:
                        # Use the snippet as a fallback
                        merged_data["Product Description"] = result.get("snippet", "")

                except Exception as e:
                    logger.error(f"Error extracting data from {url}: {e}")

            # Add to enriched results
            enriched_results.append(merged_data)

        # Log the number of enriched startups
        logger.info(f"Enriched data for {len(enriched_results)} startups")

        return enriched_results

    def search(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search for startups matching the query using the two-phase approach.

        Args:
            query: Search query.
            max_results: Maximum number of results to return.

        Returns:
            List of startup data dictionaries.
        """
        logger.info(f"Searching for startups: {query}")

        # Phase 1: Discover startup names
        startup_info_list = self.discover_startups(query, max_results=max_results)

        # Phase 2: Enrich startup data
        enriched_results = self.enrich_startup_data(startup_info_list)

        # Remove duplicates (based on company name)
        unique_results = []
        seen_companies = set()

        for result in enriched_results:
            company_name = result.get("Company Name", "").lower()

            if company_name and company_name not in seen_companies:
                seen_companies.add(company_name)
                unique_results.append(result)

        # Limit to max_results
        final_results = unique_results[:max_results]

        # Log the final number of startups
        logger.info(f"Final search results: {len(final_results)} startups")

        logger.info(f"Search complete. Found {len(final_results)} startups.")
        return final_results
