"""
Enhanced Startup Crawler

This module provides an enhanced version of the StartupCrawler that uses
Google Search as a proxy to extract data from LinkedIn and Crunchbase.
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from bs4 import BeautifulSoup

from src.processor.crawler import StartupCrawler
from src.processor.website_extractor import WebsiteExtractor
from src.processor.linkedin_extractor import LinkedInExtractor
from src.processor.crunchbase_extractor import CrunchbaseExtractor
from src.utils.api_client import GeminiAPIClient

# Set up logging
logger = logging.getLogger(__name__)

class EnhancedStartupCrawler(StartupCrawler):
    """
    Enhanced version of the StartupCrawler that uses Google Search as a proxy
    to extract data from LinkedIn and Crunchbase.
    """

    def enrich_startup_data(self, startup_info_list: List[Dict[str, Any]], max_results_per_startup: int = 5) -> List[Dict[str, Any]]:
        """
        Enrich a list of startup data with additional information.

        Args:
            startup_info_list: List of dictionaries containing basic startup information.
            max_results_per_startup: Maximum number of search results to process per startup.

        Returns:
            List of enriched startup data dictionaries.
        """
        enriched_results = []

        for startup_info in startup_info_list:
            enriched_data = self._enrich_single_startup_enhanced(startup_info, max_results_per_startup)
            if enriched_data:
                enriched_results.append(enriched_data)

        logger.info(f"Enriched data for {len(enriched_results)} startups")

        return enriched_results

    def _enrich_single_startup_enhanced(self, startup_info: Dict[str, Any], max_results_per_startup: int) -> Dict[str, Any]:
        """
        Enrich data for a single startup using enhanced methods.

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

        # Step 1: Find the company's official website
        merged_data = self._find_official_website(name, merged_data)

        # Step 2: Find the company's LinkedIn page and extract data
        merged_data = self._extract_linkedin_data(name, merged_data)

        # Step 3: Extract data from Crunchbase
        merged_data = self._extract_crunchbase_data(name, merged_data)

        # Step 4: Extract data from the official website if available
        merged_data = self._extract_website_data(name, merged_data)

        # Step 5: Gather additional information from general search results
        merged_data = self._gather_additional_info(name, merged_data, max_results_per_startup)

        return merged_data

    def _find_official_website(self, company_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Find the official website for a company.

        Args:
            company_name: Name of the company.
            data: Current data dictionary.

        Returns:
            Updated data dictionary.
        """
        if "Website" in data and data["Website"]:
            return data

        try:
            # Try different search queries to find the official website
            search_queries = [
                f"\"{company_name}\" official website",
                f"{company_name} company website",
                f"{company_name} homepage"
            ]

            for query in search_queries:
                website_results = self.google_search.search(query, max_results=3)

                if website_results:
                    for result in website_results:
                        url = result.get("url", "")

                        # Skip LinkedIn, Twitter, Facebook, etc.
                        if any(domain in url.lower() for domain in ["linkedin.com", "twitter.com", "facebook.com", "instagram.com", "youtube.com", "crunchbase.com"]):
                            continue

                        # Check if the URL contains the company name or looks like an official website
                        normalized_company = company_name.lower().replace(" ", "").replace("-", "").replace(".", "")
                        normalized_url = url.lower().replace("www.", "").replace("http://", "").replace("https://", "")

                        # If the URL contains the company name or starts with the company name, it's likely the official website
                        if normalized_company in normalized_url.replace(".", "") or normalized_url.split(".")[0] == normalized_company:
                            data["Website"] = url
                            logger.info(f"Found official website for {company_name}: {url}")
                            return data

            # If we couldn't find a good match, return the first result from the first query
            if website_results:
                url = website_results[0].get("url", "")
                if not any(domain in url.lower() for domain in ["linkedin.com", "twitter.com", "facebook.com", "instagram.com", "youtube.com", "crunchbase.com"]):
                    data["Website"] = url
                    logger.info(f"Using first result as website for {company_name}: {url}")

            return data
        except Exception as e:
            logger.error(f"Error finding official website for {company_name}: {e}")
            return data

    def _extract_linkedin_data(self, company_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract data from LinkedIn using Google Search as a proxy and LLM for extraction.

        Args:
            company_name: Name of the company.
            data: Current data dictionary.

        Returns:
            Updated data dictionary.
        """
        try:
            # Create an API client instance for LLM extraction
            api_client = GeminiAPIClient()

            # Search for LinkedIn information
            linkedin_query = f"site:linkedin.com/company/ \"{company_name}\""
            linkedin_results = self.google_search.search(linkedin_query, max_results=3)

            if linkedin_results:
                # First, try to get the LinkedIn URL if we don't have it
                if "LinkedIn" not in data or not data["LinkedIn"]:
                    for result in linkedin_results:
                        url = result.get("url", "")
                        if "linkedin.com/company/" in url:
                            data["LinkedIn"] = url
                            logger.info(f"Found LinkedIn page for {company_name}: {url}")
                            break

                # Combine all snippets into a single text for better context
                combined_text = f"LinkedIn information for {company_name}:\n\n"

                for result in linkedin_results:
                    title = result.get("title", "")
                    snippet = result.get("snippet", "")
                    url = result.get("url", "")

                    combined_text += f"Title: {title}\n"
                    combined_text += f"URL: {url}\n"
                    combined_text += f"Snippet: {snippet}\n\n"

                # Define the fields we want to extract
                fields_to_extract = [
                    "Company Description",
                    "Company Size",
                    "Industry",
                    "Founded Year",
                    "Location",
                    "Founders"
                ]

                # Use the LLM to extract structured data
                linkedin_data = api_client.extract_structured_data(
                    company_name=company_name,
                    source_type="LinkedIn Search Results",
                    content=combined_text,
                    fields=fields_to_extract
                )

                # Merge the LinkedIn data with the main data
                for key, value in linkedin_data.items():
                    if value and (key not in data or not data[key]):
                        data[key] = value

                logger.info(f"Extracted LinkedIn data for {company_name} using LLM: {list(linkedin_data.keys())}")

            return data
        except Exception as e:
            logger.error(f"Error extracting LinkedIn data for {company_name}: {e}")
            return data

    def _extract_crunchbase_data(self, company_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract data from Crunchbase using Google Search as a proxy and LLM for extraction.

        Args:
            company_name: Name of the company.
            data: Current data dictionary.

        Returns:
            Updated data dictionary.
        """
        try:
            # Create an API client instance for LLM extraction
            api_client = GeminiAPIClient()

            # Use the Crunchbase extractor to search for data from Google Search snippets
            crunchbase_data = CrunchbaseExtractor.search_crunchbase_data(
                google_search=self.google_search,
                company_name=company_name,
                max_results=3,
                api_client=api_client
            )

            # Try an alternative search query to get more information about funding
            try:
                funding_query = f"\"{company_name}\" funding raised crunchbase"
                funding_results = self.google_search.search(funding_query, max_results=3)

                if funding_results and "Funding" not in crunchbase_data:
                    # Combine all snippets into a single text for better context
                    combined_text = f"Funding information for {company_name}:\n\n"

                    for result in funding_results:
                        title = result.get("title", "")
                        snippet = result.get("snippet", "")
                        url = result.get("url", "")

                        combined_text += f"Title: {title}\n"
                        combined_text += f"URL: {url}\n"
                        combined_text += f"Snippet: {snippet}\n\n"

                    # Use the LLM to extract funding information
                    funding_data = api_client.extract_structured_data(
                        company_name=company_name,
                        source_type="Funding Search Results",
                        content=combined_text,
                        fields=["Funding", "Funding Rounds", "Investors"]
                    )

                    # Add any new funding data
                    for key, value in funding_data.items():
                        if value and key not in crunchbase_data:
                            crunchbase_data[key] = value
            except Exception as e:
                logger.warning(f"Error getting additional funding data for {company_name}: {e}")

            # Merge the Crunchbase data with the main data
            for key, value in crunchbase_data.items():
                if value and (key not in data or not data[key]):
                    data[key] = value

            logger.info(f"Extracted Crunchbase data for {company_name} using LLM: {list(crunchbase_data.keys())}")
            return data
        except Exception as e:
            logger.error(f"Error extracting Crunchbase data for {company_name}: {e}")
            return data

    def _extract_website_data(self, company_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract data from the company's official website using LLM.

        Args:
            company_name: Name of the company.
            data: Current data dictionary.

        Returns:
            Updated data dictionary.
        """
        if "Website" in data and data["Website"]:
            try:
                # Create an API client instance for LLM extraction
                api_client = GeminiAPIClient()

                # Fetch the website
                official_url = data["Website"]
                raw_html, soup = self.web_crawler.fetch_webpage(official_url)

                if raw_html and soup:
                    # Extract data using the website extractor with LLM
                    website_data = WebsiteExtractor.extract_data(
                        company_name=company_name,
                        url=official_url,
                        raw_html=raw_html,
                        soup=soup,
                        api_client=api_client
                    )

                    # Merge the extracted data
                    for key, value in website_data.items():
                        if value and (key not in data or not data[key]):
                            data[key] = value

                    logger.info(f"Extracted website data for {company_name} using LLM: {list(website_data.keys())}")
                else:
                    # If we couldn't fetch the website directly, try to get data from Google's cached version
                    try:
                        cache_query = f"cache:{official_url}"
                        cache_results = self.google_search.search(cache_query, max_results=1)

                        if cache_results:
                            # Extract basic info from the snippet using LLM
                            snippet = cache_results[0].get("snippet", "")
                            title = cache_results[0].get("title", "")

                            # Combine into text for LLM processing
                            cache_text = f"Title: {title}\nSnippet: {snippet}\n"

                            # Use LLM to extract data from cache
                            cache_data = api_client.extract_structured_data(
                                company_name=company_name,
                                source_type="Website Cache",
                                content=cache_text,
                                fields=["Company Description", "Products/Services"]
                            )

                            # Merge cache data
                            for key, value in cache_data.items():
                                if value and (key not in data or not data[key]):
                                    data[key] = value

                            logger.info(f"Used Google cache with LLM for {company_name} website data")
                    except Exception as e:
                        logger.warning(f"Error getting cached website data for {company_name}: {e}")
            except Exception as e:
                logger.error(f"Error extracting data from website {data.get('Website')}: {e}")

                # If direct access fails, try an alternative approach using Google search
                try:
                    about_query = f"site:{data['Website']} about {company_name}"
                    about_results = self.google_search.search(about_query, max_results=2)

                    if about_results:
                        # Combine all snippets into a single text for better context
                        about_text = f"About information for {company_name} from website {data['Website']}:\n\n"

                        for result in about_results:
                            title = result.get("title", "")
                            snippet = result.get("snippet", "")
                            url = result.get("url", "")

                            about_text += f"Title: {title}\n"
                            about_text += f"URL: {url}\n"
                            about_text += f"Snippet: {snippet}\n\n"

                        # Use LLM to extract data from about page
                        about_data = api_client.extract_structured_data(
                            company_name=company_name,
                            source_type="Website About Page",
                            content=about_text,
                            fields=["Company Description", "Location", "Founded Year", "Products/Services"]
                        )

                        # Merge about data
                        for key, value in about_data.items():
                            if value and (key not in data or not data[key]):
                                data[key] = value

                        logger.info(f"Used Google search with LLM for {company_name} website data")
                except Exception as e:
                    logger.warning(f"Error getting alternative website data for {company_name}: {e}")

        return data

    def _gather_additional_info(self, company_name: str, data: Dict[str, Any], max_results: int) -> Dict[str, Any]:
        """
        Gather additional information about a company from general search results using LLM.

        Args:
            company_name: Name of the company.
            data: Current data dictionary.
            max_results: Maximum number of search results to process.

        Returns:
            Updated data dictionary.
        """
        try:
            # Create an API client instance for LLM extraction
            api_client = GeminiAPIClient()

            # Create a specific query for this startup
            specific_query = f"\"{company_name}\" startup company information"

            # Search for specific information about this startup
            search_results = self.google_search.search(specific_query, max_results=max_results)

            if not search_results:
                return data

            # First, try to extract information from search snippets using LLM
            combined_text = f"General information for {company_name}:\n\n"

            for result in search_results:
                title = result.get("title", "")
                snippet = result.get("snippet", "")
                url = result.get("url", "")

                combined_text += f"Title: {title}\n"
                combined_text += f"URL: {url}\n"
                combined_text += f"Snippet: {snippet}\n\n"

            # Define fields that might be missing from our data
            missing_fields = []
            for field in ["Location", "Founded Year", "Industry", "Funding", "Company Description", "Products/Services"]:
                if field not in data or not data[field]:
                    missing_fields.append(field)

            # If we have missing fields, try to extract them from search results
            if missing_fields:
                # Use LLM to extract data from search results
                search_data = api_client.extract_structured_data(
                    company_name=company_name,
                    source_type="General Search Results",
                    content=combined_text,
                    fields=missing_fields
                )

                # Merge search data
                for key, value in search_data.items():
                    if value and (key not in data or not data[key]):
                        data[key] = value

                logger.info(f"Extracted additional data for {company_name} from search snippets using LLM: {list(search_data.keys())}")

            # Prepare URLs for parallel fetching (for more detailed extraction)
            urls_to_fetch = []
            url_to_result_map = {}

            for result in search_results:
                url = result.get("url", "")
                if url:
                    # Skip URLs we've already processed
                    if url == data.get("Website") or url == data.get("LinkedIn"):
                        continue
                    urls_to_fetch.append(url)
                    url_to_result_map[url] = result

            # Fetch webpages in parallel
            webpage_results = self.web_crawler.fetch_webpages_parallel(urls_to_fetch)

            # Process each result with LLM
            for url, (raw_html, soup) in webpage_results.items():
                if not raw_html or not soup:
                    continue

                # Check if we still have missing fields
                missing_fields = []
                for field in ["Location", "Founded Year", "Industry", "Funding", "Company Description", "Products/Services"]:
                    if field not in data or not data[field]:
                        missing_fields.append(field)

                # If we have all fields, we can stop
                if not missing_fields:
                    break

                try:
                    # Extract text content from the page
                    text_content = ""

                    # Add the title
                    if soup.title:
                        text_content += f"Title: {soup.title.get_text()}\n\n"

                    # Add meta descriptions
                    meta_desc = soup.find('meta', attrs={'name': 'description'})
                    if meta_desc and 'content' in meta_desc.attrs:
                        text_content += f"Meta Description: {meta_desc['content']}\n\n"

                    # Extract text from main content
                    main_content = soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                    for element in main_content:
                        if element.get_text().strip():
                            text_content += element.get_text().strip() + "\n"

                    # If we couldn't extract meaningful text, skip this page
                    if len(text_content) < 100:
                        continue

                    # Use LLM to extract data from the page
                    page_data = api_client.extract_structured_data(
                        company_name=company_name,
                        source_type="Additional Webpage",
                        content=text_content,
                        fields=missing_fields
                    )

                    # Merge page data
                    for key, value in page_data.items():
                        if value and (key not in data or not data[key]):
                            data[key] = value

                    logger.info(f"Extracted additional data for {company_name} from {url} using LLM: {list(page_data.keys())}")

                except Exception as e:
                    logger.error(f"Error extracting additional data from {url}: {e}")

        except Exception as e:
            logger.error(f"Error gathering additional info for {company_name}: {e}")

        return data
