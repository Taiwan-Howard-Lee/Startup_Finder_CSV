#!/usr/bin/env python3
"""
Startup Finder

A comprehensive tool to find and gather information about startups based on search queries.
This script combines query expansion, web crawling, startup name extraction, and data enrichment
to generate a detailed CSV file with startup information.
"""

import os
import sys
import csv
import time
import logging
import argparse
import re
from typing import Dict, Any, List, Optional, Tuple

# Import setup_env to ensure API keys are available
import setup_env

# Import core functionality
from src.processor.enhanced_crawler import EnhancedStartupCrawler
from src.processor.website_extractor import WebsiteExtractor
from src.processor.linkedin_extractor import LinkedInExtractor
from src.collector.query_expander import QueryExpander
from src.utils.api_client import GeminiAPIClient
from src.utils.drive_uploader import upload_to_drive

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("startup_finder.log")
    ]
)
logger = logging.getLogger(__name__)

# Create data directory if it doesn't exist
os.makedirs("data", exist_ok=True)


def load_env_from_file():
    """Load environment variables from .env file."""
    try:
        with open(".env", "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                key, value = line.split("=", 1)
                os.environ[key] = value

        print(f"Loaded API keys from .env file")
    except Exception as e:
        print(f"Error loading environment variables: {e}")


def enrich_startup_data(crawler: EnhancedStartupCrawler, startup_name: str) -> Dict[str, Any]:
    """
    Enhanced function to enrich startup data with LinkedIn and company website information.

    Args:
        crawler: StartupCrawler instance.
        startup_name: Name of the startup.

    Returns:
        Dictionary with enriched startup data.
    """
    logger.info(f"Enriching data for: {startup_name}")

    # Start with basic info
    startup_data = {"Company Name": startup_name}

    # Step 1: Find the company's official website
    try:
        # Search for the official website
        website_query = f"{startup_name} official website"
        website_results = crawler.google_search.search(website_query, max_results=3)

        if website_results:
            for result in website_results:
                official_url = result.get("url", "")
                # Skip social media sites
                if any(domain in official_url.lower() for domain in ["linkedin.com", "twitter.com", "facebook.com"]):
                    continue
                # Check if the URL contains the company name
                normalized_name = startup_name.lower().replace(" ", "").replace("-", "").replace(".", "")
                normalized_url = official_url.lower().replace("www.", "").replace("http://", "").replace("https://", "")

                if normalized_name in normalized_url.replace(".", "") or normalized_url.split(".")[0] == normalized_name:
                    startup_data["Website"] = official_url
                    logger.info(f"Found official website for {startup_name}: {official_url}")
                    break

            # If we couldn't find a good match, use the first result
            if "Website" not in startup_data:
                startup_data["Website"] = website_results[0].get("url", "")
                logger.info(f"Using first result as website for {startup_name}: {startup_data['Website']}")
    except Exception as e:
        logger.error(f"Error finding official website for {startup_name}: {e}")

    # Step 2: Find the company's LinkedIn page
    try:
        # Search for the LinkedIn page
        linkedin_query = f"site:linkedin.com/company/ \"{startup_name}\""
        linkedin_results = crawler.google_search.search(linkedin_query, max_results=3)

        if linkedin_results:
            for result in linkedin_results:
                linkedin_url = result.get("url", "")
                if "linkedin.com/company/" in linkedin_url.lower():
                    startup_data["LinkedIn"] = linkedin_url
                    logger.info(f"Found LinkedIn page for {startup_name}: {linkedin_url}")
                    break
    except Exception as e:
        logger.error(f"Error finding LinkedIn page for {startup_name}: {e}")

    # Step 3: Extract data from the official website if available
    if "Website" in startup_data and startup_data["Website"]:
        try:
            # Fetch the website
            official_url = startup_data["Website"]
            raw_html, soup = crawler.web_crawler.fetch_webpage(official_url)

            if raw_html and soup:
                # Extract data using the website extractor
                website_data = WebsiteExtractor.extract_data(startup_name, official_url, raw_html, soup)

                # Merge the extracted data
                for key, value in website_data.items():
                    if value and (key not in startup_data or not startup_data[key]):
                        startup_data[key] = value

                logger.info(f"Extracted website data for {startup_name}: {list(website_data.keys())}")
        except Exception as e:
            logger.error(f"Error extracting data from website {startup_data.get('Website')}: {e}")

    # Step 4: Extract data from the LinkedIn page if available
    if "LinkedIn" in startup_data and startup_data["LinkedIn"]:
        try:
            # Fetch the LinkedIn page
            linkedin_url = startup_data["LinkedIn"]
            raw_html, soup = crawler.web_crawler.fetch_webpage(linkedin_url)

            if raw_html and soup:
                # Extract data using the LinkedIn extractor
                linkedin_data = LinkedInExtractor.extract_data(startup_name, linkedin_url, raw_html, soup)

                # Merge the extracted data
                for key, value in linkedin_data.items():
                    if value and (key not in startup_data or not startup_data[key]):
                        startup_data[key] = value

                logger.info(f"Extracted LinkedIn data for {startup_name}: {list(linkedin_data.keys())}")
        except Exception as e:
            logger.error(f"Error extracting data from LinkedIn {startup_data.get('LinkedIn')}: {e}")

    # Step 5: Gather additional information from general search results
    try:
        # Create a specific query for this startup
        specific_query = f"\"{startup_name}\" startup company information"

        # Search for specific information about this startup
        search_results = crawler.google_search.search(specific_query, max_results=3)

        # Prepare URLs for parallel fetching
        urls_to_fetch = []
        url_to_result_map = {}

        for result in search_results:
            url = result.get("url", "")
            if url:
                # Skip URLs we've already processed
                if url == startup_data.get("Website") or url == startup_data.get("LinkedIn"):
                    continue
                urls_to_fetch.append(url)
                url_to_result_map[url] = result

        # Fetch webpages in parallel
        webpage_results = crawler.web_crawler.fetch_webpages_parallel(urls_to_fetch)

        # Process each result
        for url, (raw_html, soup) in webpage_results.items():
            if not raw_html or not soup:
                continue

            result = url_to_result_map[url]

            # Extract basic information
            try:
                # Try to find location
                if "Location" not in startup_data or not startup_data["Location"]:
                    location_patterns = [
                        r"(?:located|based|headquarters) in ([^\.]+)",
                        r"(?:HQ|Headquarters):\s*([^,\.]+(?:,\s*[A-Z]{2})?)"
                    ]

                    for pattern in location_patterns:
                        location_match = re.search(pattern, raw_html, re.IGNORECASE)
                        if location_match:
                            startup_data["Location"] = location_match.group(1).strip()
                            break

                # Try to find founding year
                if "Founded Year" not in startup_data or not startup_data["Founded Year"]:
                    year_pattern = r"(?:founded|established|started) in (\d{4})"
                    year_match = re.search(year_pattern, raw_html, re.IGNORECASE)
                    if year_match:
                        startup_data["Founded Year"] = year_match.group(1)

                # Try to find product description
                if "Product Description" not in startup_data or not startup_data["Product Description"]:
                    # Use the snippet as a fallback
                    startup_data["Product Description"] = result.get("snippet", "")

                # Try to find industry
                if "Industry" not in startup_data or not startup_data["Industry"]:
                    industry_patterns = [
                        r"(?:industry|sector):\s*([^\.,]+)",
                        r"(?:operates|operating) in the ([^\.,]+) (?:industry|sector)"
                    ]

                    for pattern in industry_patterns:
                        industry_match = re.search(pattern, raw_html, re.IGNORECASE)
                        if industry_match:
                            startup_data["Industry"] = industry_match.group(1).strip()
                            break

                # Try to find funding information
                if "Funding" not in startup_data or not startup_data["Funding"]:
                    funding_patterns = [
                        r"(?:raised|secured|closed) (?:a|an)\s+([^\.,]+)\s+(?:funding|investment|round)",
                        r"(?:funding|investment) of\s+([^\.,]+)"
                    ]

                    for pattern in funding_patterns:
                        funding_match = re.search(pattern, raw_html, re.IGNORECASE)
                        if funding_match:
                            startup_data["Funding"] = funding_match.group(1).strip()
                            break

            except Exception as e:
                logger.error(f"Error extracting additional data from {url}: {e}")

    except Exception as e:
        logger.error(f"Error gathering additional info for {startup_name}: {e}")

    return startup_data


def batch_enrich_startups(crawler: EnhancedStartupCrawler, startup_info_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Enrich a batch of startups with detailed information.

    Args:
        crawler: StartupCrawler instance.
        startup_info_list: List of basic startup information.

    Returns:
        List of enriched startup data.
    """
    enriched_results = []

    for startup_info in startup_info_list:
        startup_name = startup_info.get("Company Name", "Unknown")
        print(f"\nProcessing: {startup_name}")
        enriched_data = enrich_startup_data(crawler, startup_name)
        enriched_results.append(enriched_data)
        print(f"Completed: {startup_name}")
        print(f"Data fields: {list(enriched_data.keys())}")

        # Add a small delay to avoid rate limiting
        time.sleep(1)

    return enriched_results


def validate_and_correct_data_with_gemini(enriched_data: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
    """
    Use Gemini 2.5 Pro to validate and correct the startup data before CSV generation.

    Args:
        enriched_data: List of enriched startup dictionaries.
        query: Original search query to provide context.

    Returns:
        List of validated and corrected startup data dictionaries.
    """
    print("\n" + "=" * 80)
    print("PHASE 3: DATA VALIDATION WITH GEMINI 2.5 PRO")
    print("=" * 80)
    print("Validating and correcting data with Gemini 2.5 Pro...")

    try:
        # Initialize the Gemini Pro model
        gemini_client = GeminiAPIClient()
        pro_model = gemini_client.pro_model

        # Define the fields we want to validate
        fields = [
            "Company Name",
            "Website",
            "LinkedIn",
            "Location",
            "Founded Year",
            "Industry",
            "Company Size",
            "Funding",
            "Product Description",
            "Products/Services",
            "Team",
            "Contact"
        ]

        # Process startups in batches to avoid overwhelming the API
        batch_size = 5
        validated_data = []

        for i in range(0, len(enriched_data), batch_size):
            batch = enriched_data[i:i+batch_size]
            print(f"Validating batch {i//batch_size + 1}/{(len(enriched_data) + batch_size - 1)//batch_size}...")

            # Convert batch to JSON for the prompt
            import json
            batch_json = json.dumps(batch, indent=2)

            # Create a prompt for Gemini Pro
            prompt = f"""
            You are a data validation expert for startup company information. I have a dataset of startups related to the query: "{query}".

            Please analyze the following startup data for anomalies, inconsistencies, or missing information, and provide a corrected version.

            For each startup, check and correct the following:
            1. Ensure company names are properly formatted and don't contain artifacts
            2. Verify websites are valid and properly formatted (add https:// if missing)
            3. Ensure LinkedIn URLs are valid
            4. Format locations consistently
            5. Ensure founded years are valid (4-digit years, not in the future)
            6. Standardize industry names
            7. Format company sizes consistently (e.g., "1-10 employees", "11-50 employees")
            8. Format funding information consistently
            9. Improve product descriptions if they're unclear or too short
            10. Fill in missing information where possible based on other fields

            Here's the data to validate and correct:
            {batch_json}

            Return ONLY the corrected data in valid JSON format, with the same structure as the input.
            Do not include any explanations or notes outside the JSON structure.
            """

            # Get response from Gemini Pro
            response = pro_model.generate_content(prompt)

            # Extract the corrected data
            try:
                # Find JSON in the response
                response_text = response.text

                # Extract JSON content (assuming it's the entire response or contained within triple backticks)
                if "```json" in response_text:
                    json_content = response_text.split("```json")[1].split("```")[0].strip()
                elif "```" in response_text:
                    json_content = response_text.split("```")[1].strip()
                else:
                    json_content = response_text.strip()

                # Parse the JSON
                corrected_batch = json.loads(json_content)

                # Add to validated data
                validated_data.extend(corrected_batch)
                print(f"Successfully validated and corrected {len(corrected_batch)} startups")

            except Exception as e:
                logger.error(f"Error parsing Gemini Pro response: {e}")
                print(f"Error parsing Gemini Pro response. Using original data for this batch.")
                # Fall back to original data for this batch
                validated_data.extend(batch)

        print(f"Data validation complete. Processed {len(validated_data)} startups.")
        return validated_data

    except Exception as e:
        logger.error(f"Error validating data with Gemini Pro: {e}")
        print(f"Error validating data with Gemini Pro: {e}")
        print("Proceeding with original data.")
        return enriched_data


def generate_csv_from_startups(enriched_data: List[Dict[str, Any]], output_file: str, create_dir: bool = True,
                           upload_to_google_drive: bool = False, credentials_path: str = 'credentials.json') -> Tuple[bool, Optional[str]]:
    """
    Generate a CSV file from the enriched startup data and optionally upload to Google Drive.

    Args:
        enriched_data: List of enriched startup dictionaries.
        output_file: Path to the output CSV file.
        create_dir: Whether to create the directory if it doesn't exist.
        upload_to_google_drive: Whether to upload the CSV to Google Drive.
        credentials_path: Path to the Google Drive API credentials file.

    Returns:
        Tuple containing:
            - bool: True if CSV generation was successful, False otherwise.
            - Optional[str]: Google Drive link if upload was successful, None otherwise.
    """
    # Define the fields we want to include in the CSV
    fields = [
        "Company Name",
        "Website",
        "LinkedIn",
        "Location",
        "Founded Year",
        "Industry",
        "Company Size",
        "Funding",
        "Product Description",
        "Products/Services",
        "Team",
        "Contact",
        "Source URL"
    ]

    drive_link = None

    try:
        # Create directory if it doesn't exist and create_dir is True
        if create_dir:
            output_dir = os.path.dirname(output_file)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
                logger.info(f"Created directory: {output_dir}")

        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fields)

            # Write the header
            writer.writeheader()

            # Write the data
            for startup in enriched_data:
                # Create a row with only the fields we want
                row = {}
                for field in fields:
                    if field == "Source URL":
                        row[field] = startup.get("Original URL", "")
                    else:
                        row[field] = startup.get(field, "")
                writer.writerow(row)

        print(f"CSV file generated: {output_file}")

        # Upload to Google Drive if requested
        if upload_to_google_drive:
            print("\nUploading CSV file to Google Drive...")
            try:
                # Create a folder name based on the search query or timestamp
                folder_name = f"Startup_Finder_{time.strftime('%Y%m%d')}"

                # Upload the file to Google Drive
                drive_link = upload_to_drive(
                    file_path=output_file,
                    credentials_path=credentials_path,
                    folder_name=folder_name
                )

                if drive_link:
                    print(f"CSV file uploaded to Google Drive successfully!")
                    print(f"Google Drive link: {drive_link}")
                else:
                    print("Failed to upload CSV file to Google Drive.")
            except Exception as e:
                print(f"Error uploading to Google Drive: {e}")

        return True, drive_link
    except Exception as e:
        print(f"Error generating CSV file: {e}")
        return False, None


def run_startup_finder(query: str, max_results: int = 5, num_expansions: int = 3,
                      output_file: Optional[str] = None, use_query_expansion: bool = True,
                      direct_startups: Optional[List[str]] = None, upload_to_google_drive: bool = False,
                      credentials_path: str = 'credentials.json'):
    """
    Run the startup finder and generate a CSV file with the results.

    Args:
        query: Search query to find startups.
        max_results: Maximum number of search results to process per query.
        num_expansions: Number of query expansions to generate.
        output_file: Path to the output CSV file.
        use_query_expansion: Whether to use query expansion.
        direct_startups: List of startup names to directly search for.
        upload_to_google_drive: Whether to upload the CSV to Google Drive.
        credentials_path: Path to the Google Drive API credentials file.

    Returns:
        bool: True if successful, False otherwise.
    """
    print("\n" + "=" * 80)
    print("STARTUP FINDER")
    print("=" * 80)

    # Load environment variables from .env file
    load_env_from_file()

    # Ensure environment is set up
    setup_env.setup_environment(test_apis=False)

    # Set default output file if not provided
    if not output_file:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_file = f"data/startups_{timestamp}.csv"

    # Add .csv extension if not provided
    if not output_file.endswith('.csv'):
        output_file += '.csv'

    # Create an enhanced crawler with maximum parallel processing
    max_workers = 20  # Use a high number of workers for maximum speed
    crawler = EnhancedStartupCrawler(max_workers=max_workers)
    print(f"Using {max_workers} parallel workers for maximum speed")

    # Initialize query expander if needed
    expanded_queries = [query]  # Default to just the original query
    if use_query_expansion:
        try:
            # Initialize the API client and query expander
            gemini_client = GeminiAPIClient()
            query_expander = QueryExpander(api_client=gemini_client)

            # Expand the query
            print("\nExpanding search query...")
            expanded_queries = query_expander.expand_query(query, num_expansions=num_expansions)

            print(f"\nExpanded queries:")
            for i, expanded_query in enumerate(expanded_queries):
                print(f"  {i+1}. {expanded_query}")
        except Exception as e:
            logger.error(f"Error expanding query: {e}")
            print(f"\nError expanding query: {e}")
            print("Proceeding with original query only.")
            expanded_queries = [query]

    # Phase 1: Discover startup names with LLM filtering
    print("\n" + "=" * 80)
    print("PHASE 1: STARTUP DISCOVERY")
    print("=" * 80)

    start_time = time.time()
    all_startup_info = []

    # If direct startups are provided, use them instead of discovery
    if direct_startups and len(direct_startups) > 0:
        print(f"Using {len(direct_startups)} directly provided startups:")
        for startup_name in direct_startups:
            print(f"- {startup_name}")
            all_startup_info.append({"Company Name": startup_name})
    else:
        print(f"Searching for: {len(expanded_queries)} queries")
        print(f"Processing up to {max_results} search results per query")
        print("This may take a few minutes...")

        # Process each expanded query
        for i, expanded_query in enumerate(expanded_queries):
            print(f"\nProcessing query {i+1}/{len(expanded_queries)}: {expanded_query}")

            # Discover startups for this query
            startup_info_list = crawler.discover_startups(expanded_query, max_results=max_results)

            # Add to the combined list, avoiding duplicates
            existing_names = {startup.get("Company Name", "").lower() for startup in all_startup_info}
            for startup in startup_info_list:
                name = startup.get("Company Name", "").lower()
                if name and name not in existing_names:
                    all_startup_info.append(startup)
                    existing_names.add(name)

            print(f"Found {len(startup_info_list)} startups from this query")
            print(f"Total unique startups so far: {len(all_startup_info)}")

    phase1_time = time.time() - start_time

    print(f"\nPhase 1 completed in {phase1_time:.2f} seconds")
    print(f"Found {len(all_startup_info)} unique startups across all queries")

    if not all_startup_info:
        print("\nNo startups found. Exiting.")
        return False

    # Phase 2: Enrich startup data
    print("\n" + "=" * 80)
    print("PHASE 2: DATA ENRICHMENT")
    print("=" * 80)
    print(f"Enriching data for {len(all_startup_info)} startups")
    print("This may take a few minutes...")

    start_time = time.time()

    # Use our custom enrichment function for direct startups
    if direct_startups:
        enriched_results = batch_enrich_startups(crawler, all_startup_info)
    else:
        # Use the crawler's built-in enrichment for discovered startups
        enriched_results = crawler.enrich_startup_data(all_startup_info)

    phase2_time = time.time() - start_time

    print(f"\nPhase 2 completed in {phase2_time:.2f} seconds")

    # Phase 3: Validate and correct data with Gemini 2.5 Pro
    start_time = time.time()
    validated_results = validate_and_correct_data_with_gemini(enriched_results, query)
    phase3_time = time.time() - start_time

    print(f"\nPhase 3 completed in {phase3_time:.2f} seconds")

    # Generate CSV file and optionally upload to Google Drive
    print("\n" + "=" * 80)
    print("GENERATING CSV FILE")
    print("=" * 80)

    success, drive_link = generate_csv_from_startups(
        validated_results,
        output_file,
        create_dir=True,
        upload_to_google_drive=upload_to_google_drive,
        credentials_path=credentials_path
    )

    if success:
        # Summary
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Original search query: {query}")
        print(f"Number of expanded queries: {len(expanded_queries)}")
        print(f"Phase 1 (Discovery) time: {phase1_time:.2f} seconds")
        print(f"Phase 2 (Enrichment) time: {phase2_time:.2f} seconds")
        print(f"Phase 3 (Validation) time: {phase3_time:.2f} seconds")
        print(f"Total time: {phase1_time + phase2_time + phase3_time:.2f} seconds")
        print(f"Startups found: {len(all_startup_info)}")
        print(f"Startups validated: {len(validated_results)}")
        print(f"CSV file generated: {output_file}")

        if drive_link:
            print(f"Google Drive link: {drive_link}")
    else:
        print("\nFailed to generate CSV file.")

    print("\n" + "=" * 80)
    print("PROCESS COMPLETE")
    print("=" * 80)

    return success


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Startup Finder - Find and gather information about startups")

    parser.add_argument("--query", "-q", type=str, help="Search query to find startups")
    parser.add_argument("--max-results", "-m", type=int, default=10,
                        help="Maximum number of search results to process per query (default: 10)")
    parser.add_argument("--num-expansions", "-n", type=int, default=10,
                        help="Number of query expansions to generate (1-100, default: 10)")
    parser.add_argument("--output-file", "-o", type=str,
                        help="Path to the output CSV file (default: data/startups_TIMESTAMP.csv)")
    parser.add_argument("--no-expansion", action="store_true",
                        help="Disable query expansion")
    parser.add_argument("--startups", "-s", type=str, nargs="+",
                        help="List of startup names to directly search for, bypassing discovery phase")
    parser.add_argument("--startups-file", "-f", type=str,
                        help="Path to a file containing startup names, one per line")
    parser.add_argument("--max-workers", "-w", type=int, default=40,
                        help="Maximum number of parallel workers for web crawling (default: 40)")
    parser.add_argument("--upload-to-drive", "-u", action="store_true",
                        help="Upload the CSV file to Google Drive")
    parser.add_argument("--credentials-path", "-c", type=str, default="credentials.json",
                        help="Path to the Google Drive API credentials file (default: credentials.json)")

    return parser.parse_args()


def interactive_mode():
    """Run the startup finder in interactive mode."""
    print("\nStartup Finder - Interactive Mode")
    print("\nChoose an option:")
    print("1. Search for startups using a query")
    print("2. Directly input startup names")
    print("3. Load startup names from a file")

    choice = input("\nEnter your choice (1-3): ").strip()

    direct_startups = None

    if choice == "2":
        # Get startup names directly from user
        print("\nEnter startup names, one per line. Enter an empty line when done.")
        startups = []
        while True:
            startup = input("Startup name: ").strip()
            if not startup:
                break
            startups.append(startup)

        if not startups:
            print("No startup names provided. Exiting.")
            return False

        direct_startups = startups
        query = "startup companies"  # Generic query

    elif choice == "3":
        # Get startup names from a file
        file_path = input("\nEnter the path to the file containing startup names: ").strip()
        if not file_path:
            print("No file path provided. Exiting.")
            return False

        try:
            with open(file_path, 'r') as f:
                startups = [line.strip() for line in f if line.strip()]

            if not startups:
                print("No startup names found in the file. Exiting.")
                return False

            print(f"Loaded {len(startups)} startup names from {file_path}")
            direct_startups = startups
            query = "startup companies"  # Generic query

        except Exception as e:
            print(f"Error loading startups file: {e}")
            return False

    else:  # Default to option 1
        # Get search query from user
        print("\nEnter a search query to find startups. Examples:")
        print("- top ai startups 2024")
        print("- fintech startups in singapore")
        print("- healthcare ai companies")
        print("- cybersecurity startups")
        query = input("\nYour search query: ").strip()

        if not query:
            print("No query provided. Exiting.")
            return False

    # Get number of results from user (only relevant for query search)
    max_results = 10
    if not direct_startups:
        try:
            max_results = int(input("\nMaximum number of search results to process (1-20, default: 10): ").strip() or "10")
            max_results = max(1, min(20, max_results))  # Ensure between 1 and 20
        except ValueError:
            print("Invalid input. Using default value of 10.")
            max_results = 10

    # Ask if user wants to use query expansion (only relevant for query search)
    use_query_expansion = True
    if not direct_startups:
        use_query_expansion = input("\nUse query expansion to improve results? (y/n, default: y): ").strip().lower() != 'n'

    # Get number of query expansions if enabled (only relevant for query search)
    num_expansions = 10  # Default
    if not direct_startups and use_query_expansion:
        try:
            num_expansions = int(input("\nNumber of query expansions (1-100, default: 10): ").strip() or "10")
            num_expansions = max(1, min(100, num_expansions))  # Ensure between 1 and 100
        except ValueError:
            print("Invalid input. Using default value of 10.")
            num_expansions = 10

    # Get number of parallel workers
    max_workers = 20  # Default
    try:
        max_workers = int(input("\nNumber of parallel workers for web crawling (1-30, default: 20): ").strip() or "20")
        max_workers = max(1, min(30, max_workers))  # Ensure between 1 and 30
    except ValueError:
        print("Invalid input. Using default value of 20.")
        max_workers = 20

    # Get output file name
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    default_filename = f"data/startups_{timestamp}.csv"  # Store in data directory by default
    output_file = input(f"\nOutput CSV file name (default: {default_filename}): ").strip() or default_filename

    # Ask if user wants to upload to Google Drive
    upload_to_drive = input("\nUpload results to Google Drive? (y/n, default: n): ").strip().lower() == 'y'

    # Get credentials path if uploading to Google Drive
    credentials_path = "credentials.json"  # Default
    if upload_to_drive:
        credentials_path = input(f"\nPath to Google Drive credentials file (default: {credentials_path}): ").strip() or credentials_path
        print("\nNote: You will need to authenticate with Google when the program runs.")

    # Run the startup finder
    return run_startup_finder(
        query=query,
        max_results=max_results,
        num_expansions=num_expansions,
        output_file=output_file,
        use_query_expansion=use_query_expansion,
        direct_startups=direct_startups,
        upload_to_google_drive=upload_to_drive,
        credentials_path=credentials_path
    )


if __name__ == "__main__":
    # Parse command line arguments
    args = parse_arguments()

    # Get direct startups if provided
    direct_startups = None
    if args.startups:
        direct_startups = args.startups
    elif args.startups_file:
        try:
            with open(args.startups_file, 'r') as f:
                direct_startups = [line.strip() for line in f if line.strip()]
            print(f"Loaded {len(direct_startups)} startup names from {args.startups_file}")
        except Exception as e:
            print(f"Error loading startups file: {e}")

    # If query is provided or direct startups are provided, run in command line mode
    if args.query or direct_startups:
        # If no query is provided but direct startups are, use a generic query
        query = args.query or "startup companies"
        run_startup_finder(
            query=query,
            max_results=args.max_results,
            num_expansions=args.num_expansions,
            output_file=args.output_file,
            use_query_expansion=not args.no_expansion,
            direct_startups=direct_startups,
            upload_to_google_drive=args.upload_to_drive,
            credentials_path=args.credentials_path
        )
    # Otherwise, run in interactive mode
    else:
        interactive_mode()
