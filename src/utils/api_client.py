"""
Gemini API Client for Startup Intelligence Finder.

This module provides a wrapper around Google's Gemini API for AI-powered
startup intelligence gathering.
"""

import os
import json
from typing import Dict, List, Optional, Union

import google.generativeai as genai


class GeminiAPIClient:
    """
    A client for interacting with Google's Gemini API.

    This class handles authentication, request formatting, and response parsing
    for the Gemini API, which is used for query expansion and data analysis.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Gemini API client.

        Args:
            api_key: The API key for Gemini. If not provided, will look for
                    GEMINI_API_KEY environment variable.

        Raises:
            ValueError: If no API key is provided and none is found in environment.
        """
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")

        if not self.api_key:
            # Try to import and run setup_environment if available
            try:
                import importlib.util

                # Check if setup_env.py exists in the current directory
                setup_env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "setup_env.py")

                if os.path.exists(setup_env_path):
                    # Import setup_env.py
                    spec = importlib.util.spec_from_file_location("setup_env", setup_env_path)
                    setup_env = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(setup_env)

                    # Run setup_environment
                    if setup_env.setup_environment():
                        # Try to get the API key again
                        self.api_key = os.environ.get("GEMINI_API_KEY")
            except Exception:
                # If anything goes wrong, just continue to the error
                pass

            # If we still don't have an API key, raise an error
            if not self.api_key:
                raise ValueError(
                    "No API key provided. Either pass api_key parameter, "
                    "set GEMINI_API_KEY environment variable, or run setup_env.py first."
                )

        # Initialize the Gemini API
        genai.configure(api_key=self.api_key)

        # Use the specified models
        self.flash_model = genai.GenerativeModel('gemini-2.5-flash-preview-04-17')  # For quick responses
        self.pro_model = genai.GenerativeModel('gemini-2.5-pro-preview-03-25')      # For deep thinking

    def expand_query(self, query: str, num_expansions: int = 3) -> List[str]:
        """
        Expand a search query into multiple variations using Gemini AI.

        Args:
            query: The original search query.
            num_expansions: Number of query variations to generate.

        Returns:
            A list of expanded query strings.

        Raises:
            Exception: If there's an error communicating with the Gemini API.
        """
        prompt = f"""
        You are a startup intelligence researcher. Expand the following search query
        into {num_expansions} different variations to find startups matching this criteria.
        Make each variation unique but semantically similar to the original query.

        Original query: "{query}"

        Return only the expanded queries as a numbered list, without any additional text.
        """

        try:
            # Use the flash model for query expansion as it's a simpler task
            response = self.flash_model.generate_content(prompt)

            # Process the response to extract the expanded queries
            expanded_queries = []
            if response.text:
                # Split by newlines and filter out empty lines and numbering
                lines = response.text.strip().split('\n')
                for line in lines:
                    # Remove numbering (e.g., "1. ", "2. ")
                    clean_line = line.strip()
                    if clean_line:
                        # Remove numbering and quotes if present
                        for prefix in ["1.", "2.", "3.", "4.", "5.", "-"]:
                            if clean_line.startswith(prefix):
                                clean_line = clean_line[len(prefix):].strip()

                        # Remove quotes if present
                        clean_line = clean_line.strip('"\'')

                        if clean_line:
                            expanded_queries.append(clean_line)

            # Ensure we have the requested number of expansions
            # If we have too few, add the original query
            while len(expanded_queries) < num_expansions and len(expanded_queries) > 0:
                expanded_queries.append(query)

            # If we have no expansions at all, just use the original query
            if not expanded_queries:
                expanded_queries = [query] * num_expansions

            # If we have too many, truncate
            expanded_queries = expanded_queries[:num_expansions]

            return expanded_queries

        except Exception as e:
            print(f"Error expanding query with Gemini API: {e}")
            # Return the original query if there's an error
            return [query]

    def analyze_startup(self, startup_data: Dict[str, str], fields: List[str]) -> Dict[str, Union[str, Dict]]:
        """
        Analyze startup data to extract requested fields using Gemini AI.

        Args:
            startup_data: Raw data about the startup.
            fields: List of fields to extract (e.g., "Founders", "Funding").

        Returns:
            A dictionary with the extracted information.

        Raises:
            Exception: If there's an error communicating with the Gemini API.
        """
        # Convert startup data to a string representation
        data_str = "\n".join([f"{k}: {v}" for k, v in startup_data.items()])

        # Create a prompt for Gemini
        fields_str = ", ".join(fields)
        prompt = f"""
        You are a startup intelligence analyst. Extract the following information about
        this startup: {fields_str}.

        Startup data:
        {data_str}

        For each field, provide the most accurate information available in the data.
        If information for a field is not available, respond with "Not available".

        Format your response as a JSON object with the requested fields as keys.
        """

        try:
            # Use the pro model for deeper analysis
            response = self.pro_model.generate_content(prompt)

            # Try to parse the response as JSON
            try:
                # Extract JSON from the response
                response_text = response.text.strip()

                # If the response is wrapped in ```json and ```, extract just the JSON part
                if response_text.startswith("```json") and response_text.endswith("```"):
                    response_text = response_text[7:-3].strip()
                elif response_text.startswith("```") and response_text.endswith("```"):
                    response_text = response_text[3:-3].strip()

                parsed_data = json.loads(response_text)

                # Add metadata
                result = {
                    "data": parsed_data,
                    "confidence": 0.9,  # Placeholder - in a real implementation, this would be calculated
                    "last_updated": "2024-04-01"  # Placeholder - in a real implementation, this would be dynamic
                }

                return result

            except json.JSONDecodeError:
                # If we can't parse as JSON, return the raw response
                return {
                    "raw_response": response.text,
                    "confidence": 0.5,  # Lower confidence for unparseable responses
                    "last_updated": "2024-04-01"  # Placeholder
                }

        except Exception as e:
            print(f"Error analyzing startup with Gemini API: {e}")
            return {
                "error": str(e),
                "confidence": 0.0,
                "last_updated": "2024-04-01"  # Placeholder
            }
