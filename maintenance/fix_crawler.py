"""
Script to fix the _enrich_single_startup method in crawler.py
"""

# Read the file
with open('src/processor/crawler.py', 'r') as f:
    content = f.read()

# Find the method definition
start_marker = "    def _enrich_single_startup"
end_marker = "        return merged_data"

# Define the correct implementation
correct_implementation = """    def _enrich_single_startup(self, startup_info: Dict[str, Any], max_results_per_startup: int) -> Dict[str, Any]:
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
        
        # Create a specific query for this startup
        specific_query = f"\\\"{name}\\\" startup company information"
        
        # Search for specific information about this startup
        search_results = self.google_search.search(specific_query, max_results=max_results_per_startup)
        
        # Start with the basic info we already have
        merged_data = startup_info.copy()
        
        # Prepare URLs for parallel fetching
        urls_to_fetch = []
        url_to_result_map = {}
        
        for result in search_results:
            url = result.get("url", "")
            if url:
                urls_to_fetch.append(url)
                url_to_result_map[url] = result
        
        # Fetch webpages in parallel
        webpage_results = self.web_crawler.fetch_webpages_parallel(urls_to_fetch)
        
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
                    r"(?:HQ|Headquarters):\\s*([^,\.]+(?:,\\s*[A-Z]{2})?)" 
                ]

                for pattern in location_patterns:
                    location_match = re.search(pattern, raw_html, re.IGNORECASE)
                    if location_match:
                        location = location_match.group(1).strip()
                        if "Location" not in merged_data or not merged_data["Location"]:
                            merged_data["Location"] = location
                        break

                # Try to find founding year
                year_pattern = r"(?:founded|established|started) in (\\d{4})"
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
                        linkedin_match = re.search(r'(https?://[^\\s"]+linkedin\\.com/company/[^\\s"]+)', raw_html)
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
        
        return merged_data"""

# Find the start and end positions of the method
start_pos = content.find(start_marker)
if start_pos == -1:
    print("Could not find the method definition")
    exit(1)

end_pos = content.find(end_marker, start_pos)
if end_pos == -1:
    print("Could not find the end of the method")
    exit(1)
end_pos += len(end_marker)

# Replace the method with the correct implementation
new_content = content[:start_pos] + correct_implementation + content[end_pos:]

# Write the fixed content back to the file
with open('src/processor/crawler.py', 'w') as f:
    f.write(new_content)

print("Fixed the _enrich_single_startup method in crawler.py")
