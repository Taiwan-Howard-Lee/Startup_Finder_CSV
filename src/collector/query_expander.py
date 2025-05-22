"""
Query Expander for Startup Intelligence Finder.

This module expands user queries into multiple variations to improve search results.
"""

import logging
from typing import List, Optional, Dict

from src.utils.api_client import GeminiAPIClient

# Set up logging
logger = logging.getLogger(__name__)


class QueryExpander:
    """
    A utility for expanding search queries into multiple variations.

    This class uses the Gemini API to generate semantically similar
    variations of the original query to improve search coverage.
    """

    def __init__(self, api_client: Optional[GeminiAPIClient] = None, api_key: Optional[str] = None):
        """
        Initialize the QueryExpander.

        Args:
            api_client: An existing GeminiAPIClient instance.
            api_key: API key for Gemini if api_client is not provided.

        Note:
            Either api_client or api_key must be provided.
        """
        if api_client:
            self.api_client = api_client
        elif api_key:
            self.api_client = GeminiAPIClient(api_key=api_key)
        else:
            # Try to initialize with environment variable
            self.api_client = GeminiAPIClient()

    def expand_query_parallel(self, query: str, num_expansions: int = 10) -> List[str]:
        """
        Expand a search query into multiple variations using parallel processing.

        Args:
            query: The original search query.
            num_expansions: Number of query variations to generate (1-100).

        Returns:
            A list of expanded query strings, including the original.
        """
        # This now simply calls the simplified expand_query method
        # as we're letting the LLM handle all the complexity
        return self.expand_query(query, num_expansions)

    def expand_query(self, query: str, num_expansions: int = 10) -> List[str]:
        """
        Expand a search query into multiple variations using Gemini 2.5 Flash.

        Uses Gemini 2.5 Flash for all query expansions.
        The expansion focuses on semantic diversity to maximize unique search results.

        Args:
            query: The original search query.
            num_expansions: Number of NEW query variations to generate (in addition to original).

        Returns:
            A list of expanded query strings, including the original.
            Total length will be num_expansions + 1 (original + new variations).
        """
        # Ensure num_expansions is at least 0
        num_expansions = max(0, num_expansions)

        # If no expansions requested, just return the original query
        if num_expansions <= 0:
            return [query]

        try:
            logger.info(f"Generating {num_expansions} NEW semantically diverse query variations using Gemini 2.5 Flash...")

            # Get variations directly from the API client
            # The API client now returns original + new variations
            expanded_queries = self.api_client.expand_query(
                query=query,
                num_expansions=num_expansions
            )

            logger.info(f"Generated {len(expanded_queries)-1} unique query variations (requested {num_expansions})")
            return expanded_queries

        except Exception as e:
            # Log the error but continue with just the original query
            logger.error(f"Error expanding query: {e}")
            return [query]
