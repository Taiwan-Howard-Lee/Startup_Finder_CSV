"""
Input Handler for Startup Intelligence Finder.

This module processes user queries and validates input parameters.
"""

from typing import Dict, List, Optional, Union


class InputHandler:
    """
    A handler for processing user input queries and parameters.
    
    This class validates and normalizes user inputs for the startup finder.
    """
    
    def __init__(self, default_fields: Optional[List[str]] = None):
        """
        Initialize the InputHandler.
        
        Args:
            default_fields: List of default fields to include in search results.
                           If None, a basic set of fields will be used.
        """
        self.default_fields = default_fields or [
            "Company Name",
            "Founded Year",
            "Location",
            "Website",
        ]
        
        # Define all available fields
        self.available_fields = [
            # Basic Info
            "Company Name",
            "Founded Year",
            "Location",
            "Website",
            
            # Optional Fields
            "Founders",
            "Funding Information",
            "Technology Stack",
            "Product Description",
            "Team Size",
            "Social Media",
            "Latest News",
            "Competitors",
            "Business Model",
            "Target Market"
        ]
    
    def validate_query(self, query: str) -> str:
        """
        Validate and normalize a search query.
        
        Args:
            query: The user's search query.
            
        Returns:
            Normalized query string.
            
        Raises:
            ValueError: If the query is empty or invalid.
        """
        if not query:
            raise ValueError("Search query cannot be empty")
        
        # Normalize the query (trim whitespace, etc.)
        normalized_query = query.strip()
        
        if len(normalized_query) < 3:
            raise ValueError("Search query must be at least 3 characters long")
            
        return normalized_query
    
    def validate_fields(self, fields: Optional[List[str]] = None) -> List[str]:
        """
        Validate and normalize requested fields.
        
        Args:
            fields: List of fields to include in search results.
                  If None, default_fields will be used.
                  
        Returns:
            List of validated field names.
            
        Raises:
            ValueError: If any field is invalid.
        """
        if fields is None:
            return self.default_fields.copy()
        
        # Normalize field names (case-insensitive matching)
        normalized_fields = []
        
        for field in fields:
            field = field.strip()
            
            # Try to match with available fields (case-insensitive)
            matched = False
            for available_field in self.available_fields:
                if field.lower() == available_field.lower():
                    normalized_fields.append(available_field)
                    matched = True
                    break
            
            if not matched:
                # Suggest similar fields
                suggestions = [f for f in self.available_fields 
                              if field.lower() in f.lower()]
                
                if suggestions:
                    suggestion_str = ", ".join(suggestions)
                    raise ValueError(
                        f"Invalid field: '{field}'. Did you mean one of these? {suggestion_str}"
                    )
                else:
                    available_fields_str = ", ".join(self.available_fields)
                    raise ValueError(
                        f"Invalid field: '{field}'. Available fields are: {available_fields_str}"
                    )
        
        # Always include basic fields
        for basic_field in ["Company Name", "Founded Year", "Location", "Website"]:
            if basic_field not in normalized_fields:
                normalized_fields.append(basic_field)
        
        return normalized_fields
    
    def validate_config(self, config: Optional[Dict[str, Union[int, float, bool, str]]] = None) -> Dict[str, Union[int, float, bool, str]]:
        """
        Validate and normalize configuration parameters.
        
        Args:
            config: Dictionary of configuration parameters.
                  If None, default configuration will be used.
                  
        Returns:
            Dictionary of validated configuration parameters.
            
        Raises:
            ValueError: If any configuration parameter is invalid.
        """
        default_config = {
            "max_results": 50,
            "min_confidence": 0.8,
            "include_sources": True,
            "export_format": "csv"
        }
        
        if config is None:
            return default_config.copy()
        
        validated_config = default_config.copy()
        
        # Update with provided values, validating each one
        if "max_results" in config:
            max_results = config["max_results"]
            if not isinstance(max_results, int) or max_results < 1:
                raise ValueError("max_results must be a positive integer")
            validated_config["max_results"] = max_results
        
        if "min_confidence" in config:
            min_confidence = config["min_confidence"]
            if not isinstance(min_confidence, (int, float)) or not (0 <= min_confidence <= 1):
                raise ValueError("min_confidence must be a float between 0 and 1")
            validated_config["min_confidence"] = min_confidence
        
        if "include_sources" in config:
            include_sources = config["include_sources"]
            if not isinstance(include_sources, bool):
                raise ValueError("include_sources must be a boolean")
            validated_config["include_sources"] = include_sources
        
        if "export_format" in config:
            export_format = config["export_format"]
            if not isinstance(export_format, str) or export_format.lower() not in ["csv", "json"]:
                raise ValueError("export_format must be either 'csv' or 'json'")
            validated_config["export_format"] = export_format.lower()
        
        return validated_config
    
    def process_input(self, 
                     query: str, 
                     fields: Optional[List[str]] = None,
                     config: Optional[Dict[str, Union[int, float, bool, str]]] = None) -> Dict[str, Union[str, List[str], Dict]]:
        """
        Process and validate all input parameters.
        
        Args:
            query: The user's search query.
            fields: List of fields to include in search results.
            config: Dictionary of configuration parameters.
            
        Returns:
            Dictionary containing validated inputs.
            
        Raises:
            ValueError: If any input is invalid.
        """
        validated_query = self.validate_query(query)
        validated_fields = self.validate_fields(fields)
        validated_config = self.validate_config(config)
        
        return {
            "query": validated_query,
            "fields": validated_fields,
            "config": validated_config
        }
