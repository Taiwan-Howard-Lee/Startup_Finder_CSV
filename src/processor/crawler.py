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
import random
import urllib.parse
import concurrent.futures
from typing import Dict, List, Optional, Any, Tuple, Set, Union, TYPE_CHECKING

# Type checking imports
if TYPE_CHECKING:
    from src.utils.metrics_collector import MetricsCollector
import logging
import hashlib
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

import google.generativeai as genai
from google.generativeai import types

import requests
import urllib3
from bs4 import BeautifulSoup
from urllib.robotparser import RobotFileParser
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Import our data extractors
from src.processor.linkedin_extractor import LinkedInExtractor
from src.processor.website_extractor import WebsiteExtractor

# Disable SSL verification warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# These will be defined later in the file
AutoScraperDataSource = None
Crawler = None
MockDataSource = None


class URLNormalizer:
    """
    Class to normalize URLs to avoid duplicates.
    """

    @staticmethod
    def normalize(url: str) -> str:
        """
        Normalize a URL to avoid duplicates.

        This function performs the following normalizations:
        1. Convert to lowercase
        2. Remove default ports (80 for HTTP, 443 for HTTPS)
        3. Remove fragments
        4. Sort query parameters
        5. Remove tracking parameters (utm_*, ref, etc.)
        6. Remove trailing slashes
        7. Handle common redirects (e.g., www vs non-www)

        Args:
            url: URL to normalize.

        Returns:
            Normalized URL.
        """
        if not url:
            return ""

        # Parse the URL
        parsed = urlparse(url)

        # Convert to lowercase
        netloc = parsed.netloc.lower()
        path = parsed.path.lower()

        # Remove default ports
        if netloc.endswith(':80') and parsed.scheme == 'http':
            netloc = netloc[:-3]
        elif netloc.endswith(':443') and parsed.scheme == 'https':
            netloc = netloc[:-4]

        # Remove trailing slashes from path
        if path.endswith('/') and len(path) > 1:
            path = path[:-1]

        # Handle query parameters
        if parsed.query:
            # Parse query parameters
            query_params = parse_qs(parsed.query)

            # Remove tracking parameters
            tracking_params = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content', 'ref', 'fbclid', 'gclid']
            for param in tracking_params:
                if param in query_params:
                    del query_params[param]

            # Sort query parameters
            sorted_query = urlencode(sorted(query_params.items()), doseq=True)
        else:
            sorted_query = ''

        # Reconstruct the URL without fragments
        normalized_url = urlunparse((parsed.scheme, netloc, path, parsed.params, sorted_query, ''))

        return normalized_url

    @staticmethod
    def get_url_fingerprint(url: str) -> str:
        """
        Generate a unique fingerprint for a URL.

        Args:
            url: URL to generate fingerprint for.

        Returns:
            URL fingerprint as a hex string.
        """
        normalized_url = URLNormalizer.normalize(url)
        return hashlib.md5(normalized_url.encode()).hexdigest()


class RobotsTxtChecker:
    """Class to check robots.txt files for crawling permissions."""

    def __init__(self):
        """Initialize the robots.txt checker."""
        self.parsers = {}  # Cache for robot parsers
        self.user_agent = "StartupFinder/1.0"
        self.disabled = False  # Disable robots.txt checking if there are persistent issues
        self.error_count = 0
        self.max_errors = 5

    def can_fetch(self, url: str) -> bool:
        """Check if the URL can be fetched according to robots.txt rules.

        Args:
            url: URL to check.

        Returns:
            True if the URL can be fetched, False otherwise.
        """
        # If robots.txt checking is disabled, always return True
        if self.disabled:
            return True

        try:
            parsed_url = urllib.parse.urlparse(url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            robots_url = f"{base_url}/robots.txt"

            # Check if we already have a parser for this domain
            if base_url not in self.parsers:
                parser = RobotFileParser()
                parser.set_url(robots_url)
                try:
                    # Use requests instead of urllib to handle SSL issues
                    response = requests.get(robots_url, timeout=5, verify=False)
                    if response.status_code == 200:
                        parser.parse(response.text.splitlines())
                    else:
                        # If robots.txt doesn't exist or can't be accessed, assume we can fetch
                        return True
                    self.parsers[base_url] = parser
                except Exception as e:
                    logger.error(f"Error reading robots.txt for {base_url}: {e}")
                    # Count errors and disable if too many
                    self.error_count += 1
                    if self.error_count >= self.max_errors:
                        logger.warning(f"Too many robots.txt errors, disabling robots.txt checking")
                        self.disabled = True
                    # If we can't read robots.txt, assume we can fetch
                    return True

            # Check if we can fetch the URL
            return self.parsers[base_url].can_fetch(self.user_agent, url)
        except Exception as e:
            logger.warning(f"Error checking robots.txt for {url}: {e}")
            # Count errors and disable if too many
            self.error_count += 1
            if self.error_count >= self.max_errors:
                logger.warning(f"Too many robots.txt errors, disabling robots.txt checking")
                self.disabled = True
            # If there's an error, assume we can fetch
            return True


class DataSource:
    """
    Base class for data sources.
    """

    def search(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search for information using this data source.

        Args:
            query: Search query.
            max_results: Maximum number of results to return.

        Returns:
            List of search results.
        """
        raise NotImplementedError("Subclasses must implement search()")


class GoogleSearchDataSource(DataSource):
    """
    Data source using Google Search API.
    """

    def __init__(self):
        """
        Initialize the Google Search data source.
        """
        self.api_key = os.environ.get("GOOGLE_SEARCH_API_KEY")
        self.cx_id = os.environ.get("GOOGLE_CX_ID")

        if not self.api_key or not self.cx_id:
            logger.warning("Google Search API key or CX ID not set. Set GOOGLE_SEARCH_API_KEY and GOOGLE_CX_ID environment variables.")

    def search(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search for information using Google Search API.

        Args:
            query: Search query.
            max_results: Maximum number of results to return.

        Returns:
            List of search results.
        """
        if not self.api_key or not self.cx_id:
            logger.error("Google Search API key or CX ID not set. Set GOOGLE_SEARCH_API_KEY and GOOGLE_CX_ID environment variables.")
            return []

        results = []

        try:
            # Build the API URL
            base_url = "https://www.googleapis.com/customsearch/v1"
            params = {
                "key": self.api_key,
                "cx": self.cx_id,
                "q": query,
                "num": min(10, max_results)  # API allows max 10 results per request
            }

            # Make the request
            response = requests.get(base_url, params=params, timeout=10)
            response.raise_for_status()

            # Parse the response
            data = response.json()

            # Extract the search results
            if "items" in data:
                for item in data["items"]:
                    result = {
                        "title": item.get("title", ""),
                        "url": item.get("link", ""),
                        "snippet": item.get("snippet", "")
                    }
                    results.append(result)

            logger.info(f"Found {len(results)} results from Google Search")
            return results[:max_results]

        except Exception as e:
            logger.error(f"Error searching Google: {e}")
            return []


class GeminiDataSource(DataSource):
    """
    Data source using Gemini API for extracting and validating information.
    """

    def __init__(self, api_client=None):
        """
        Initialize the Gemini data source.

        Args:
            api_client: Gemini API client. If None, will use environment variables.
        """
        # No need to call super().__init__ as DataSource doesn't have an __init__ method

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

    def extract_startup_names(self, title: str, snippet: str, url: str, original_query: str = "") -> List[str]:
        """
        Extract startup names from the full webpage content using Gemini API.

        Args:
            title: Title of the article or webpage.
            snippet: Snippet or description of the content.
            url: URL of the webpage.
            original_query: The original search query used to find this content.

        Returns:
            List of startup names.
        """
        # First, crawl the full webpage content using Crawl4AI
        import asyncio
        try:
            from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
        except ImportError:
            logger.warning("Crawl4AI not installed. Installing now...")
            import subprocess
            subprocess.check_call(["pip", "install", "crawl4ai"])
            from crawl4ai import AsyncWebCrawler, CrawlerRunConfig

        # Function to run the crawler asynchronously
        async def crawl_page():
            async with AsyncWebCrawler() as crawler:
                config = CrawlerRunConfig(
                    page_timeout=30000,  # 30 seconds timeout
                    wait_until='domcontentloaded',
                    magic=True  # Enable magic mode for better extraction
                )
                result = await crawler.arun(url=url, config=config)
                return result.markdown if result.success else None

        # Run the crawler
        try:
            page_content = asyncio.run(crawl_page())

            # Log successful crawl
            if page_content:
                logger.info(f"Crawl4AI successfully retrieved content from {url}")
                logger.info(f"Content length: {len(page_content)} characters")
                logger.info(f"Content preview: {page_content[:500]}...")
        except Exception as e:
            logger.error(f"Error crawling page with Crawl4AI: {e}")
            page_content = None

        # If crawling failed, try Beautiful Soup as a secondary method
        if not page_content:
            logger.warning(f"Crawl4AI failed for {url}, trying Beautiful Soup as fallback")
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

                # Parse the HTML with Beautiful Soup
                soup = BeautifulSoup(response.text, "lxml")

                # Extract text content
                # Remove script and style elements
                for script in soup(["script", "style", "nav", "footer", "header"]):
                    script.extract()

                # Get text
                text = soup.get_text(separator="\n", strip=True)

                # Clean up text
                lines = [line.strip() for line in text.splitlines() if line.strip()]
                page_content = "\n".join(lines)

                logger.info(f"Beautiful Soup successfully extracted content from {url}")
                logger.info(f"Content length: {len(page_content)} characters")
                logger.info(f"Content preview: {page_content[:500]}...")
            except Exception as e:
                logger.error(f"Beautiful Soup extraction failed for {url}: {e}")
                logger.warning(f"All extraction methods failed, falling back to search snippet")
                page_content = f"Title: {title}\nDescription: {snippet}\nURL: {url}"

        # Create a more explicit prompt for Gemini with the full page content
        prompt = f"""
        You are a startup and company name extractor. Your task is to identify and extract the names of companies mentioned in the following webpage content.

        IMPORTANT INSTRUCTIONS:
        1. Extract ALL company names from the content, including both startups and established companies
        2. Exclude website names, section headers, and navigation elements
        3. Return ONLY the company names as a comma-separated list
        4. If no companies are found, return "No startups found"
        5. Do not include any explanations, just the list of names

        URL: {url}

        CONTENT:
        {page_content}
        """

        # Get response from Gemini
        try:
            logger.info(f"Sending prompt to Gemini for startup extraction from URL: {url}")
            logger.debug(f"Prompt: {prompt[:500]}...")

            try:
                response = self.api_client.flash_model.generate_content(prompt)
                logger.info(f"Received response from Gemini: {response.text[:200]}...")
            except Exception as api_e:
                logger.error(f"Error from Gemini API: {api_e}")
                logger.error(f"Model name: {self.api_client.flash_model.model_name}")
                raise api_e

            # Extract startup names from response
            if response.text and "No startups found" not in response.text:
                # Split by commas and clean up
                startup_names = [name.strip() for name in response.text.split(',')]

                # Remove any empty strings after stripping
                startup_names = [name for name in startup_names if name]

                logger.info(f"Gemini extracted {len(startup_names)} startup names")
                return startup_names
            else:
                logger.info("Gemini found no startup names")
                return []

        except Exception as e:
            logger.error(f"Error extracting startup names with Gemini: {e}")

            # Pattern-based extraction has been completely removed from the codebase
            # If Gemini API fails, we simply return an empty list
            logger.warning("Gemini API failed. Returning empty list.")
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

            As a startup intelligence analyst, I need you to identify which of these are GENUINE STARTUPS or EARLY-STAGE COMPANIES that are DIRECTLY RELEVANT to the search query: "{original_query}".

            DEFINITION OF A STARTUP:
            - Focused on innovation, growth, and scalability
            - Typically developing new technologies, products, or business models
            - Usually smaller than established corporations

            RELEVANCE CRITERIA:
            - The startup's core business, products, or services must directly relate to "{original_query}"
            - The startup should be operating in the industry or solving problems mentioned in the query
            - The startup should be targeting the market or audience implied by the query

            FILTERING INSTRUCTIONS:
            1. ONLY include ACTUAL STARTUPS that exist in the real world (not fictional examples or UI elements)
            2. ONLY include startups that are RELEVANT to "{original_query}"
            3. Exclude established large corporations unless they are specifically relevant to the query
            4. Exclude names that are clearly website sections, UI elements, or malformed extractions
            5. Exclude generic terms, common phrases, or names that don't represent actual companies

            RESPONSE FORMAT:
            Return ONLY the names of LEGITIMATE STARTUPS that are RELEVANT to the query as a comma-separated list.
            If you're unsure about a name, err on the side of exclusion.
            If none of them appear to be legitimate startups relevant to the query, return "No relevant startups found".
            """

            # Use the Pro model with search grounding for more complex reasoning
            # Note: Search grounding is configured when the model is initialized

            # Generate content with search grounding
            response = self.api_client.pro_model.generate_content(prompt, stream=True)

            # Process the streaming response to handle search grounding
            full_response = ""
            search_queries = []

            for chunk in response:
                if hasattr(chunk, 'candidates') and chunk.candidates:
                    candidate = chunk.candidates[0]
                    if hasattr(candidate, 'content') and candidate.content:
                        content = candidate.content
                        if hasattr(content, 'parts') and content.parts:
                            for part in content.parts:
                                if hasattr(part, 'text') and part.text:
                                    full_response += part.text
                                elif hasattr(part, 'function_call'):
                                    if part.function_call.name == "search":
                                        query = part.function_call.args.get("query", "No query provided")
                                        search_queries.append(query)
                                        logger.info(f"Search grounding query: {query}")

            # Log search grounding usage
            if search_queries:
                logger.info(f"Used {len(search_queries)} search queries for grounding")

            # Extract filtered startup names from response
            if full_response and "No relevant startups found" not in full_response:
                # Split by commas and clean up
                filtered_names = [name.strip() for name in full_response.split(',')]

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

        Args:
            query: Search query.
            max_results: Maximum number of results to return.

        Returns:
            Empty list.
        """
        logger.warning(f"GeminiDataSource does not support search() for query: {query} with max_results: {max_results}")
        return []


class ContentExtractionStrategy:
    """
    Base class for content extraction strategies.
    """

    def extract_content(self, url: str, headers: Dict[str, str], session: Optional[requests.Session] = None) -> Tuple[Optional[str], Optional[BeautifulSoup]]:
        """
        Extract content from a URL.

        Args:
            url: URL to extract content from.
            headers: HTTP headers to use.
            session: Optional requests.Session to use for connection pooling.

        Returns:
            Tuple of (raw_html, parsed_html) or (None, None) if extraction failed.
        """
        raise NotImplementedError("Subclasses must implement extract_content()")


class SimpleRequestStrategy(ContentExtractionStrategy):
    """
    Simple content extraction strategy using requests.
    """

    def extract_content(self, url: str, headers: Dict[str, str], session: Optional[requests.Session] = None) -> Tuple[Optional[str], Optional[BeautifulSoup]]:
        """
        Extract content from a URL using simple requests.

        Args:
            url: URL to extract content from.
            headers: HTTP headers to use.
            session: Optional requests.Session to use for connection pooling.

        Returns:
            Tuple of (raw_html, parsed_html) or (None, None) if extraction failed.
        """
        try:
            # Use the provided session or create a new one
            req_session = session or requests.Session()

            # Make the request with a session to handle cookies
            response = req_session.get(
                url,
                headers=headers,
                timeout=10,  # Reduced timeout for faster processing
                allow_redirects=True,
                verify=False  # Disable SSL verification to avoid certificate issues
            )
            response.raise_for_status()

            # Parse the HTML
            soup = BeautifulSoup(response.text, "lxml")

            return response.text, soup
        except Exception as e:
            logger.error(f"SimpleRequestStrategy failed for {url}: {e}")
            return None, None


class AjaxRequestStrategy(ContentExtractionStrategy):
    """
    Content extraction strategy for AJAX-heavy websites.
    """

    def extract_content(self, url: str, headers: Dict[str, str], session: Optional[requests.Session] = None) -> Tuple[Optional[str], Optional[BeautifulSoup]]:
        """
        Extract content from an AJAX-heavy website.

        Args:
            url: URL to extract content from.
            headers: HTTP headers to use.
            session: Optional requests.Session to use for connection pooling.

        Returns:
            Tuple of (raw_html, parsed_html) or (None, None) if extraction failed.
        """
        try:
            # Add headers that mimic a browser better for AJAX sites
            ajax_headers = headers.copy()
            ajax_headers.update({
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Referer": url
            })

            # Use the provided session or create a new one
            req_session = session or requests.Session()

            # Make the request with a session to handle cookies
            response = req_session.get(
                url,
                headers=ajax_headers,
                timeout=15,  # Reduced timeout for faster processing (from 20)
                allow_redirects=True,
                verify=False
            )
            response.raise_for_status()

            # Parse the HTML
            soup = BeautifulSoup(response.text, "lxml")

            return response.text, soup
        except Exception as e:
            logger.error(f"AjaxRequestStrategy failed for {url}: {e}")
            return None, None


class MobileUserAgentStrategy(ContentExtractionStrategy):
    """
    Content extraction strategy using a mobile user agent.
    """

    def extract_content(self, url: str, headers: Dict[str, str], session: Optional[requests.Session] = None) -> Tuple[Optional[str], Optional[BeautifulSoup]]:
        """
        Extract content from a URL using a mobile user agent.

        Args:
            url: URL to extract content from.
            headers: HTTP headers to use.
            session: Optional requests.Session to use for connection pooling.

        Returns:
            Tuple of (raw_html, parsed_html) or (None, None) if extraction failed.
        """
        try:
            # Use a mobile user agent
            mobile_headers = headers.copy()
            mobile_headers["User-Agent"] = "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"

            # Use the provided session or create a new one
            req_session = session or requests.Session()

            # Make the request with a session to handle cookies
            response = req_session.get(
                url,
                headers=mobile_headers,
                timeout=10,  # Reduced timeout for faster processing
                allow_redirects=True,
                verify=False
            )
            response.raise_for_status()

            # Parse the HTML
            soup = BeautifulSoup(response.text, "lxml")

            return response.text, soup
        except Exception as e:
            logger.error(f"MobileUserAgentStrategy failed for {url}: {e}")
            return None, None


class WebCrawler:
    """
    Web crawler for extracting information from webpages.
    """

    def __init__(self, user_agent: Optional[str] = None, max_retries: int = 3, max_workers: int = 5):
        """
        Initialize the web crawler.

        Args:
            user_agent: User agent string for HTTP requests.
            max_retries: Maximum number of retries for failed requests.
            max_workers: Maximum number of parallel workers.
        """
        self.user_agent = user_agent or "StartupFinder/1.0"
        self.headers = {
            "User-Agent": self.user_agent
        }

        # Rate limiting parameters - optimized for speed
        self.request_delay = 0.2  # seconds between requests (reduced from 1.0)
        self.last_request_time = 0
        self.domain_last_request = {}  # Track last request time per domain
        self.domain_delay = 0.5  # seconds between requests to the same domain (reduced from 2.0)

        # Retry parameters - optimized for speed
        self.max_retries = max_retries
        self.retry_delay = 1.0  # seconds between retries (reduced from 2.0)

        # Set up connection pooling for better performance
        self.session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=0.1,  # Faster backoff
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "HEAD"]
        )

        # Mount the adapter with our retry strategy for both http and https
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=max_workers * 2,  # Double the number of workers
            pool_maxsize=max_workers * 4       # Quadruple the number of workers
        )
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Parallel processing
        self.max_workers = max_workers

        # Cache for fetched pages
        self.cache = {}
        self.url_fingerprints = set()  # Set of URL fingerprints to avoid duplicates

        # Robots.txt checker
        self.robots_checker = RobotsTxtChecker()

        # Content extraction strategies
        self.extraction_strategies = [
            SimpleRequestStrategy(),
            AjaxRequestStrategy(),
            MobileUserAgentStrategy()
        ]

        # Website structure patterns for adaptive crawling
        self.website_patterns = {
            "wordpress": ["wp-content", "wp-includes", "wp-admin"],
            "shopify": ["cdn.shopify.com", "shopify.com/s/"],
            "linkedin": ["linkedin.com/company/", "linkedin.com/in/"],
            "twitter": ["twitter.com", "t.co"],
            "facebook": ["facebook.com", "fb.com"],
            "news": ["article", "news", "blog", "post"]
        }

        logger.info(f"Initialized WebCrawler with {max_workers} workers")

    def _respect_rate_limits(self, url: str):
        """Ensure we respect rate limits by adding delays between requests.

        Args:
            url: URL being requested.
        """
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time

        # Global rate limiting
        if time_since_last_request < self.request_delay:
            # Sleep to respect global rate limit
            sleep_time = self.request_delay - time_since_last_request
            time.sleep(sleep_time)

        # Domain-specific rate limiting
        domain = urllib.parse.urlparse(url).netloc
        if domain in self.domain_last_request:
            domain_time_since_last = current_time - self.domain_last_request[domain]
            if domain_time_since_last < self.domain_delay:
                # Sleep to respect domain-specific rate limit
                domain_sleep_time = self.domain_delay - domain_time_since_last
                time.sleep(domain_sleep_time)

        # Update timestamps
        self.last_request_time = time.time()
        self.domain_last_request[domain] = time.time()

    def _detect_website_type(self, url: str) -> str:
        """
        Detect the type of website based on the URL.

        Args:
            url: URL to analyze.

        Returns:
            Website type as a string.
        """
        url_lower = url.lower()

        # Check for known website types
        for website_type, patterns in self.website_patterns.items():
            for pattern in patterns:
                if pattern in url_lower:
                    return website_type

        # Default to generic
        return "generic"

    def _choose_extraction_strategy(self, url: str, website_type: str) -> List[ContentExtractionStrategy]:
        """
        Choose the appropriate content extraction strategies based on the website type.

        Args:
            url: URL to extract content from.
            website_type: Type of website.

        Returns:
            List of content extraction strategies to try, in order of preference.
        """
        # Start with the default strategy
        strategies = [self.extraction_strategies[0]]  # SimpleRequestStrategy

        # Add specialized strategies based on website type
        if website_type == "linkedin":
            # LinkedIn often requires AJAX handling
            strategies.append(self.extraction_strategies[1])  # AjaxRequestStrategy
        elif website_type in ["twitter", "facebook"]:
            # Social media sites often work better with mobile user agents
            strategies.append(self.extraction_strategies[2])  # MobileUserAgentStrategy
        elif website_type == "news":
            # News sites might have different mobile versions
            strategies.append(self.extraction_strategies[2])  # MobileUserAgentStrategy
        else:
            # For other sites, try all strategies
            strategies = self.extraction_strategies

        return strategies

    def fetch_webpage(self, url: str, retry_count: int = 0, metrics_collector: Optional["MetricsCollector"] = None) -> Tuple[Optional[str], Optional[BeautifulSoup]]:
        """
        Fetch a webpage and return its content using a single optimized strategy.

        Args:
            url: URL of the webpage to fetch.
            retry_count: Current retry attempt (used internally).
            metrics_collector: Optional metrics collector.

        Returns:
            Tuple of (raw_html, parsed_html) or (None, None) if fetch failed.
        """
        start_time = time.time()

        # Normalize the URL to avoid duplicates
        normalized_url = URLNormalizer.normalize(url)

        # Check if we should skip this URL due to robots.txt
        if not self.robots_checker.can_fetch(url):
            if metrics_collector:
                metrics_collector.add_blocked_url(url)
            logger.info(f"Skipping {url} due to robots.txt rules")
            return None, None

        # Check cache first
        if normalized_url in self.cache:
            if metrics_collector:
                metrics_collector.urls_cache_hit += 1
            return self.cache[normalized_url]

        # Check if this URL has been processed before
        url_fingerprint = URLNormalizer.get_url_fingerprint(normalized_url)
        if url_fingerprint in self.url_fingerprints:
            if metrics_collector:
                metrics_collector.urls_skipped_duplicate += 1
            logger.info(f"Skipping duplicate URL: {url}")
            return None, None

        # Add to processed URLs
        self.url_fingerprints.add(url_fingerprint)

        # Check robots.txt - but don't retry or spend time on errors
        try:
            if not self.robots_checker.can_fetch(url):
                logger.warning(f"Robots.txt disallows fetching {url}")
                return None, None
        except Exception as e:
            # Just log and continue if there's an error with robots.txt
            logger.warning(f"Error checking robots.txt for {url}: {e}")

        # Respect rate limits - simplified
        self._respect_rate_limits(url)

        # First try with our optimized session with connection pooling
        try:
            # Use our optimized session with connection pooling
            response = self.session.get(
                url,
                headers=self.headers,
                timeout=5,  # Short timeout to avoid long waits
                allow_redirects=True,
                verify=False  # Disable SSL verification to avoid certificate issues
            )
            response.raise_for_status()

            # Parse the HTML
            soup = BeautifulSoup(response.text, "lxml")

            # Cache the result
            self.cache[normalized_url] = (response.text, soup)

            # Record metrics
            if metrics_collector:
                processing_time = time.time() - start_time
                metrics_collector.add_processed_url(url, processing_time)

            logger.info(f"Successfully fetched {url} with primary method")
            return response.text, soup

        except Exception as e:
            # If the primary method fails, try with Beautiful Soup as a fallback
            logger.warning(f"Primary fetch method failed for {url}: {e}")
            logger.info(f"Trying Beautiful Soup fallback for {url}")

            try:
                # Create a new session with different settings
                fallback_session = requests.Session()
                retry_strategy = Retry(
                    total=3,
                    backoff_factor=0.1,
                    status_forcelist=[429, 500, 502, 503, 504],
                    allowed_methods=["GET", "HEAD"]
                )
                adapter = HTTPAdapter(max_retries=retry_strategy)
                fallback_session.mount("http://", adapter)
                fallback_session.mount("https://", adapter)

                # Set headers to mimic a browser
                fallback_headers = {
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1"
                }

                # Make the request with a longer timeout
                response = fallback_session.get(
                    url,
                    headers=fallback_headers,
                    timeout=15,
                    verify=False,
                    allow_redirects=True
                )
                response.raise_for_status()

                # Parse the HTML
                soup = BeautifulSoup(response.text, "lxml")

                # Cache the result
                self.cache[normalized_url] = (response.text, soup)
                logger.info(f"Successfully fetched {url} with Beautiful Soup fallback")
                return response.text, soup

            except Exception as fallback_e:
                # If both methods fail, log the error and return None
                logger.error(f"Both primary and fallback fetch methods failed for {url}. Primary error: {e}, Fallback error: {fallback_e}")
                return None, None

    def fetch_webpages_parallel(self, urls: List[str], metrics_collector: Optional["MetricsCollector"] = None) -> Dict[str, Tuple[Optional[str], Optional[BeautifulSoup]]]:
        """
        Fetch multiple webpages in parallel using adaptive crawling techniques.

        Args:
            urls: List of URLs to fetch.
            metrics_collector: Optional metrics collector.

        Returns:
            Dictionary mapping URLs to (raw_html, parsed_html) tuples.
        """
        # Normalize URLs to avoid duplicates
        normalized_urls = []
        url_to_normalized = {}

        for url in urls:
            normalized_url = URLNormalizer.normalize(url)
            # We don't need to use the fingerprint here, just normalize the URL

            # Don't skip URLs during discovery phase
            # We want to process all URLs even if they've been seen before
            normalized_urls.append(normalized_url)
            url_to_normalized[url] = normalized_url

        # Check cache first for all URLs
        results = {}
        urls_to_fetch = []

        for url in urls:
            if url in url_to_normalized:
                normalized_url = url_to_normalized[url]

                # Check cache
                if normalized_url in self.cache:
                    results[url] = self.cache[normalized_url]
                else:
                    urls_to_fetch.append(url)

        # Fetch remaining URLs in parallel
        if urls_to_fetch:
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all fetch tasks
                # Pass metrics_collector to fetch_webpage
                future_to_url = {executor.submit(self.fetch_webpage, url, metrics_collector=metrics_collector): url for url in urls_to_fetch}

                # Process results as they complete
                for future in concurrent.futures.as_completed(future_to_url):
                    url = future_to_url[future]
                    try:
                        raw_html, soup = future.result()
                        results[url] = (raw_html, soup)
                    except Exception as e:
                        logger.error(f"Error in parallel fetch for {url}: {e}")
                        results[url] = (None, None)
                        if metrics_collector:
                            metrics_collector.add_failed_url(url)

        return results

    def extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """
        Extract links from a webpage for adaptive crawling.

        Args:
            soup: BeautifulSoup object of the webpage.
            base_url: Base URL of the webpage.

        Returns:
            List of normalized URLs.
        """
        if not soup:
            return []

        links = []

        try:
            # Parse the base URL
            parsed_base = urlparse(base_url)
            base_domain = parsed_base.netloc

            # Extract all links
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']

                # Skip empty links and javascript links
                if not href or href.startswith('javascript:') or href == '#':
                    continue

                # Handle relative URLs
                if href.startswith('/'):
                    full_url = f"{parsed_base.scheme}://{base_domain}{href}"
                elif not href.startswith(('http://', 'https://')):
                    full_url = f"{parsed_base.scheme}://{base_domain}/{href}"
                else:
                    full_url = href

                # Normalize the URL
                normalized_url = URLNormalizer.normalize(full_url)

                # Add to links if not empty
                if normalized_url:
                    links.append(normalized_url)

            # Remove duplicates while preserving order
            seen = set()
            unique_links = []
            for link in links:
                if link not in seen:
                    seen.add(link)
                    unique_links.append(link)

            return unique_links

        except Exception as e:
            logger.error(f"Error extracting links from {base_url}: {e}")
            return []

    # Pattern matching methods have been removed as they are no longer used
    # The system now relies exclusively on LLM-based extraction

    def adaptive_crawl(self, start_url: str, max_depth: int = 2, max_pages: int = 10, filter_same_domain: bool = True) -> Dict[str, Tuple[Optional[str], Optional[BeautifulSoup]]]:
        """
        Perform adaptive crawling starting from a URL.

        Args:
            start_url: URL to start crawling from.
            max_depth: Maximum crawling depth.
            max_pages: Maximum number of pages to crawl.
            filter_same_domain: Whether to only crawl pages from the same domain.

        Returns:
            Dictionary mapping URLs to (raw_html, parsed_html) tuples.
        """
        # Initialize crawling state
        to_visit = [(start_url, 0)]  # (url, depth)
        visited = set()
        results = {}

        # Get the domain of the start URL if filtering by domain
        start_domain = None
        if filter_same_domain:
            parsed_start = urlparse(start_url)
            start_domain = parsed_start.netloc

        # Crawl until we've visited max_pages or there are no more URLs to visit
        while to_visit and len(results) < max_pages:
            # Get the next URL to visit
            url, depth = to_visit.pop(0)

            # Skip if we've already visited this URL
            normalized_url = URLNormalizer.normalize(url)
            if normalized_url in visited:
                continue

            # Mark as visited
            visited.add(normalized_url)

            # Fetch the webpage
            raw_html, soup = self.fetch_webpage(url)

            # Skip if fetch failed
            if not raw_html or not soup:
                continue

            # Add to results
            results[url] = (raw_html, soup)

            # Stop if we've reached max_depth
            if depth >= max_depth:
                continue

            # Extract links for the next level
            links = self.extract_links(soup, url)

            # Filter links if needed
            if filter_same_domain and start_domain:
                links = [link for link in links if urlparse(link).netloc == start_domain]

            # Add links to the queue
            for link in links:
                if len(results) + len(to_visit) >= max_pages:
                    break

                if URLNormalizer.normalize(link) not in visited:
                    to_visit.append((link, depth + 1))

        return results

    def filter_startup_names(self, names: List[str]) -> List[str]:
        """
        Filter out common words and non-startup names.

        Note: This method is kept for backward compatibility but is no longer used
        in the main extraction flow since pattern matching has been removed.

        Args:
            names: List of potential startup names.

        Returns:
            Filtered list of startup names.
        """
        # This method is no longer used in the main extraction flow
        # but is kept for backward compatibility
        return names


class StartupCrawler:
    """
    Main crawler that implements the two-phase approach to startup data collection.
    """

    def __init__(self, max_workers: int = 5):
        """Initialize the startup crawler.

        Args:
            max_workers: Maximum number of parallel workers.
        """
        # Initialize data sources
        self.google_search = GoogleSearchDataSource()
        self.gemini = GeminiDataSource()
        self.web_crawler = WebCrawler(max_workers=max_workers)

        # Parallel processing
        self.max_workers = max_workers

        # Cache for company data
        self.company_cache = {}

        logger.info(f"Initialized StartupCrawler with {max_workers} workers")

    def discover_startups(self, query: str, max_results: int = 10, metrics_collector: Optional["MetricsCollector"] = None) -> List[Dict[str, Any]]:
        """
        Phase 1: Discover startup names based on the query.

        Args:
            query: Search query.
            max_results: Maximum number of startup names to discover.
            metrics_collector: Optional metrics collector.

        Returns:
            List of dictionaries containing startup names and basic information.
        """
        logger.info(f"Phase 1: Discovering startups for query: {query}")

        if metrics_collector:
            metrics_collector.add_query(query)
            metrics_collector.google_api_calls += 1

        # Step 1: Search for articles about startups
        search_results = self.google_search.search(query, max_results=max_results)

        # Step 2: Extract startup names from search results using parallel processing
        all_validated_names = []
        startup_names_set = set()  # For quick lookup to avoid duplicates
        startup_info_map = {}  # Map of startup names to their source info

        # Prepare URLs for parallel fetching
        urls_to_fetch = []
        url_to_result_map = {}

        for result in search_results:
            url = result.get("url", "")
            if url:
                urls_to_fetch.append(url)
                url_to_result_map[url] = result

        # Fetch webpages in parallel
        logger.info(f"Fetching {len(urls_to_fetch)} webpages in parallel")
        webpage_results = self.web_crawler.fetch_webpages_parallel(urls_to_fetch, metrics_collector=metrics_collector)

        # Process results using ThreadPoolExecutor for parallel processing
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit tasks for processing each result
            future_to_url = {}
            for url, (raw_html, soup) in webpage_results.items():
                if raw_html and soup:
                    result = url_to_result_map[url]
                    future = executor.submit(
                        self._process_search_result,
                        url,
                        result.get("title", ""),
                        result.get("snippet", ""),
                        raw_html,
                        soup,
                        query,  # Pass the original query
                        metrics_collector  # Pass metrics collector
                    )
                    future_to_url[future] = url

            # Process results as they complete
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    validated_names, source_info = future.result()

                    # Add validated names to our list
                    for name in validated_names:
                        if name and name not in startup_names_set:
                            startup_names_set.add(name)
                            all_validated_names.append(name)

                            # Store source info for this startup
                            startup_info_map[name] = source_info

                except Exception as e:
                        logger.error(f"Error processing search result for {url}: {e}")

        # Create the final list of startup info directly from validated names
        startup_info_list = []
        for name in all_validated_names:
            if name in startup_info_map:
                # Create basic info for this startup
                basic_info = {
                    "Company Name": name,
                    **startup_info_map[name]  # Unpack the stored source info
                }

                startup_info_list.append(basic_info)
                logger.info(f"Found startup: {name}")

                # Track final startup
                if metrics_collector:
                    metrics_collector.add_final_startup(name, basic_info)

        # Log the number of startups found
        logger.info(f"Found {len(startup_info_list)} startups in discovery phase")

        return startup_info_list

    def _process_search_result(self, url: str, title: str, snippet: str, raw_html: str, soup: BeautifulSoup,
                          original_query: str = "", metrics_collector: Optional["MetricsCollector"] = None) -> Tuple[List[str], Dict[str, Any]]:
        """
        Process a single search result to extract startup names.

        Args:
            url: URL of the webpage.
            title: Title of the webpage.
            snippet: Snippet from the search result.
            raw_html: Raw HTML content (not used since pattern matching was removed).
            soup: BeautifulSoup object.
            original_query: The original search query used to find this content.
            metrics_collector: Optional metrics collector.

        Returns:
            Tuple of (validated_names, source_info).
        """
        logger.info(f"Analyzing: {title}")

        # Extract startup names using Gemini
        gemini_names = self.gemini.extract_startup_names(title, snippet, url, original_query)
        logger.info(f"Gemini extracted {len(gemini_names)} startup names")

        # Track LLM-extracted names
        if metrics_collector:
            for name in gemini_names:
                metrics_collector.add_potential_startup_name(name, url)
                metrics_collector.add_llm_extracted_name(name)
                metrics_collector.gemini_api_calls += 1

        # Validate startup names using Gemini
        validated_names = []
        if gemini_names:
            validated_names = self.gemini.validate_startup_names(gemini_names, url)
            logger.info(f"Gemini validated {len(validated_names)} startup names")

            # Track validated names
            if metrics_collector:
                for name in validated_names:
                    metrics_collector.add_validated_name(name)
                metrics_collector.gemini_api_calls += 1

        # Create source info
        source_info = {
            "Source": "Google Search",
            "Found In": title,
            "Original URL": url
        }

        return validated_names, source_info

    def enrich_startup_data(self, startup_info_list: List[Dict[str, Any]], max_results_per_startup: int = 3,
                          metrics_collector: Optional["MetricsCollector"] = None) -> List[Dict[str, Any]]:
        """
        Phase 2: Enrich startup data using the discovered startup names.

        Args:
            startup_info_list: List of dictionaries containing startup names and basic information.
            max_results_per_startup: Maximum number of results to collect per startup.
            metrics_collector: Optional metrics collector.

        Returns:
            List of enriched startup data dictionaries.
        """
        logger.info(f"Phase 2: Enriching data for {len(startup_info_list)} startups")

        # Use ThreadPoolExecutor for parallel processing
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit tasks for enriching each startup
            future_to_startup = {}
            for startup_info in startup_info_list:
                name = startup_info.get("Company Name", "")
                if name:
                    future = executor.submit(
                        self._enrich_single_startup,
                        startup_info,
                        max_results_per_startup,
                        metrics_collector
                    )
                    future_to_startup[future] = name

            # Process results as they complete
            enriched_results = []
            for future in concurrent.futures.as_completed(future_to_startup):
                name = future_to_startup[future]
                try:
                    enriched_data = future.result()
                    if enriched_data:
                        enriched_results.append(enriched_data)
                except Exception as e:
                        logger.error(f"Error enriching data for {name}: {e}")

        # Log the number of enriched startups
        logger.info(f"Enriched data for {len(enriched_results)} startups")

        return enriched_results

    def _enrich_single_startup(self, startup_info: Dict[str, Any], max_results_per_startup: int,
                             metrics_collector: Optional["MetricsCollector"] = None) -> Dict[str, Any]:
        """
        Enrich data for a single startup.

        Args:
            startup_info: Dictionary containing basic startup information.
            max_results_per_startup: Maximum number of results to collect.
            metrics_collector: Optional metrics collector.

        Returns:
            Enriched startup data dictionary.
        """
        name = startup_info.get("Company Name", "")
        if not name:
            return None

        logger.info(f"Enriching data for: {name}")

        # Import the extractors
        try:
            from src.processor.website_extractor import WebsiteExtractor
            from src.processor.linkedin_extractor import LinkedInExtractor
            from src.processor.crunchbase_extractor import CrunchbaseExtractor
        except ImportError as e:
            logger.error(f"Error importing extractors: {e}")
            return startup_info

        # Create a specific query for this startup
        specific_query = f"\"{name}\" startup company information"

        # Also create a query for the official website
        website_query = f"{name} official website"

        # And a query for LinkedIn
        linkedin_query = f"site:linkedin.com/company/ \"{name}\""

        # And a query for Crunchbase
        crunchbase_query = f"site:crunchbase.com \"{name}\" company"

        # Start with the basic info we already have
        merged_data = startup_info.copy()

        # Search for specific information about this startup
        search_results = self.google_search.search(specific_query, max_results=max_results_per_startup)

        if metrics_collector:
            metrics_collector.google_api_calls += 1
            start_time = time.time()

        # Prepare URLs for parallel fetching
        urls_to_fetch = []
        url_to_result_map = {}

        for result in search_results:
            url = result.get("url", "")
            if url:
                urls_to_fetch.append(url)
                url_to_result_map[url] = result

        # Fetch webpages in parallel
        webpage_results = self.web_crawler.fetch_webpages_parallel(urls_to_fetch, metrics_collector=metrics_collector)

        # Process each result
        for url, (raw_html, soup) in webpage_results.items():
            if not raw_html or not soup:
                continue

            result = url_to_result_map[url]

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

                # Try to find LinkedIn URL
                if "LinkedIn" not in merged_data or not merged_data["LinkedIn"]:
                    # Look for LinkedIn links in the page
                    linkedin_links = []
                    if soup:
                        linkedin_links = [a['href'] for a in soup.find_all('a', href=True)
                                        if 'linkedin.com/company/' in a['href']]

                    if linkedin_links:
                        merged_data["LinkedIn"] = linkedin_links[0]
                    elif "linkedin.com/company/" in raw_html:
                        # Try to extract from raw HTML if not found in links
                        linkedin_match = re.search(r'(https?://[^\s"]+linkedin\.com/company/[^\s"]+)', raw_html)
                        if linkedin_match:
                            merged_data["LinkedIn"] = linkedin_match.group(1)

                # Try to find product description
                if "Product Description" not in merged_data or not merged_data["Product Description"]:
                    # Use the snippet as a fallback
                    merged_data["Product Description"] = result.get("snippet", "")

            except Exception as e:
                logger.error(f"Error extracting data from {url}: {e}")

        # If we still don't have a website, try a direct search
        if "Website" not in merged_data or not merged_data["Website"]:
            try:
                # Search for the official website
                website_query = f"{name} official website"
                website_results = self.google_search.search(website_query, max_results=1)
                if website_results:
                    official_url = website_results[0].get("url", "")
                    if official_url and name.lower() in official_url.lower():
                        merged_data["Website"] = official_url
            except Exception as e:
                logger.error(f"Error finding official website for {name}: {e}")

        # Get LinkedIn data if we have a LinkedIn URL
        if "LinkedIn" in merged_data and merged_data["LinkedIn"]:
            try:
                linkedin_url = merged_data["LinkedIn"]
                logger.info(f"Extracting LinkedIn data for {name} from {linkedin_url}")
                linkedin_data = LinkedInExtractor.extract_data(company_name=name, url=linkedin_url)

                # Merge LinkedIn data
                if linkedin_data:
                    for key, value in linkedin_data.items():
                        if value and (key not in merged_data or not merged_data[key]):
                            merged_data[key] = value
                    logger.info(f"Added LinkedIn data for {name}: {list(linkedin_data.keys())}")
            except Exception as e:
                logger.error(f"Error extracting LinkedIn data for {name}: {e}")

        # Get Crunchbase data using Google Search as a proxy
        try:
            logger.info(f"Searching for Crunchbase data for {name}")
            crunchbase_data = CrunchbaseExtractor.search_crunchbase_data(
                google_search=self.google_search,
                company_name=name,
                max_results=3
            )

            # Merge Crunchbase data
            if crunchbase_data:
                for key, value in crunchbase_data.items():
                    if value and (key not in merged_data or not merged_data[key]):
                        merged_data[key] = value
                logger.info(f"Added Crunchbase data for {name}: {list(crunchbase_data.keys())}")
        except Exception as e:
            logger.error(f"Error searching Crunchbase data for {name}: {e}")

        # Get website data if we have a website URL
        if "Website" in merged_data and merged_data["Website"]:
            try:
                website_url = merged_data["Website"]
                logger.info(f"Extracting website data for {name} from {website_url}")
                website_data = WebsiteExtractor.extract_data(company_name=name, url=website_url)

                # Merge website data
                if website_data:
                    for key, value in website_data.items():
                        if value and (key not in merged_data or not merged_data[key]):
                            merged_data[key] = value
                    logger.info(f"Added website data for {name}: {list(website_data.keys())}")
            except Exception as e:
                logger.error(f"Error extracting website data for {name}: {e}")

        # Record enrichment time
        if metrics_collector and 'start_time' in locals():
            enrichment_time = time.time() - start_time
            metrics_collector.startup_enrichment_times.append(enrichment_time)
            metrics_collector.startup_enrichment_time_map[name] = enrichment_time

            # Track field completion
            metrics_collector.add_final_startup(name, merged_data)

        return merged_data

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


# Define backward compatibility classes

# Define a minimal AutoScraperDataSource for backward compatibility
class AutoScraperDataSource:
    """Minimal mock implementation of AutoScraperDataSource."""

    def __init__(self, model_path=None):
        self.is_trained = False

    def train_scraper(self, url, data):
        return True

    def extract_startup_data(self, url):
        return {"Company Name": "MockStartup", "Website": url}

    def save_model(self, model_path):
        return True

    def load_model(self, model_path):
        return True

# Alias for backward compatibility
Crawler = StartupCrawler

# Mock data source for backward compatibility
class MockDataSource(DataSource):
    """Mock data source for testing."""

    def search(self, query, max_results=10):
        """Return mock search results."""
        return [
            {"title": "Mock Result 1", "url": "https://example.com/1", "snippet": "This is a mock result."},
            {"title": "Mock Result 2", "url": "https://example.com/2", "snippet": "This is another mock result."}
        ][:max_results]
