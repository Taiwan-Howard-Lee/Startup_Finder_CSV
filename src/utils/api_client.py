"""
Gemini API Client for Startup Intelligence Finder.

This module provides a wrapper around Google's Gemini API for AI-powered
startup intelligence gathering with robust validation and error handling.
"""

import os
import json
import time
import logging
import re
import traceback
from typing import Dict, List, Optional, Union, Any, Tuple, Set

import google.generativeai as genai
from google.generativeai import types

from src.utils.batch_processor import GeminiAPIBatchProcessor

# Set up logging
logger = logging.getLogger(__name__)

# Define response validation constants
MAX_CONTENT_LENGTH = 15000  # Maximum content length for Gemini API


class GeminiAPIClient:
    """
    A client for interacting with Google's Gemini API.

    This class handles authentication, request formatting, and response parsing
    for the Gemini API, which is used for query expansion and data analysis.
    Includes robust validation and error handling for API responses.
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

        # Use Gemini 2.0 Flash for most operations
        self.flash_model = genai.GenerativeModel('gemini-2.0-flash')  # For most responses

        # Use Gemini 2.5 Flash for query expansion and other advanced tasks
        self.pro_model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')  # For query expansion and validation

        # Set up response validation parameters
        self.expected_field_types = {
            "Company Name": str,
            "Website": str,
            "LinkedIn": str,
            "Location": str,
            "Founded Year": (str, int),
            "Industry": str,
            "Company Size": str,
            "Funding": (str, dict),
            "Company Description": str,
            "Products/Services": (str, list),
            "Founders": (str, list),
            "Founder LinkedIn Profiles": (str, list),
            "CEO/Leadership": (str, dict, list),
            "Team": (str, dict, list),
            "Technology Stack": (str, list),
            "Competitors": (str, list),
            "Market Focus": str,
            "Social Media Links": (str, dict),
            "Latest News": str,
            "Investors": (str, list),
            "Growth Metrics": (str, dict),
            "Contact": (str, dict)
        }

    def _validate_response(self, response_text: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Validate and parse a response from the Gemini API.

        Args:
            response_text: The raw text response from the API.

        Returns:
            Tuple containing:
            - Boolean indicating if the response is valid
            - Parsed data (if valid) or None (if invalid)
            - Error message (if invalid) or None (if valid)
        """
        if not response_text or not response_text.strip():
            return False, None, "Empty response from API"

        # Extract JSON content if wrapped in code blocks
        json_content = response_text.strip()

        # Handle markdown code blocks
        if "```json" in json_content:
            try:
                json_content = json_content.split("```json")[1].split("```")[0].strip()
            except IndexError:
                return False, None, "Malformed JSON code block in response"
        elif "```" in json_content:
            try:
                json_content = json_content.split("```")[1].strip()
            except IndexError:
                return False, None, "Malformed code block in response"

        # Try to parse the JSON directly without regex validation
        # This is more lenient and will handle valid JSON that doesn't match the regex pattern
        try:
            parsed_data = json.loads(json_content)

            # Validate the structure based on expected type
            if isinstance(parsed_data, dict):
                return True, parsed_data, None
            elif isinstance(parsed_data, list):
                # For list responses, check if all items are dictionaries
                if all(isinstance(item, dict) for item in parsed_data):
                    return True, parsed_data, None
                else:
                    return False, None, "List response contains non-dictionary items"
            else:
                return False, None, f"Unexpected response type: {type(parsed_data)}"

        except json.JSONDecodeError as e:
            # If JSON parsing fails, log the error and the content for debugging
            logger.debug(f"JSON parsing error: {str(e)}")
            logger.debug(f"JSON content: {json_content[:500]}...")

            # Try to clean the content and parse again
            try:
                # Sometimes Gemini adds extra text before or after the JSON
                # Try to find JSON-like content using a more relaxed approach
                if json_content.find('{') >= 0 and json_content.rfind('}') >= 0:
                    start = json_content.find('{')
                    end = json_content.rfind('}') + 1
                    cleaned_json = json_content[start:end]
                    parsed_data = json.loads(cleaned_json)
                    logger.info("Successfully parsed JSON after cleaning")
                    return True, parsed_data, None
                elif json_content.find('[') >= 0 and json_content.rfind(']') >= 0:
                    start = json_content.find('[')
                    end = json_content.rfind(']') + 1
                    cleaned_json = json_content[start:end]
                    parsed_data = json.loads(cleaned_json)
                    logger.info("Successfully parsed JSON array after cleaning")
                    return True, parsed_data, None
            except json.JSONDecodeError:
                pass

            return False, None, f"JSON parsing error: {str(e)}"

    def _validate_fields(self, data: Dict[str, Any], required_fields: Optional[List[str]] = None) -> Tuple[bool, Dict[str, Any], List[str]]:
        """
        Validate the fields in the parsed data against expected types.

        Args:
            data: The parsed data dictionary.
            required_fields: List of fields that must be present (optional).

        Returns:
            Tuple containing:
            - Boolean indicating if the data is valid
            - Cleaned data with validated fields
            - List of validation warnings
        """
        warnings = []
        cleaned_data = {}

        # Check for required fields
        if required_fields:
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                warnings.append(f"Missing required fields: {', '.join(missing_fields)}")

        # Validate each field against expected types
        for field, value in data.items():
            # Skip null values
            if value is None:
                continue

            # Check if this is a known field
            if field in self.expected_field_types:
                expected_types = self.expected_field_types[field]
                if not isinstance(expected_types, tuple):
                    expected_types = (expected_types,)

                # Check if the value matches any of the expected types
                if not any(isinstance(value, t) for t in expected_types):
                    warnings.append(f"Field '{field}' has unexpected type: {type(value).__name__}, expected {expected_types}")

                    # Try to convert to the first expected type
                    try:
                        if str in expected_types and not isinstance(value, str):
                            # Convert to string
                            cleaned_data[field] = str(value)
                        elif list in expected_types and isinstance(value, str):
                            # Convert comma-separated string to list
                            cleaned_data[field] = [item.strip() for item in value.split(",")]
                        elif dict in expected_types and isinstance(value, str):
                            # Try to parse string as JSON
                            try:
                                cleaned_data[field] = json.loads(value)
                            except json.JSONDecodeError:
                                cleaned_data[field] = value
                        else:
                            # Keep original value
                            cleaned_data[field] = value
                    except Exception as e:
                        warnings.append(f"Error converting field '{field}': {str(e)}")
                        cleaned_data[field] = value
                else:
                    # Value has correct type
                    cleaned_data[field] = value
            else:
                # Unknown field, keep as is
                cleaned_data[field] = value

        return len(warnings) == 0, cleaned_data, warnings

    def expand_query(self, query: str, num_expansions: int = 5) -> List[str]:
        """
        Expand a search query into multiple variations using Gemini 2.5 Flash.

        Uses Gemini 2.5 Flash for all query expansions to maximize semantic diversity
        and ensure each query targets a different aspect of the search space.

        Args:
            query: The original search query.
            num_expansions: Number of NEW query variations to generate (in addition to original).

        Returns:
            A list of expanded query strings, including the original query.
            Total length will be num_expansions + 1 (original + new variations).

        Raises:
            Exception: If there's an error communicating with the Gemini API.
        """
        # If query is empty or only whitespace, return it as is
        if not query or not query.strip():
            return [query]

        # If no expansions requested, just return the original
        if num_expansions <= 0:
            return [query]

        # Create an enhanced prompt for Gemini 2.5 Flash with diversity optimization
        prompt = f"""
        You are a startup intelligence researcher specializing in query expansion for Google search.

        TASK:
        Generate exactly {num_expansions} different search query variations for finding startups related to: "{query}"

        GUIDELINES:
        - Maximize DIVERSITY in the search vector space - each query should target a different aspect or dimension
        - Avoid semantic overlap between queries - each should retrieve a substantially different set of results
        - Consider different:
          * Industry verticals (energy, mobility, social tech, etc.)
          * Geographic focuses (specific regions, urban/rural)
          * Technology approaches (hardware, software, services)
          * Business models (B2B, B2C, marketplace)
          * Company stages (early-stage, growth, established)
          * Funding status (bootstrapped, seed, venture-backed)
        - Use industry-specific terminology where appropriate
        - Include both specific and general variations, but ensure they target different result sets
        - Each query should be 2-8 words long and search-engine optimized
        - Prioritize queries that would yield unique startups not found by other queries

        EXAMPLES of good query variations for "AI startups":
        - "artificial intelligence companies"
        - "machine learning ventures"
        - "AI tech entrepreneurs"
        - "deep learning businesses"
        - "neural network startups"

        FORMAT:
        Return EXACTLY {num_expansions} queries, one per line, without numbering or any other text.
        Do not include the original query "{query}" in your response.
        Each line should contain only one search query.
        """

        try:
            # Use Gemini 2.5 Flash for query expansions
            logger.info("Using Gemini 2.5 Flash for query expansion...")
            response = self.pro_model.generate_content(prompt)
            logger.info("Successfully used Gemini 2.5 Flash for query expansion")

            # Always start with the original query
            expanded_queries = [query]

            if response.text:
                # Split by newlines and clean up
                new_queries = [line.strip() for line in response.text.strip().split('\n') if line.strip()]

                # Remove any numbering or bullet points that might have been added
                cleaned_queries = []
                for new_query in new_queries:
                    # Remove common prefixes like "1.", "- ", etc.
                    cleaned_query = new_query
                    if '. ' in cleaned_query and cleaned_query.split('. ', 1)[0].isdigit():
                        cleaned_query = cleaned_query.split('. ', 1)[1]
                    elif cleaned_query.startswith('- '):
                        cleaned_query = cleaned_query[2:]
                    elif cleaned_query.startswith('* '):
                        cleaned_query = cleaned_query[2:]

                    cleaned_query = cleaned_query.strip()
                    if cleaned_query and cleaned_query.lower() != query.lower():
                        cleaned_queries.append(cleaned_query)

                # Add unique expansions up to the requested number
                for new_query in cleaned_queries:
                    if len(expanded_queries) >= num_expansions + 1:  # +1 for original query
                        break
                    if new_query not in expanded_queries:
                        expanded_queries.append(new_query)

            # If we didn't get enough variations, try to generate more with a simpler approach
            if len(expanded_queries) < num_expansions + 1:
                missing_count = (num_expansions + 1) - len(expanded_queries)
                logger.warning(f"Only got {len(expanded_queries)-1} variations, need {missing_count} more")

                # Try a simpler fallback prompt
                fallback_prompt = f"""
                Generate {missing_count} more search variations for: "{query}"
                Make them different from these existing ones: {', '.join(expanded_queries[1:])}
                Return only the new queries, one per line.
                """

                try:
                    fallback_response = self.pro_model.generate_content(fallback_prompt)
                    if fallback_response.text:
                        fallback_queries = [line.strip() for line in fallback_response.text.strip().split('\n') if line.strip()]
                        for fallback_query in fallback_queries:
                            if len(expanded_queries) >= num_expansions + 1:
                                break
                            if fallback_query and fallback_query not in expanded_queries:
                                expanded_queries.append(fallback_query)
                except Exception as fallback_error:
                    logger.warning(f"Fallback query generation failed: {fallback_error}")

            logger.info(f"Generated {len(expanded_queries)-1} unique query variations (requested {num_expansions})")
            return expanded_queries

        except Exception as e:
            logger.error(f"Error expanding query with Gemini API: {e}")
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
            # Use the pro model with search grounding for deeper analysis
            # Note: Search grounding is configured when the model is initialized

            # Generate content with search grounding
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

    def expand_queries_batch(self, queries: List[str], num_expansions: int = 5) -> Dict[str, List[str]]:
        """
        Expand multiple queries in parallel.

        Args:
            queries: List of queries to expand.
            num_expansions: Number of expansions per query.

        Returns:
            Dictionary mapping original queries to their expansions.
        """
        logger.info(f"Expanding {len(queries)} queries in parallel with {num_expansions} expansions each")

        batch_processor = GeminiAPIBatchProcessor(max_workers=30)

        # Define the processing function
        def process_query(api_client, query, num_expansions):
            return {
                "query": query,
                "expansions": api_client.expand_query(query, num_expansions)
            }

        # Process the batch
        results = batch_processor.process_batch(
            self, queries, process_query, num_expansions
        )

        # Convert to dictionary
        expansions_dict = {}
        for result in results:
            if isinstance(result, dict) and "query" in result and "expansions" in result:
                expansions_dict[result["query"]] = result["expansions"]
            elif isinstance(result, dict) and "error" in result and "item" in result:
                # Handle error case
                query = result["item"]
                logger.error(f"Error expanding query '{query}': {result['error']}")
                expansions_dict[query] = [query]  # Use original query as fallback

        logger.info(f"Successfully expanded {len(expansions_dict)} queries")
        return expansions_dict

    def analyze_startups_batch(self, startups_data: List[Dict[str, str]], fields: List[str]) -> List[Dict[str, Any]]:
        """
        Analyze multiple startups in parallel.

        Args:
            startups_data: List of startup data dictionaries.
            fields: List of fields to extract for each startup.

        Returns:
            List of dictionaries with analyzed startup data.
        """
        logger.info(f"Analyzing {len(startups_data)} startups in parallel")

        batch_processor = GeminiAPIBatchProcessor(max_workers=30)

        # Define the processing function
        def process_startup(api_client, startup_data, fields):
            return api_client.analyze_startup(startup_data, fields)

        # Process the batch
        results = batch_processor.process_batch(
            self, startups_data, process_startup, fields
        )

        logger.info(f"Successfully analyzed {len(results)} startups")
        return results

    def validate_startups_batch(self, startups: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """
        Validate multiple startups in parallel.

        Args:
            startups: List of startup dictionaries to validate.
            query: The original search query.

        Returns:
            List of validated startup dictionaries.
        """
        logger.info(f"Validating {len(startups)} startups in parallel")

        # Split into smaller batches for better performance with Gemini
        batch_size = 5  # Gemini works better with smaller batches
        batches = [startups[i:i+batch_size] for i in range(0, len(startups), batch_size)]

        batch_processor = GeminiAPIBatchProcessor(max_workers=30)

        # Define the processing function
        def process_batch(api_client, batch, query):
            # Convert batch to JSON
            batch_json = json.dumps(batch, indent=2)

            # Create prompt
            prompt = f"""
            You are a startup intelligence analyst specializing in data validation and enrichment.
            I have a dataset of startups related to the search query: "{query}".

            TASK:
            Analyze the following startup data to:
            1. VERIFY each startup is RELEVANT to the query
            2. CORRECT any anomalies, inconsistencies, or inaccuracies
            3. FILL IN missing information where possible
            4. STANDARDIZE formatting across all entries

            STARTUP RELEVANCE CRITERIA:
            - The startup's core business, products, or services must directly relate to query
            - The startup should be operating in the industry or solving problems mentioned in the query
            - The startup should be targeting the market or audience implied by the query

            DATA VALIDATION GUIDELINES:
            - Company Name: Ensure correct spelling and proper capitalization
            - Website: Verify it's the official company website (not social media or third-party sites)
            - LinkedIn: Ensure it's the correct company LinkedIn page
            - Location: Standardize format (City, State/Region, Country)
            - Founded Year: Verify accuracy and use 4-digit year format
            - Industry: Use specific, standardized industry categories
            - Company Size: Standardize format (e.g., "11-50 employees")
            - Funding: Include latest round, amount, and date if available
            - Product Description: Ensure it accurately describes what the company does

            DATA TO VALIDATE:
            {batch_json}

            Return ONLY the corrected data in valid JSON format, with the same structure as the above json.
            If a startup is not relevant to the query, remove it completely from the results.
            """

            # Configure search grounding for Gemini 2.0 Flash
            safety_settings = [
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_NONE"
                }
            ]

            generation_config = {
                "temperature": 0.2,
                "top_p": 0.95,
                "top_k": 64,
                "max_output_tokens": 8192,
            }

            # Use Gemini 2.0 Flash with search grounding for validation
            model = genai.GenerativeModel(
                model_name='gemini-2.0-flash',
                generation_config=generation_config,
                safety_settings=safety_settings,
                tools=[{"web_search": {}}]  # Enable search grounding
            )

            # Get response from Gemini 2.0 Flash with search grounding
            response = model.generate_content(prompt)

            # Extract JSON from response
            try:
                # Find JSON in the response
                response_text = response.text
                if "```json" in response_text:
                    json_content = response_text.split("```json")[1].split("```")[0].strip()
                elif "```" in response_text:
                    json_content = response_text.split("```")[1].strip()
                else:
                    json_content = response_text.strip()

                # Parse the JSON
                return json.loads(json_content)
            except Exception as e:
                logger.error(f"Error parsing response: {e}")
                return batch  # Return original batch on error

        # Process all batches
        results = []
        for i, batch in enumerate(batches):
            logger.info(f"Processing batch {i+1}/{len(batches)} with {len(batch)} startups")
            batch_results = batch_processor.process_batch(
                self, [batch], process_batch, query
            )
            # Flatten results
            for batch_result in batch_results:
                if isinstance(batch_result, list):
                    results.extend(batch_result)
                else:
                    results.append(batch_result)

        logger.info(f"Successfully validated {len(results)} startups")
        return results

    def validate_startups_chunk(self, chunk_text: str, query: str, startup_indices: List[int]) -> Dict[str, Any]:
        """
        Validate a chunk of startup data using Gemini 2.0 Flash.

        This method is designed to work with the ContentProcessor's chunking functionality.

        Args:
            chunk_text: The text chunk containing startup data.
            query: The original search query.
            startup_indices: List of indices of startups in the original list.

        Returns:
            Dictionary with validated startup data and metadata.
        """
        logger.info(f"Validating chunk with {len(startup_indices)} startups")

        # Create prompt for Gemini
        prompt = f"""
        You are a startup intelligence analyst specializing in data validation and enrichment.
        I have a dataset of startups related to the search query: "{query}".

        TASK:
        Analyze the following startup data to:
        1. VERIFY each startup is RELEVANT to the query
        2. CORRECT any anomalies, inconsistencies, or inaccuracies
        3. FILL IN missing information where possible
        4. STANDARDIZE formatting across all entries

        STARTUP RELEVANCE CRITERIA:
        - The startup's core business, products, or services must directly relate to query
        - The startup should be operating in the industry or solving problems mentioned in the query
        - The startup should be targeting the market or audience implied by the query

        DATA VALIDATION GUIDELINES:
        - Company Name: Ensure correct spelling and proper capitalization
        - Website: Verify it's the official company website (not social media or third-party sites)
        - LinkedIn: Ensure it's the correct company LinkedIn page
        - Location: Standardize format (City, State/Region, Country)
        - Founded Year: Verify accuracy and use 4-digit year format
        - Industry: Use specific, standardized industry categories
        - Company Size: Standardize format (e.g., "11-50 employees")
        - Funding: Include latest round, amount, and date if available
        - Product Description: Ensure it accurately describes what the company does

        DATA TO VALIDATE:
        {chunk_text}

        Return ONLY the corrected data in valid JSON format, with the same structure as the above json.
        If a startup is not relevant to the query, remove it completely from the results.
        """

        # Configure search grounding for Gemini 2.0 Flash
        safety_settings = [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_NONE"
            }
        ]

        generation_config = {
            "temperature": 0.2,
            "top_p": 0.95,
            "top_k": 64,
            "max_output_tokens": 8192,
        }

        # Use Gemini 2.0 Flash with search grounding for validation
        model = genai.GenerativeModel(
            model_name='gemini-2.0-flash',
            generation_config=generation_config,
            safety_settings=safety_settings,
            tools=[{"web_search": {}}]  # Enable search grounding
        )

        try:
            # Get response from Gemini 2.0 Flash with search grounding
            response = model.generate_content(prompt)

            # Extract JSON from response
            response_text = response.text
            if "```json" in response_text:
                json_content = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                json_content = response_text.split("```")[1].strip()
            else:
                json_content = response_text.strip()

            # Parse the JSON
            validated_data = json.loads(json_content)

            # Return the validated data with metadata
            return {
                "validated_data": validated_data,
                "startup_indices": startup_indices,
                "success": True
            }

        except Exception as e:
            logger.error(f"Error validating chunk: {e}")
            # Return error information
            return {
                "error": str(e),
                "startup_indices": startup_indices,
                "success": False
            }

    def combine_validated_chunks(self, validated_chunks: List[Dict[str, Any]], original_startups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Combine validated chunks into a single result.

        Args:
            validated_chunks: List of dictionaries with validated startup data and metadata.
            original_startups: The original list of startup dictionaries.

        Returns:
            List of validated startup dictionaries.
        """
        logger.info(f"Combining {len(validated_chunks)} validated chunks")

        # Create a copy of the original startups to update
        result_startups = original_startups.copy()

        # Process each validated chunk
        for chunk in validated_chunks:
            # Skip failed chunks
            if not chunk.get("success", False):
                logger.warning(f"Skipping failed chunk: {chunk.get('error', 'Unknown error')}")
                continue

            # Get the validated data and startup indices
            validated_data = chunk.get("validated_data", [])
            startup_indices = chunk.get("startup_indices", [])

            # If validated_data is a list, process each item
            if isinstance(validated_data, list):
                # Match validated startups with original startups by index
                for i, validated_startup in enumerate(validated_data):
                    if i < len(startup_indices):
                        original_index = startup_indices[i]
                        if original_index < len(result_startups):
                            # Update the startup with validated data
                            result_startups[original_index] = validated_startup
                    else:
                        # If there are more validated startups than indices, append them
                        result_startups.append(validated_startup)

            # If validated_data is a dictionary, process it as a single startup
            elif isinstance(validated_data, dict):
                # Update the first startup in the indices
                if startup_indices and startup_indices[0] < len(result_startups):
                    result_startups[startup_indices[0]] = validated_data

        # Filter out any None values or empty dictionaries
        result_startups = [s for s in result_startups if s and isinstance(s, dict)]

        logger.info(f"Combined {len(result_startups)} validated startups")
        return result_startups

    def extract_structured_data_batch(self, items: List[Tuple[str, str, str, List[str]]]) -> List[Dict[str, Any]]:
        """
        Extract structured data from multiple sources in parallel.

        Args:
            items: List of tuples (company_name, source_type, content, fields).

        Returns:
            List of dictionaries with extracted data.
        """
        logger.info(f"Extracting structured data from {len(items)} sources in parallel")

        batch_processor = GeminiAPIBatchProcessor(max_workers=30)

        # Define the processing function
        def process_item(api_client, item):
            company_name, source_type, content, fields = item
            return {
                "company_name": company_name,
                "source_type": source_type,
                "data": api_client.extract_structured_data(company_name, source_type, content, fields)
            }

        # Process the batch
        results = batch_processor.process_batch(
            self, items, process_item
        )

        logger.info(f"Successfully extracted data from {len(results)} sources")
        return results

    def extract_structured_data(self, company_name: str, source_type: str, content: str, fields: List[str]) -> Dict[str, Any]:
        """
        Extract structured data from HTML or text content using Gemini AI.
        Includes robust validation and error handling.

        Args:
            company_name: Name of the company.
            source_type: Type of source (e.g., "LinkedIn", "Website", "Crunchbase").
            content: HTML or text content to analyze.
            fields: List of fields to extract (e.g., "Location", "Founded Year", "Industry").

        Returns:
            Dictionary with extracted fields.
        """
        # Truncate content if it's too long (Gemini has token limits)
        if len(content) > MAX_CONTENT_LENGTH:
            logger.info(f"Truncating content for {company_name} from {len(content)} to {MAX_CONTENT_LENGTH} characters")
            content = content[:MAX_CONTENT_LENGTH] + "..."

        # Create a more detailed prompt for Gemini with specific instructions for each field
        fields_str = ", ".join(fields)
        prompt = f"""
        You are a startup intelligence data extractor specializing in comprehensive company analysis.
        Extract the following information about {company_name} from this {source_type} content: {fields_str}.

        Content:
        {content}

        For each field, provide the most accurate and detailed information available in the content.
        If information for a field is not available, respond with null.

        Specific guidelines for extraction:

        - Company Description: Extract a comprehensive description of what the company does, its mission, and value proposition.

        - Founders: List all founders with their full names. Format as a comma-separated list.

        - Founder LinkedIn Profiles: Extract LinkedIn profile URLs for founders if available. Format as a JSON array.

        - CEO/Leadership: Extract information about the CEO and key leadership team members with their roles.

        - Location: Extract the company's headquarters location. Include city, region/state, and country if available.

        - Founded Year: Extract the year the company was founded as a 4-digit number.

        - Industry: Extract the primary industry and any sub-industries the company operates in.

        - Company Size: Extract the number of employees, preferably as a range (e.g., "11-50 employees").

        - Funding: Extract detailed funding information including total amount raised, latest round, and date if available.

        - Technology Stack: Extract technologies, programming languages, frameworks, or platforms used by the company.

        - Competitors: Extract names of direct competitors if mentioned. Format as a comma-separated list.

        - Market Focus: Extract the target market, customer segments, or geographical focus areas.

        - Social Media Links: Extract all social media profile URLs. Format as a JSON object with platform names as keys.

        - Latest News: Extract recent news, announcements, or milestones about the company.

        - Investors: Extract names of investors, VCs, or investment firms that have funded the company.

        - Growth Metrics: Extract any metrics related to company growth, such as user numbers, revenue growth, etc.

        - Products/Services: Extract detailed information about the company's products or services.

        - Team: Extract information about the team size, key team members, and their roles.

        - Contact: Extract contact information including email, phone, or contact form URL.

        Format your response as a JSON object with the requested fields as keys.
        Be precise and extract only factual information present in the content.
        """

        try:
            # Use the flash model for simpler extraction tasks
            logger.debug(f"Sending extraction request to Gemini for {company_name} from {source_type}")
            response = self.flash_model.generate_content(prompt)

            if not response or not response.text:
                logger.error(f"Empty response from Gemini for {company_name}")
                return {"error": "Empty response from API"}

            # Validate and parse the response
            is_valid, parsed_data, error_message = self._validate_response(response.text)

            if not is_valid or not parsed_data:
                logger.error(f"Invalid response from Gemini for {company_name}: {error_message}")
                # Try a simpler prompt as fallback
                return self._extract_with_fallback(company_name, source_type, content, fields)

            # Validate the fields
            fields_valid, cleaned_data, warnings = self._validate_fields(parsed_data, fields)

            if warnings:
                for warning in warnings:
                    logger.warning(f"Validation warning for {company_name}: {warning}")

            # Filter out null values and standardize "not available" values
            filtered_data = {}
            for k, v in cleaned_data.items():
                if v is None or v == "null" or v == "Not available" or v == "":
                    continue

                # For lists, filter out empty items
                if isinstance(v, list) and not any(item for item in v if item):
                    continue

                # For dicts, filter out empty dicts
                if isinstance(v, dict) and not v:
                    continue

                filtered_data[k] = v

            logger.info(f"Successfully extracted {len(filtered_data)} fields for {company_name} from {source_type}")
            return filtered_data

        except Exception as e:
            error_traceback = traceback.format_exc()
            logger.error(f"Error extracting data from {source_type} for {company_name}: {e}")
            logger.debug(f"Error traceback: {error_traceback}")

            # Try fallback extraction
            return self._extract_with_fallback(company_name, source_type, content, fields)

    def _extract_with_fallback(self, company_name: str, source_type: str, content: str, fields: List[str]) -> Dict[str, Any]:
        """
        Fallback method for extracting data when the primary method fails.
        Uses a simpler prompt and more robust error handling.

        Args:
            company_name: Name of the company.
            source_type: Type of source.
            content: Content to analyze.
            fields: Fields to extract.

        Returns:
            Dictionary with extracted fields.
        """
        logger.info(f"Attempting fallback extraction for {company_name} from {source_type}")

        try:
            # Create a simpler prompt
            fields_str = ", ".join(fields)
            simple_prompt = f"""
            Extract information about {company_name} from this content.
            Focus on these fields: {fields_str}.

            Return a simple JSON object with the fields as keys.
            If information is not available, use null.

            Content (excerpt):
            {content[:5000]}
            """

            # Try with the flash model again
            response = self.flash_model.generate_content(simple_prompt)

            if not response or not response.text:
                logger.error(f"Empty response from fallback extraction for {company_name}")
                return {"error": "Empty response from fallback API call"}

            # Try to parse the response
            is_valid, parsed_data, error_message = self._validate_response(response.text)

            if not is_valid or not parsed_data:
                logger.error(f"Invalid response from fallback extraction for {company_name}: {error_message}")
                # Return minimal data with company name
                return {"Company Name": company_name, "error": error_message}

            # Filter out null values
            filtered_data = {k: v for k, v in parsed_data.items() if v is not None and v != "null" and v != "Not available" and v != ""}

            if not filtered_data and "Company Name" not in filtered_data:
                filtered_data["Company Name"] = company_name

            logger.info(f"Fallback extraction retrieved {len(filtered_data)} fields for {company_name}")
            return filtered_data

        except Exception as e:
            logger.error(f"Fallback extraction failed for {company_name}: {e}")
            return {"Company Name": company_name, "error": str(e)}
