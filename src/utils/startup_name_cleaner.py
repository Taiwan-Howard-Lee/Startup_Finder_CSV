"""
Startup Name Cleaner

This module provides utilities for cleaning and deduplicating startup names
using LLM-based processing to ensure high-quality results.
"""

import os
import re
import csv
import time
import json
import logging
from typing import List, Dict, Any, Set, Tuple, Optional
from collections import defaultdict

# Import API client
from src.utils.api_client import GeminiAPIClient

# Set up logging
logger = logging.getLogger(__name__)

class StartupNameCleaner:
    """Clean and deduplicate startup names using LLM-based processing."""

    def __init__(self, api_client: Optional[GeminiAPIClient] = None):
        """
        Initialize the startup name cleaner.

        Args:
            api_client: Optional GeminiAPIClient instance
        """
        self.api_client = api_client or GeminiAPIClient()
        self.name_cache = {}  # Cache for cleaned names

    def clean_name(self, name: str) -> str:
        """
        Clean a single startup name.

        Args:
            name: Startup name to clean

        Returns:
            Cleaned startup name
        """
        # Check cache first
        if name in self.name_cache:
            return self.name_cache[name]

        # Basic cleaning
        cleaned_name = self._basic_clean(name)

        # Cache and return
        self.name_cache[name] = cleaned_name
        return cleaned_name

    def _basic_clean(self, name: str) -> str:
        """
        Perform basic cleaning on a startup name.

        Args:
            name: Startup name to clean

        Returns:
            Cleaned startup name
        """
        # Remove common suffixes
        suffixes = [
            r'\s+Inc\.?$', r'\s+LLC\.?$', r'\s+Ltd\.?$', r'\s+Limited$',
            r'\s+Corp\.?$', r'\s+Corporation$', r'\s+Co\.?$', r'\s+Company$',
            r'\s+GmbH$', r'\s+S\.?A\.?$', r'\s+B\.?V\.?$', r'\s+P\.?L\.?C\.?$'
        ]

        for suffix in suffixes:
            name = re.sub(suffix, '', name, flags=re.IGNORECASE)

        # Remove quotes and special characters
        name = re.sub(r'[\'"`]', '', name)

        # Normalize whitespace
        name = re.sub(r'\s+', ' ', name).strip()

        return name

    def deduplicate_names(self, names: List[str], query: str = "") -> List[str]:
        """
        Deduplicate a list of startup names using LLM-based processing.

        Args:
            names: List of startup names to deduplicate
            query: Original search query for context

        Returns:
            Deduplicated list of startup names
        """
        if not names:
            return []

        # First, apply basic cleaning to all names
        cleaned_names = [self.clean_name(name) for name in names]

        # Group similar names
        name_groups = self._group_similar_names(cleaned_names)

        # Use LLM to select the best name from each group
        deduplicated_names = self._select_best_names(name_groups, query)

        logger.info(f"Deduplicated {len(names)} names to {len(deduplicated_names)} unique startups")
        return deduplicated_names

    def _group_similar_names(self, names: List[str]) -> List[List[str]]:
        """
        Group similar startup names together.

        Args:
            names: List of startup names

        Returns:
            List of groups of similar names
        """
        # Create a mapping of normalized names to original names
        normalized_to_original = defaultdict(list)

        for name in names:
            # Create a normalized version for comparison
            normalized = self._normalize_for_comparison(name)
            normalized_to_original[normalized].append(name)

        # Create groups of similar names
        name_groups = []
        processed_names = set()

        # First, add exact duplicates as groups
        for normalized, originals in normalized_to_original.items():
            if len(originals) > 1:
                name_groups.append(originals)
                processed_names.update(originals)

        # Find similar names using fuzzy matching
        remaining_names = [name for name in names if name not in processed_names]

        if remaining_names:
            # Group similar names
            similar_groups = self._find_similar_names(remaining_names)

            # Add groups with multiple names
            for group in similar_groups:
                if len(group) > 1:
                    name_groups.append(group)
                    processed_names.update(group)

        # Then, add remaining names as individual groups
        for name in names:
            if name not in processed_names:
                name_groups.append([name])

        return name_groups

    def _find_similar_names(self, names: List[str]) -> List[List[str]]:
        """
        Find similar names using fuzzy matching.

        Args:
            names: List of names to group

        Returns:
            List of groups of similar names
        """
        # Try to use fuzzy matching if available
        try:
            from difflib import SequenceMatcher

            # Calculate similarity matrix
            n = len(names)
            similarity_matrix = [[0.0 for _ in range(n)] for _ in range(n)]

            for i in range(n):
                for j in range(i, n):
                    if i == j:
                        similarity_matrix[i][j] = 1.0
                    else:
                        # Calculate similarity ratio
                        ratio = SequenceMatcher(None, names[i].lower(), names[j].lower()).ratio()
                        similarity_matrix[i][j] = ratio
                        similarity_matrix[j][i] = ratio

            # Group similar names
            threshold = 0.8  # Similarity threshold
            groups = []
            used_indices = set()

            for i in range(n):
                if i in used_indices:
                    continue

                # Find similar names
                group = [names[i]]
                used_indices.add(i)

                for j in range(n):
                    if j != i and j not in used_indices and similarity_matrix[i][j] >= threshold:
                        group.append(names[j])
                        used_indices.add(j)

                if group:
                    groups.append(group)

            return groups

        except Exception as e:
            logger.warning(f"Error using fuzzy matching: {e}")
            # Fallback to basic grouping
            return [[name] for name in names]

    def _normalize_for_comparison(self, name: str) -> str:
        """
        Normalize a name for comparison purposes.

        Args:
            name: Name to normalize

        Returns:
            Normalized name
        """
        # Convert to lowercase
        normalized = name.lower()

        # Remove all non-alphanumeric characters
        normalized = re.sub(r'[^a-z0-9]', '', normalized)

        return normalized

    def _select_best_names(self, name_groups: List[List[str]], query: str) -> List[str]:
        """
        Select the best name from each group using LLM.

        Args:
            name_groups: List of groups of similar names
            query: Original search query for context

        Returns:
            List of selected best names
        """
        # For groups with only one name, use that name
        single_name_groups = [group[0] for group in name_groups if len(group) == 1]

        # For groups with multiple names, use LLM to select the best one
        multi_name_groups = [group for group in name_groups if len(group) > 1]

        if not multi_name_groups:
            return single_name_groups

        # Process in batches to avoid large API calls
        batch_size = 10
        selected_names = []

        for i in range(0, len(multi_name_groups), batch_size):
            batch = multi_name_groups[i:i+batch_size]
            batch_selected = self._process_name_batch(batch, query)
            selected_names.extend(batch_selected)

        # Combine with single name groups
        return single_name_groups + selected_names

    def _process_name_batch(self, name_groups: List[List[str]], query: str) -> List[str]:
        """
        Process a batch of name groups with the LLM.

        Args:
            name_groups: List of groups of similar names
            query: Original search query for context

        Returns:
            List of selected best names
        """
        # Create the prompt
        prompt = f"""
        You are a startup name standardization expert. Your task is to select the best, most accurate name for each startup from groups of similar names.

        Original search query: {query}

        For each group of similar names below, select the most accurate and standardized name. Consider:
        1. Proper capitalization
        2. Removal of unnecessary suffixes (Inc, LLC, Ltd, etc.)
        3. Consistency in formatting
        4. Accuracy and completeness

        Return your selections as a JSON array of strings, with one name selected from each group.

        Groups of similar names:
        {json.dumps(name_groups, indent=2)}
        """

        try:
            # Call the LLM
            response = self.api_client.generate_content(
                prompt,
                model="gemini-2.0-flash",
                temperature=0.1,
                max_tokens=1024
            )

            # Extract the JSON array from the response
            response_text = response.text

            # Find JSON array in the response
            json_start = response_text.find('[')
            json_end = response_text.rfind(']') + 1

            if json_start >= 0 and json_end > json_start:
                json_text = response_text[json_start:json_end]
                selected_names = json.loads(json_text)

                # Ensure we have the right number of names
                if len(selected_names) == len(name_groups):
                    return selected_names
                else:
                    logger.warning(f"LLM returned {len(selected_names)} names, expected {len(name_groups)}")

            # If JSON parsing fails, use the first name from each group
            logger.warning("Failed to parse LLM response, using first name from each group")
            return [group[0] for group in name_groups]

        except Exception as e:
            logger.error(f"Error processing name batch with LLM: {e}")
            # Fallback to using the first name from each group
            return [group[0] for group in name_groups]

    def clean_and_deduplicate_csv(self, input_file: str, output_file: str, name_column: str = "Company Name", query: str = "") -> int:
        """
        Clean and deduplicate startup names in a CSV file.

        Args:
            input_file: Path to input CSV file
            output_file: Path to output CSV file
            name_column: Name of the column containing startup names
            query: Original search query for context

        Returns:
            Number of unique startups after deduplication
        """
        try:
            # Read the input CSV
            with open(input_file, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)

                if not rows:
                    logger.warning(f"No data found in {input_file}")
                    return 0

                # Extract startup names
                names = [row.get(name_column, "") for row in rows if row.get(name_column)]

                if not names:
                    logger.warning(f"No startup names found in column '{name_column}'")
                    return 0

                logger.info(f"Found {len(names)} startup names in {input_file}")

                # Create a mapping of original names to rows
                name_to_rows = defaultdict(list)
                for row in rows:
                    name = row.get(name_column, "")
                    if name:
                        name_to_rows[name].append(row)

                # Deduplicate names
                unique_names = self.deduplicate_names(names, query)

                # Create a mapping of cleaned names to original names
                cleaned_to_original = {}
                for name in names:
                    cleaned = self.clean_name(name)
                    if cleaned not in cleaned_to_original:
                        cleaned_to_original[cleaned] = name

                # Create output rows with deduplicated names
                output_rows = []
                for unique_name in unique_names:
                    # Find the original name that corresponds to this unique name
                    original_name = cleaned_to_original.get(self.clean_name(unique_name), unique_name)

                    # Get the rows for this original name
                    rows_for_name = name_to_rows.get(original_name, [])

                    if rows_for_name:
                        # Use the first row for this name
                        row = rows_for_name[0].copy()

                        # Update the name to the cleaned version
                        row[name_column] = unique_name

                        output_rows.append(row)

                # Write the output CSV
                if output_rows:
                    with open(output_file, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=output_rows[0].keys())
                        writer.writeheader()
                        writer.writerows(output_rows)

                    logger.info(f"Wrote {len(output_rows)} deduplicated startups to {output_file}")
                    return len(output_rows)
                else:
                    logger.warning("No output rows generated")
                    return 0

        except Exception as e:
            logger.error(f"Error cleaning and deduplicating CSV: {e}")
            return 0

# Create a function to clean and deduplicate a CSV file
def clean_and_deduplicate_startups(input_file: str, output_file: str = None, query: str = "") -> str:
    """
    Clean and deduplicate startup names in a CSV file.

    Args:
        input_file: Path to input CSV file
        output_file: Path to output CSV file (optional)
        query: Original search query for context

    Returns:
        Path to the output CSV file
    """
    # Create default output file if not provided
    if not output_file:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.dirname(input_file)
        filename = os.path.basename(input_file)
        name, ext = os.path.splitext(filename)
        output_file = os.path.join(output_dir, f"{name}_deduplicated_{timestamp}{ext}")

    # Create the cleaner
    cleaner = StartupNameCleaner()

    # Clean and deduplicate
    num_startups = cleaner.clean_and_deduplicate_csv(input_file, output_file, query=query)

    logger.info(f"Cleaned and deduplicated {input_file} to {output_file} with {num_startups} unique startups")
    return output_file
