"""
CSV Appender for Startup Finder.

This module provides utilities for appending results to a single CSV file
instead of creating multiple intermediate files.
"""

import os
import csv
import time
import logging
from typing import List, Dict, Any, Optional, Set

# Set up logging
logger = logging.getLogger(__name__)

class CSVAppender:
    """Utility for appending results to a single CSV file."""
    
    def __init__(self, output_file: str = None):
        """
        Initialize the CSV appender.
        
        Args:
            output_file: Path to the output CSV file
        """
        self.output_file = output_file
        self.existing_companies = set()
        self.header_written = False
        self.fieldnames = []
        
        # Create output directory if it doesn't exist
        if output_file:
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            # Check if file exists and load existing companies
            if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                self._load_existing_companies()
    
    def _load_existing_companies(self):
        """Load existing companies from the output file."""
        try:
            with open(self.output_file, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self.fieldnames = reader.fieldnames or []
                
                # Get company names
                name_column = "Company Name"
                if name_column in self.fieldnames:
                    for row in reader:
                        company_name = row.get(name_column, "").strip()
                        if company_name:
                            self.existing_companies.add(company_name.lower())
                
                self.header_written = True
                logger.info(f"Loaded {len(self.existing_companies)} existing companies from {self.output_file}")
        except Exception as e:
            logger.error(f"Error loading existing companies: {e}")
    
    def append_results(self, results: List[Dict[str, Any]], batch_info: str = "") -> int:
        """
        Append results to the output file.
        
        Args:
            results: List of result dictionaries
            batch_info: Batch information to add to the results
            
        Returns:
            Number of rows appended
        """
        if not self.output_file or not results:
            return 0
        
        try:
            # Get fieldnames from results
            all_fields = set()
            for result in results:
                all_fields.update(result.keys())
            
            # Add batch info field if not empty
            if batch_info and "Batch Info" not in all_fields:
                all_fields.add("Batch Info")
            
            # Combine with existing fieldnames
            if self.fieldnames:
                all_fields.update(self.fieldnames)
            
            # Convert to list and ensure Company Name is first
            fieldnames = list(all_fields)
            if "Company Name" in fieldnames:
                fieldnames.remove("Company Name")
                fieldnames.insert(0, "Company Name")
            
            # Filter out duplicates
            name_column = "Company Name"
            rows_to_append = []
            
            for result in results:
                company_name = result.get(name_column, "").strip()
                
                # Skip empty company names
                if not company_name:
                    continue
                
                # Skip duplicates
                if company_name.lower() in self.existing_companies:
                    logger.debug(f"Skipping duplicate company: {company_name}")
                    continue
                
                # Add to existing companies
                self.existing_companies.add(company_name.lower())
                
                # Add batch info if provided
                if batch_info:
                    result["Batch Info"] = batch_info
                
                rows_to_append.append(result)
            
            # Append to file
            mode = 'a' if self.header_written else 'w'
            with open(self.output_file, mode, newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                
                # Write header if needed
                if not self.header_written:
                    writer.writeheader()
                    self.header_written = True
                    self.fieldnames = fieldnames
                
                # Write rows
                for row in rows_to_append:
                    writer.writerow(row)
            
            logger.info(f"Appended {len(rows_to_append)} rows to {self.output_file}")
            return len(rows_to_append)
        
        except Exception as e:
            logger.error(f"Error appending results: {e}")
            return 0
    
    def get_existing_companies(self) -> Set[str]:
        """
        Get the set of existing company names.
        
        Returns:
            Set of existing company names (lowercase)
        """
        return self.existing_companies
    
    def get_company_count(self) -> int:
        """
        Get the number of companies in the output file.
        
        Returns:
            Number of companies
        """
        return len(self.existing_companies)

# Create a default CSV appender
def create_csv_appender(output_file: str = None) -> CSVAppender:
    """
    Create a CSV appender.
    
    Args:
        output_file: Path to the output CSV file
        
    Returns:
        CSV appender instance
    """
    if not output_file:
        # Create default output file
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_file = f"output/data/startups_{timestamp}.csv"
    
    return CSVAppender(output_file)
