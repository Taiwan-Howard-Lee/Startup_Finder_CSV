"""
Metrics collector for tracking performance and startup names at different stages.
"""

import time
import os
import json
import csv
from typing import Dict, Any, List, Optional, Set, Tuple
from collections import defaultdict

class MetricsCollector:
    """Collects and reports performance metrics for the Startup Finder."""

    def __init__(self):
        # URL metrics
        self.urls_processed = 0
        self.urls_failed = 0
        self.urls_blocked_robots = 0  # Counter for URLs blocked by robots.txt
        self.processed_urls = set()  # Store actual URLs processed
        self.failed_urls = set()     # Store URLs that failed to fetch

        # Startup metrics
        self.potential_startups_found = 0
        self.startups_after_llm = 0
        self.startups_after_validation = 0
        self.final_unique_startups = 0

        # Startup name tracking at each stage
        self.potential_startup_names = set()  # All potential names found
        self.llm_extracted_names = set()      # Names found by LLM
        self.validated_names = set()          # Names that passed validation
        self.filtered_names = set()           # Names that passed relevance filtering
        self.final_startup_names = set()      # Final unique startup names

        # Track startup names by source
        self.startups_by_source = defaultdict(set)  # Map source URL to startup names

        # Track startup mentions with context
        self.startup_mentions = defaultdict(list)  # Map startup name to list of mention contexts
        self.url_content_map = {}  # Map URL to cleaned content

        # Track keyword relevance
        self.startup_keywords = defaultdict(dict)  # Map startup name to keyword relevance scores

        # Funding information tracking has been removed

        # Track mention trends over time
        self.mention_timestamps = defaultdict(list)  # Map startup name to list of mention timestamps

        # Extraction metrics
        self.website_extraction_attempts = 0
        self.website_extraction_successes = 0
        self.linkedin_extraction_attempts = 0
        self.linkedin_extraction_successes = 0
        self.crunchbase_extraction_attempts = 0
        self.crunchbase_extraction_successes = 0
        self.fallback_usages = 0

        # Field completion metrics
        self.field_counts = defaultdict(int)
        self.total_startups = 0
        self.field_values = defaultdict(dict)  # Store actual field values for each startup

        # Time metrics
        self.url_processing_times = []
        self.startup_enrichment_times = []
        self.url_processing_time_map = {}  # Map URL to processing time
        self.startup_enrichment_time_map = {}  # Map startup name to enrichment time

        # API metrics
        self.google_api_calls = 0
        self.gemini_api_calls = 0
        self.api_call_timestamps = []  # Track when API calls were made

        # Query metrics
        self.queries_processed = []  # Store all queries processed
        self.query_startup_map = defaultdict(set)  # Map query to startups found

        # Start time
        self.start_time = time.time()

    def add_potential_startup_name(self, name: str, source_url: str = None, context: str = None):
        """
        Add a potential startup name with optional context.

        Args:
            name: The startup name
            source_url: The URL where the name was found
            context: The paragraph or context where the name was mentioned
        """
        self.potential_startup_names.add(name)
        self.potential_startups_found = len(self.potential_startup_names)
        if source_url:
            self.startups_by_source[source_url].add(name)

        # Store the mention context if provided
        if context:
            timestamp = time.time()
            self.startup_mentions[name].append({
                "url": source_url,
                "context": context,
                "stage": "potential",
                "timestamp": timestamp
            })

            # Track mention timestamp for trend analysis
            self.mention_timestamps[name].append(timestamp)

    def add_keyword_relevance(self, startup_name: str, keyword: str, relevance_score: float):
        """
        Add keyword relevance score for a startup.

        Args:
            startup_name: The startup name
            keyword: The keyword or topic
            relevance_score: A score from 0.0 to 1.0 indicating relevance
        """
        self.startup_keywords[startup_name][keyword] = relevance_score

    # Funding information method has been removed

    def add_llm_extracted_name(self, name: str):
        """Add a startup name found by LLM."""
        self.llm_extracted_names.add(name)
        self.startups_after_llm = len(self.llm_extracted_names)

    def add_validated_name(self, name: str):
        """Add a validated startup name."""
        self.validated_names.add(name)
        self.startups_after_validation = len(self.validated_names)

    def add_filtered_name(self, name: str):
        """Add a startup name that passed relevance filtering."""
        self.filtered_names.add(name)
        # We don't need to track a count for this since it's just before final

    def add_final_startup(self, name: str, data: Dict[str, Any]):
        """Add a final startup with its data."""
        self.final_startup_names.add(name)
        self.final_unique_startups = len(self.final_startup_names)
        self.total_startups += 1

        # Track field completion
        for field, value in data.items():
            if value:
                self.field_counts[field] += 1
                self.field_values[name][field] = value

    def calculate_eliminated_names(self):
        """Calculate names that were eliminated during the process."""
        # Names that were potential but not in final list
        self.eliminated_names = self.potential_startup_names - self.final_startup_names
        self.startups_eliminated = len(self.eliminated_names)

    def add_processed_url(self, url: str, processing_time: float = None, content: str = None):
        """
        Add a processed URL with optional processing time and content.

        Args:
            url: The URL that was processed
            processing_time: The time taken to process the URL
            content: The cleaned content from the URL
        """
        self.processed_urls.add(url)
        self.urls_processed = len(self.processed_urls)
        if processing_time is not None:
            self.url_processing_times.append(processing_time)
            self.url_processing_time_map[url] = processing_time

        # Store the cleaned content if provided
        if content:
            self.url_content_map[url] = content

    def add_blocked_url(self, url: str):
        """Add a URL blocked by robots.txt."""
        # We no longer track the URLs themselves, just count them
        self.urls_blocked_robots += 1

    def add_failed_url(self, url: str):
        """Add a URL that failed to fetch."""
        self.failed_urls.add(url)
        self.urls_failed = len(self.failed_urls)

    def add_query(self, query: str):
        """Add a processed query."""
        self.queries_processed.append(query)

    def map_query_to_startups(self, query: str, startup_names: List[str]):
        """Map a query to the startups found from it."""
        for name in startup_names:
            self.query_startup_map[query].add(name)

    def extract_context_for_startup(self, startup_name: str, url: str, window_size: int = 200) -> str:
        """
        Extract context for a startup name from the content of a URL.

        Args:
            startup_name: The startup name to find context for
            url: The URL where the startup was mentioned
            window_size: The number of characters to include before and after the mention

        Returns:
            The context paragraph or an empty string if not found
        """
        # OPTIMIZATION: Skip context extraction for common words to reduce processing time
        if startup_name.lower() in ["share", "view", "click", "read", "more", "next", "previous"]:
            return []

        # Skip if URL content is not available
        if url not in self.url_content_map:
            return []

        content = self.url_content_map[url]

        # Skip if content is too large (over 100,000 characters)
        if len(content) > 100000:
            # Return a minimal context to avoid excessive processing
            return [f"Context extraction skipped for {startup_name} due to large content size"]

        # Find all occurrences of the startup name in the content
        name_lower = startup_name.lower()
        content_lower = content.lower()

        contexts = []

        # OPTIMIZATION: Only find the first occurrence to reduce processing time
        pos = content_lower.find(name_lower)
        if pos == -1:
            return []

        # Extract context around the mention
        context_start = max(0, pos - window_size)
        context_end = min(len(content), pos + len(startup_name) + window_size)

        # Try to expand to paragraph boundaries - with limits to avoid excessive processing
        max_iterations = 100  # Prevent infinite loops
        iterations = 0

        while context_start > 0 and content[context_start] != '\n' and iterations < max_iterations:
            context_start -= 1
            iterations += 1

        iterations = 0
        while context_end < len(content) and content[context_end] != '\n' and iterations < max_iterations:
            context_end += 1
            iterations += 1

        # Extract the context
        context = content[context_start:context_end].strip()

        # Highlight the startup name in the context
        highlight_start = pos - context_start
        highlight_end = highlight_start + len(startup_name)

        # Ensure highlight indices are valid
        if 0 <= highlight_start < len(context) and highlight_end <= len(context):
            highlighted_context = (
                context[:highlight_start] +
                "**" + context[highlight_start:highlight_end] + "**" +
                context[highlight_end:]
            )
            contexts.append(highlighted_context)
        else:
            # If indices are invalid, just return the context without highlighting
            contexts.append(context)

        return contexts

    def report(self):
        """Generate a comprehensive performance report."""
        # Calculate eliminated names first
        self.calculate_eliminated_names()

        # Calculate derived metrics
        elapsed_time = time.time() - self.start_time

        # URL metrics
        url_success_rate = self.urls_processed / max(1, len(self.processed_urls) + len(self.failed_urls)) * 100

        # Startup metrics
        startup_conversion_rate = self.final_unique_startups / max(1, self.potential_startups_found) * 100

        # Extraction metrics
        website_success_rate = self.website_extraction_successes / max(1, self.website_extraction_attempts) * 100
        linkedin_success_rate = self.linkedin_extraction_successes / max(1, self.linkedin_extraction_attempts) * 100
        crunchbase_success_rate = self.crunchbase_extraction_successes / max(1, self.crunchbase_extraction_attempts) * 100

        # Field completion metrics
        field_completion = {field: count / max(1, self.total_startups) * 100
                           for field, count in self.field_counts.items()}

        # Time metrics
        avg_url_time = sum(self.url_processing_times) / max(1, len(self.url_processing_times))
        avg_startup_time = sum(self.startup_enrichment_times) / max(1, len(self.startup_enrichment_times))

        # Trend analysis metrics
        mention_trends = {}
        for name, timestamps in self.mention_timestamps.items():
            if name in self.final_startup_names and timestamps:
                # Group mentions by day
                from datetime import datetime
                days = {}
                for ts in timestamps:
                    day = datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
                    days[day] = days.get(day, 0) + 1

                # Sort by day
                sorted_days = sorted(days.items())

                mention_trends[name] = {
                    "total_mentions": len(timestamps),
                    "first_mention": datetime.fromtimestamp(min(timestamps)).strftime('%Y-%m-%d'),
                    "last_mention": datetime.fromtimestamp(max(timestamps)).strftime('%Y-%m-%d'),
                    "daily_mentions": dict(sorted_days)
                }

        # Keyword relevance metrics
        keyword_metrics = {}
        for name, keywords in self.startup_keywords.items():
            if name in self.final_startup_names and keywords:
                # Sort keywords by relevance score
                sorted_keywords = sorted(keywords.items(), key=lambda x: x[1], reverse=True)
                keyword_metrics[name] = {
                    "top_keywords": dict(sorted_keywords[:5]),  # Top 5 keywords
                    "keyword_count": len(keywords)
                }

        # Funding information metrics have been removed
        funding_metrics = {}

        # Create report
        report = {
            "elapsed_time": elapsed_time,
            "url_metrics": {
                "processed": self.urls_processed,
                "failed": self.urls_failed,
                "success_rate": url_success_rate
            },
            "startup_metrics": {
                "potential_found": self.potential_startups_found,
                "after_llm_extraction": self.startups_after_llm,
                "after_validation": self.startups_after_validation,
                "after_relevance_filtering": len(self.filtered_names),
                "final_unique": self.final_unique_startups,
                "conversion_rate": startup_conversion_rate
            },
            "extraction_metrics": {
                "website_success_rate": website_success_rate,
                "linkedin_success_rate": linkedin_success_rate,
                "crunchbase_success_rate": crunchbase_success_rate,
                "fallback_usages": self.fallback_usages
            },
            "field_completion": field_completion,
            "time_metrics": {
                "avg_url_processing_time": avg_url_time,
                "avg_startup_enrichment_time": avg_startup_time,
                "total_elapsed_time": elapsed_time
            },
            "api_metrics": {
                "google_api_calls": self.google_api_calls,
                "gemini_api_calls": self.gemini_api_calls
            },
            "query_metrics": {
                "queries_processed": len(self.queries_processed),
                "avg_startups_per_query": sum(len(startups) for startups in self.query_startup_map.values()) / max(1, len(self.query_startup_map))
            },
            "trend_metrics": mention_trends,
            "keyword_metrics": keyword_metrics,
            "funding_metrics": funding_metrics
        }

        return report
