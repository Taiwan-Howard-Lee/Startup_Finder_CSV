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
        # Validate input range
        num_expansions = max(1, min(100, num_expansions))

        # Always include the original query
        expanded_queries = [query]

        # If only 1 expansion requested, just return the original query
        if num_expansions <= 1:
            return expanded_queries

        try:
            logger.info(f"Generating {num_expansions} query variations using parallel Gemini API calls...")

            # Create multiple variations of the query to send in parallel
            query_variations = [
                f"{query}",  # Original query
                f"Alternative search query for: {query}",
                f"Different way to search for: {query}",
                f"Rephrase this search query: {query}",
                f"Startup search query variation: {query}",
                f"Business search alternative for: {query}"
            ]

            # Calculate how many expansions we need per variation to reach our target
            expansions_per_variation = max(1, (num_expansions // len(query_variations)) + 1)

            # Use batch processing to expand all variations in parallel
            expansions_dict = self.api_client.expand_queries_batch(
                query_variations,
                num_expansions=expansions_per_variation
            )

            # Collect all unique expansions
            for variation, expansions in expansions_dict.items():
                for expansion in expansions:
                    if expansion and expansion not in expanded_queries:
                        expanded_queries.append(expansion)
                        if len(expanded_queries) >= num_expansions + 1:  # +1 for original
                            break
                if len(expanded_queries) >= num_expansions + 1:
                    break

            logger.info(f"Generated {len(expanded_queries)-1} unique query variations using parallel processing")

            # If we couldn't generate enough variations, fill with modified versions
            if len(expanded_queries) < num_expansions + 1:
                logger.info(f"Could only generate {len(expanded_queries)-1} unique variations. Adding modified versions.")

                # Create modified versions by adding common prefixes/suffixes
                prefixes = ["latest ", "top ", "best ", "innovative ", "new "]
                suffixes = [" companies", " startups", " businesses", " ventures", " enterprises"]

                # Add variations until we reach the requested number
                existing_variations = expanded_queries.copy()
                for variation in existing_variations:
                    if len(expanded_queries) >= num_expansions + 1:
                        break

                    for prefix in prefixes:
                        modified = f"{prefix}{variation}"
                        if modified not in expanded_queries:
                            expanded_queries.append(modified)
                            if len(expanded_queries) >= num_expansions + 1:
                                break

                    if len(expanded_queries) >= num_expansions + 1:
                        break

                    for suffix in suffixes:
                        modified = f"{variation}{suffix}"
                        if modified not in expanded_queries:
                            expanded_queries.append(modified)
                            if len(expanded_queries) >= num_expansions + 1:
                                break

            # Ensure we don't exceed the requested number
            expanded_queries = expanded_queries[:num_expansions + 1]  # +1 for original

        except Exception as e:
            logger.error(f"Error expanding query with parallel processing: {e}")
            # If parallel processing fails, fall back to the original query
            if len(expanded_queries) <= 1:
                expanded_queries = [query]

        return expanded_queries

    def expand_query(self, query: str, num_expansions: int = 10) -> List[str]:
        """
        Expand a search query into multiple variations.

        Args:
            query: The original search query.
            num_expansions: Number of query variations to generate (1-100).

        Returns:
            A list of expanded query strings, including the original.
        """
        # For larger expansion requests, use parallel processing
        if num_expansions >= 10:
            return self.expand_query_parallel(query, num_expansions)

        # Validate input range
        num_expansions = max(1, min(100, num_expansions))

        # Always include the original query
        expanded_queries = [query]

        # If only 1 expansion requested, just return the original query
        if num_expansions <= 1:
            return expanded_queries

        try:
            logger.info(f"Generating {num_expansions} query variations using Gemini AI...")

            # For large numbers of expansions, make multiple calls with smaller batches
            # to avoid overwhelming the API
            remaining_expansions = num_expansions
            batch_size = 5  # Process in batches of 5 for better reliability

            # For very large expansion requests, use a larger batch size for the first few batches
            if num_expansions > 50:
                logger.info(f"Large number of expansions requested ({num_expansions}). This may take a moment...")

            attempt = 0
            max_attempts = 20  # Limit the number of attempts to avoid infinite loops

            while remaining_expansions > 0 and attempt < max_attempts:
                attempt += 1
                current_batch = min(batch_size, remaining_expansions)

                logger.info(f"Batch {attempt}: Requesting {current_batch} variations...")

                # Get additional variations from Gemini
                ai_expansions = self.api_client.expand_query(
                    query=query,
                    num_expansions=current_batch
                )

                # Count new unique expansions
                new_expansions = 0

                # Add unique expansions
                for expansion in ai_expansions:
                    if expansion and expansion not in expanded_queries:
                        expanded_queries.append(expansion)
                        new_expansions += 1

                logger.info(f"Added {new_expansions} unique variations")

                # Update remaining count
                remaining_expansions -= new_expansions

                # If we didn't get any new expansions, try a slightly different approach
                if new_expansions == 0:
                    # If we're stuck, try a different prompt by adding some context
                    if attempt % 3 == 0:
                        logger.info("Trying a different approach to generate more unique variations...")
                        # Use a more specific prompt through the API client
                        context_expansions = self.api_client.expand_query(
                            query=f"alternative ways to search for {query}",
                            num_expansions=current_batch
                        )

                        # Add unique expansions
                        for expansion in context_expansions:
                            if expansion and expansion not in expanded_queries:
                                expanded_queries.append(expansion)
                                remaining_expansions -= 1

                    # If we're still stuck after multiple attempts, break to avoid wasting API calls
                    if attempt > 10:
                        logger.info("Reached maximum attempts. Using the variations collected so far.")
                        break

                # If we've collected enough variations, break
                if len(expanded_queries) >= num_expansions + 1:  # +1 for original
                    break

            # Ensure we don't exceed the requested number
            expanded_queries = expanded_queries[:num_expansions + 1]  # +1 for original

            logger.info(f"Generated {len(expanded_queries)-1} unique query variations")

            # If we couldn't generate enough variations, fill with modified versions of the original
            if len(expanded_queries) < num_expansions + 1:
                logger.info(f"Could only generate {len(expanded_queries)-1} unique variations. Adding modified versions of existing queries.")

                # Create modified versions by adding common prefixes/suffixes
                prefixes = ["latest ", "top ", "best ", "innovative ", "new "]
                suffixes = [" companies", " startups", " businesses", " ventures", " enterprises"]

                # Add variations until we reach the requested number
                existing_variations = expanded_queries.copy()
                for variation in existing_variations:
                    if len(expanded_queries) >= num_expansions + 1:
                        break

                    for prefix in prefixes:
                        modified = f"{prefix}{variation}"
                        if modified not in expanded_queries:
                            expanded_queries.append(modified)
                            if len(expanded_queries) >= num_expansions + 1:
                                break

                    if len(expanded_queries) >= num_expansions + 1:
                        break

                    for suffix in suffixes:
                        modified = f"{variation}{suffix}"
                        if modified not in expanded_queries:
                            expanded_queries.append(modified)
                            if len(expanded_queries) >= num_expansions + 1:
                                break

        except Exception as e:
            # Log the error but continue with just the original query
            logger.error(f"Error expanding query: {e}")

        return expanded_queries

    def get_search_keywords(self, query: str, max_keywords: int = 5) -> List[str]:
        """
        Extract key search terms from a query.

        Args:
            query: The search query.
            max_keywords: Maximum number of keywords to extract.

        Returns:
            List of important keywords from the query.
        """
        # Remove common words
        stopwords = [
            "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
            "with", "by", "about", "find", "search", "looking", "need", "want",
            "get", "show", "me", "list", "of", "that", "have", "has", "had"
        ]

        # Split into words and filter
        words = query.lower().split()
        keywords = [word for word in words if word not in stopwords]

        # Limit to max_keywords
        return keywords[:max_keywords]

    def generate_search_combinations(self, query: str) -> List[str]:
        """
        Generate search combinations based on the query.

        Args:
            query: The search query.

        Returns:
            List of search combinations.
        """
        # Get expanded queries
        expanded_queries = self.expand_query(query)

        # Get keywords
        keywords = self.get_search_keywords(query)

        # Create combinations
        combinations = expanded_queries.copy()

        # Add keyword combinations
        if len(keywords) >= 2:
            for i in range(len(keywords)):
                for j in range(i+1, len(keywords)):
                    combo = f"{keywords[i]} {keywords[j]}"
                    if combo not in combinations:
                        combinations.append(combo)

        return combinations
