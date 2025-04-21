"""
Data Cleaner for Startup Intelligence Finder.

This module provides utilities for cleaning, normalizing, and validating
startup data collected from various sources.
"""

import json
import re
import datetime
from typing import Any, Dict, List, Optional, Union

import pandas as pd


class DataCleaner:
    """
    A utility class for cleaning and normalizing startup data.
    
    This class provides methods to clean, validate, and format data
    collected about startups from various sources.
    """
    
    def __init__(self, default_fields: Optional[List[str]] = None):
        """
        Initialize the DataCleaner.
        
        Args:
            default_fields: List of default fields to include in cleaned data.
                           If None, a basic set of fields will be used.
        """
        self.default_fields = default_fields or [
            "Company Name",
            "Founded Year",
            "Location",
            "Website",
        ]
        
        # Define field-specific cleaning functions
        self.cleaning_functions = {
            "Company Name": self.clean_company_name,
            "Founded Year": self.clean_year,
            "Location": self.clean_location,
            "Website": self.clean_website,
            "Founders": self.clean_person_names,
            "Funding Information": self.clean_funding_info,
            "Technology Stack": self.clean_tech_stack,
            "Product Description": self.clean_description,
            "Team Size": self.clean_team_size,
            "Social Media": self.clean_social_media,
            "Latest News": self.clean_description,
            "Competitors": self.clean_company_list,
            "Business Model": self.clean_description,
            "Target Market": self.clean_description
        }
    
    def clean_company_name(self, name: str) -> str:
        """
        Clean and normalize a company name.
        
        Args:
            name: The raw company name.
            
        Returns:
            Cleaned company name.
        """
        # Remove common legal suffixes
        suffixes = [
            "Inc", "LLC", "Ltd", "Limited", "Corp", "Corporation",
            "Co", "Company", "GmbH", "S.A.", "B.V.", "AG"
        ]
        
        cleaned_name = name.strip()
        
        # Remove trailing periods
        cleaned_name = cleaned_name.rstrip(".")
        
        # Remove legal suffixes
        for suffix in suffixes:
            # Match suffix at the end of the name, possibly with punctuation
            pattern = rf"\s+{re.escape(suffix)}\.?$"
            cleaned_name = re.sub(pattern, "", cleaned_name, flags=re.IGNORECASE)
        
        return cleaned_name.strip()
    
    def clean_year(self, year_str: str) -> Optional[int]:
        """
        Clean and validate a year value.
        
        Args:
            year_str: The raw year string.
            
        Returns:
            Cleaned year as integer, or None if invalid.
        """
        # Extract 4-digit year
        year_match = re.search(r"\b(19|20)\d{2}\b", str(year_str))
        
        if year_match:
            year = int(year_match.group(0))
            # Validate year is reasonable (not in the future)
            current_year = datetime.datetime.now().year
            if 1900 <= year <= current_year:
                return year
        
        return None
    
    def clean_location(self, location: str) -> str:
        """
        Clean and normalize a location string.
        
        Args:
            location: The raw location string.
            
        Returns:
            Cleaned location.
        """
        # Remove common prefixes
        prefixes = ["Located in", "Based in", "HQ in", "Headquarters in"]
        cleaned_location = str(location).strip()
        
        for prefix in prefixes:
            if cleaned_location.lower().startswith(prefix.lower()):
                cleaned_location = cleaned_location[len(prefix):].strip()
        
        # Remove trailing commas and periods
        cleaned_location = cleaned_location.rstrip(".,")
        
        return cleaned_location
    
    def clean_website(self, website: str) -> Optional[str]:
        """
        Clean and validate a website URL.
        
        Args:
            website: The raw website string.
            
        Returns:
            Cleaned website URL, or None if invalid.
        """
        # Basic URL cleaning
        cleaned_url = str(website).strip().lower()
        
        # Add https:// if missing
        if not (cleaned_url.startswith("http://") or cleaned_url.startswith("https://")):
            cleaned_url = "https://" + cleaned_url
        
        # Basic validation
        url_pattern = r"^https?://[a-zA-Z0-9][-a-zA-Z0-9.]*\.[a-zA-Z]{2,}(/.*)?$"
        if re.match(url_pattern, cleaned_url):
            return cleaned_url
        
        return None
    
    def clean_person_names(self, names: str) -> str:
        """
        Clean and normalize person names.
        
        Args:
            names: The raw names string.
            
        Returns:
            Cleaned names string.
        """
        # Remove common prefixes
        prefixes = ["Founded by", "Founders:", "Founders", "Founder:"]
        cleaned_names = str(names).strip()
        
        for prefix in prefixes:
            if cleaned_names.lower().startswith(prefix.lower()):
                cleaned_names = cleaned_names[len(prefix):].strip()
        
        # Remove trailing commas and periods
        cleaned_names = cleaned_names.rstrip(".,")
        
        # Normalize separators
        # Replace various separators with commas
        cleaned_names = re.sub(r"\s+and\s+", ", ", cleaned_names)
        cleaned_names = re.sub(r"\s*[&|/]\s*", ", ", cleaned_names)
        
        return cleaned_names
    
    def clean_funding_info(self, funding: str) -> str:
        """
        Clean and normalize funding information.
        
        Args:
            funding: The raw funding string.
            
        Returns:
            Cleaned funding information.
        """
        # Remove common prefixes
        prefixes = ["Funding:", "Raised", "Investment:"]
        cleaned_funding = str(funding).strip()
        
        for prefix in prefixes:
            if cleaned_funding.lower().startswith(prefix.lower()):
                cleaned_funding = cleaned_funding[len(prefix):].strip()
        
        # Remove trailing commas and periods
        cleaned_funding = cleaned_funding.rstrip(".,")
        
        return cleaned_funding
    
    def clean_tech_stack(self, tech_stack: str) -> str:
        """
        Clean and normalize technology stack information.
        
        Args:
            tech_stack: The raw technology stack string.
            
        Returns:
            Cleaned technology stack string.
        """
        # Remove common prefixes
        prefixes = ["Technology:", "Tech Stack:", "Technologies:"]
        cleaned_tech = str(tech_stack).strip()
        
        for prefix in prefixes:
            if cleaned_tech.lower().startswith(prefix.lower()):
                cleaned_tech = cleaned_tech[len(prefix):].strip()
        
        # Remove trailing commas and periods
        cleaned_tech = cleaned_tech.rstrip(".,")
        
        # Normalize separators
        # Replace various separators with commas
        cleaned_tech = re.sub(r"\s+and\s+", ", ", cleaned_tech)
        cleaned_tech = re.sub(r"\s*[&|/]\s*", ", ", cleaned_tech)
        
        return cleaned_tech
    
    def clean_description(self, description: str) -> str:
        """
        Clean and normalize a description.
        
        Args:
            description: The raw description string.
            
        Returns:
            Cleaned description.
        """
        # Basic cleaning
        cleaned_desc = str(description).strip()
        
        # Remove excessive whitespace
        cleaned_desc = re.sub(r"\s+", " ", cleaned_desc)
        
        # Ensure proper capitalization
        if cleaned_desc and not cleaned_desc[0].isupper():
            cleaned_desc = cleaned_desc[0].upper() + cleaned_desc[1:]
        
        return cleaned_desc
    
    def clean_team_size(self, team_size: str) -> Optional[str]:
        """
        Clean and normalize team size information.
        
        Args:
            team_size: The raw team size string.
            
        Returns:
            Cleaned team size, or None if invalid.
        """
        # Try to extract numeric team size
        size_match = re.search(r"\b(\d+(?:-\d+)?)\b", str(team_size))
        
        if size_match:
            return size_match.group(0)
        
        # Check for common size ranges
        size_ranges = {
            "small": "1-10",
            "medium": "11-50",
            "large": "51-200",
            "enterprise": "201+"
        }
        
        team_size_lower = str(team_size).lower()
        for key, value in size_ranges.items():
            if key in team_size_lower:
                return value
        
        return None
    
    def clean_social_media(self, social_media: str) -> Dict[str, str]:
        """
        Clean and normalize social media information.
        
        Args:
            social_media: The raw social media string.
            
        Returns:
            Dictionary of social media platforms and their URLs.
        """
        # Initialize result
        result = {}
        
        # Extract URLs
        urls = re.findall(r"https?://[^\s]+", str(social_media))
        
        # Categorize by platform
        for url in urls:
            if "twitter.com" in url or "x.com" in url:
                result["Twitter"] = url
            elif "linkedin.com" in url:
                result["LinkedIn"] = url
            elif "facebook.com" in url:
                result["Facebook"] = url
            elif "instagram.com" in url:
                result["Instagram"] = url
            elif "github.com" in url:
                result["GitHub"] = url
            elif "youtube.com" in url:
                result["YouTube"] = url
            else:
                result["Other"] = url
        
        return result
    
    def clean_company_list(self, companies: str) -> List[str]:
        """
        Clean and normalize a list of company names.
        
        Args:
            companies: The raw company list string.
            
        Returns:
            List of cleaned company names.
        """
        # Remove common prefixes
        prefixes = ["Competitors:", "Competition:"]
        cleaned_companies = str(companies).strip()
        
        for prefix in prefixes:
            if cleaned_companies.lower().startswith(prefix.lower()):
                cleaned_companies = cleaned_companies[len(prefix):].strip()
        
        # Split by common separators
        company_list = re.split(r",|\band\b|[&|/]", cleaned_companies)
        
        # Clean each company name
        cleaned_list = [self.clean_company_name(company) for company in company_list]
        
        # Remove empty entries
        cleaned_list = [company for company in cleaned_list if company]
        
        return cleaned_list
    
    def clean_startup_data(self, data: Dict[str, Any], fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Clean and normalize startup data.
        
        Args:
            data: Raw startup data dictionary.
            fields: List of fields to include in the cleaned data.
                  If None, default_fields will be used.
                  
        Returns:
            Cleaned startup data dictionary.
        """
        fields_to_clean = fields or self.default_fields
        cleaned_data = {}
        
        # Apply specific cleaning functions based on field name
        for field in fields_to_clean:
            field_key = field.lower().replace(" ", "_")
            
            if field_key not in data and field in data:
                # Try the original field name if the normalized key isn't found
                field_key = field
            
            if field_key in data:
                value = data[field_key]
                
                # Apply specific cleaning based on field type
                if field in self.cleaning_functions:
                    cleaned_value = self.cleaning_functions[field](value)
                    if cleaned_value is not None:
                        cleaned_data[field] = cleaned_value
                    else:
                        cleaned_data[field] = "Not available"
                else:
                    # For other fields, just convert to string and strip
                    cleaned_data[field] = str(value).strip()
            else:
                cleaned_data[field] = "Not available"
        
        return cleaned_data
    
    def format_as_csv(self, startups_data: List[Dict[str, Any]]) -> str:
        """
        Format startup data as CSV.
        
        Args:
            startups_data: List of startup data dictionaries.
            
        Returns:
            CSV formatted string.
        """
        df = pd.DataFrame(startups_data)
        return df.to_csv(index=False)
    
    def format_as_json(self, startups_data: List[Dict[str, Any]]) -> str:
        """
        Format startup data as JSON.
        
        Args:
            startups_data: List of startup data dictionaries.
            
        Returns:
            JSON formatted string.
        """
        # Create a more structured JSON format
        structured_data = {}
        
        for startup in startups_data:
            company_name = startup.get("Company Name", "Unknown")
            
            # Split into basic and detailed info
            basic_info = {}
            detailed_info = {}
            meta_info = {}
            
            for key, value in startup.items():
                if key == "Company Name":
                    continue  # Skip as we're using it as the main key
                elif key in ["Founded Year", "Location", "Website"]:
                    basic_info[key.lower().replace(" ", "_")] = value
                elif key in ["confidence", "last_updated", "Source"]:
                    meta_info[key.lower()] = value
                else:
                    detailed_info[key.lower().replace(" ", "_")] = value
            
            structured_data[company_name] = {
                "basic_info": basic_info,
                "detailed_info": detailed_info
            }
            
            # Add meta info if available
            if meta_info:
                structured_data[company_name]["meta"] = meta_info
        
        return json.dumps(structured_data, indent=2)
