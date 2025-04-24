"""
Script to update the _enrich_single_startup method in the crawler.py file.
"""

import os
import re
import sys

def update_enrichment_method():
    """Update the _enrich_single_startup method in the crawler.py file."""
    # Path to the crawler.py file
    crawler_path = os.path.join("src", "processor", "crawler.py")

    # Read the crawler.py file
    with open(crawler_path, "r") as f:
        content = f.read()

    # Define the pattern to match the _enrich_single_startup method
    pattern = r"    def _enrich_single_startup\(self, startup_info: Dict\[str, Any\], max_results_per_startup: int\) -> Dict\[str, Any\]:(.*?)    def search\("

    # Define the replacement method
    replacement = """    def _enrich_single_startup(self, startup_info: Dict[str, Any], max_results_per_startup: int) -> Dict[str, Any]:
        \"\"\"
        Enrich data for a single startup.

        Args:
            startup_info: Dictionary containing basic startup information.
            max_results_per_startup: Maximum number of results to collect.

        Returns:
            Enriched startup data dictionary.
        \"\"\"
        name = startup_info.get("Company Name", "")
        if not name:
            return None

        logger.info(f"Enriching data for: {name}")

        # Start with the basic info we already have
        merged_data = startup_info.copy()

        # Step 1: Search specifically for the official website
        website_url = None
        try:
            website_query = f"\\"{name}\\" official website"
            logger.info(f"Searching for official website: {website_query}")
            website_results = self.google_search.search(website_query, max_results=2)

            if website_results:
                for result in website_results:
                    candidate_url = result.get("url", "")
                    # Check if URL likely belongs to the company
                    if candidate_url and name.lower().replace(" ", "") in candidate_url.lower().replace(" ", ""):
                        if "linkedin.com" not in candidate_url and "facebook.com" not in candidate_url and "twitter.com" not in candidate_url:
                            website_url = candidate_url
                            merged_data["Website"] = website_url
                            logger.info(f"Found official website: {website_url}")
                            break
        except Exception as e:
            logger.error(f"Error finding official website for {name}: {e}")

        # Step 2: Search specifically for LinkedIn profile
        linkedin_url = None
        try:
            linkedin_query = f"site:linkedin.com/company/ \\"{name}\\""
            logger.info(f"Searching for LinkedIn profile: {linkedin_query}")
            linkedin_results = self.google_search.search(linkedin_query, max_results=2)

            if linkedin_results:
                for result in linkedin_results:
                    candidate_url = result.get("url", "")
                    if candidate_url and "linkedin.com/company/" in candidate_url:
                        linkedin_url = candidate_url
                        merged_data["LinkedIn"] = linkedin_url
                        logger.info(f"Found LinkedIn profile: {linkedin_url}")
                        break
        except Exception as e:
            logger.error(f"Error finding LinkedIn profile for {name}: {e}")

        # Step 3: Fetch and process the official website and LinkedIn profile in parallel
        urls_to_fetch = []
        if website_url:
            urls_to_fetch.append(website_url)
        if linkedin_url:
            urls_to_fetch.append(linkedin_url)

        if urls_to_fetch:
            # Fetch webpages in parallel
            webpage_results = self.web_crawler.fetch_webpages_parallel(urls_to_fetch)

            # Process official website
            if website_url and website_url in webpage_results:
                raw_html, soup = webpage_results[website_url]
                if raw_html and soup:
                    website_data = WebsiteExtractor.extract_data(name, website_url, raw_html, soup)
                    # Merge website data, but don't overwrite existing data
                    for key, value in website_data.items():
                        if key not in merged_data or not merged_data[key]:
                            merged_data[key] = value

            # Process LinkedIn profile
            if linkedin_url and linkedin_url in webpage_results:
                raw_html, soup = webpage_results[linkedin_url]
                if raw_html and soup:
                    linkedin_data = LinkedInExtractor.extract_data(name, linkedin_url, raw_html, soup)
                    # Merge LinkedIn data, but don't overwrite existing data
                    for key, value in linkedin_data.items():
                        if key not in merged_data or not merged_data[key]:
                            merged_data[key] = value

        # Step 4: If we still need more data, do a general search
        if not website_url or not linkedin_url or "Product Description" not in merged_data:
            # Create a specific query for this startup
            specific_query = f"\\"{name}\\" startup company information"
            logger.info(f"Performing general search: {specific_query}")

            # Search for specific information about this startup
            search_results = self.google_search.search(specific_query, max_results=max_results_per_startup)

            # Prepare URLs for parallel fetching
            urls_to_fetch = []
            url_to_result_map = {}

            for result in search_results:
                url = result.get("url", "")
                if url and (not website_url or url != website_url) and (not linkedin_url or url != linkedin_url):
                    urls_to_fetch.append(url)
                    url_to_result_map[url] = result

            if urls_to_fetch:
                # Fetch webpages in parallel
                additional_results = self.web_crawler.fetch_webpages_parallel(urls_to_fetch)

                # Process each result
                for url, (raw_html, soup) in additional_results.items():
                    if not raw_html or not soup:
                        continue

                    result = url_to_result_map[url]

                    # Extract basic information
                    try:
                        # Try to find location
                        if "Location" not in merged_data or not merged_data["Location"]:
                            location_patterns = [
                                r"(?:located|based|headquarters) in ([^\.]+)",
                                r"(?:HQ|Headquarters):\\s*([^,\.]+(?:,\\s*[A-Z]{2})?)"
                            ]

                            for pattern in location_patterns:
                                location_match = re.search(pattern, raw_html, re.IGNORECASE)
                                if location_match:
                                    merged_data["Location"] = location_match.group(1).strip()
                                    break

                        # Try to find founding year
                        if "Founded Year" not in merged_data or not merged_data["Founded Year"]:
                            year_pattern = r"(?:founded|established|started) in (\\d{4})"
                            year_match = re.search(year_pattern, raw_html, re.IGNORECASE)
                            if year_match:
                                merged_data["Founded Year"] = year_match.group(1)

                        # Try to find product description
                        if "Product Description" not in merged_data or not merged_data["Product Description"]:
                            merged_data["Product Description"] = result.get("snippet", "")

                    except Exception as e:
                        logger.error(f"Error extracting data from {url}: {e}")

        return merged_data

    def search("""

    # Replace the method in the content
    updated_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

    # Write the updated content back to the file
    with open(crawler_path, "w") as f:
        f.write(updated_content)

    print(f"Updated _enrich_single_startup method in {crawler_path}")

if __name__ == "__main__":
    update_enrichment_method()
