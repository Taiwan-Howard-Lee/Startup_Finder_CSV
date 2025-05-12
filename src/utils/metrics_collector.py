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
        self.urls_discovered = 0
        self.urls_processed = 0
        self.urls_blocked_robots = 0
        self.urls_skipped_duplicate = 0
        self.urls_failed = 0
        self.urls_cache_hit = 0
        self.processed_urls = set()  # Store actual URLs processed
        self.blocked_urls = set()    # Store URLs blocked by robots.txt
        self.failed_urls = set()     # Store URLs that failed to fetch

        # Startup metrics
        self.potential_startups_found = 0
        self.startups_after_pattern = 0
        self.startups_after_llm = 0
        self.startups_after_validation = 0
        self.startups_eliminated = 0
        self.final_unique_startups = 0

        # Startup name tracking at each stage
        self.potential_startup_names = set()  # All potential names found
        self.pattern_extracted_names = set()  # Names found by pattern matching
        self.llm_extracted_names = set()      # Names found by LLM
        self.validated_names = set()          # Names that passed validation
        self.eliminated_names = set()         # Names that were filtered out
        self.final_startup_names = set()      # Final unique startup names

        # Track startup names by source
        self.startups_by_source = defaultdict(set)  # Map source URL to startup names

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

    def add_potential_startup_name(self, name: str, source_url: str = None):
        """Add a potential startup name."""
        self.potential_startup_names.add(name)
        self.potential_startups_found = len(self.potential_startup_names)
        if source_url:
            self.startups_by_source[source_url].add(name)

    def add_pattern_extracted_name(self, name: str):
        """
        Add a startup name found by pattern matching.

        Note: This method is kept for backward compatibility but is no longer used
        in the main extraction flow since pattern matching has been removed.
        """
        # This method is kept for backward compatibility
        # Pattern matching has been removed from the main extraction flow
        self.pattern_extracted_names.add(name)
        self.startups_after_pattern = len(self.pattern_extracted_names)

    def add_llm_extracted_name(self, name: str):
        """Add a startup name found by LLM."""
        self.llm_extracted_names.add(name)
        self.startups_after_llm = len(self.llm_extracted_names)

    def add_validated_name(self, name: str):
        """Add a validated startup name."""
        self.validated_names.add(name)
        self.startups_after_validation = len(self.validated_names)

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

    def add_processed_url(self, url: str, processing_time: float = None):
        """Add a processed URL with optional processing time."""
        self.processed_urls.add(url)
        self.urls_processed = len(self.processed_urls)
        if processing_time is not None:
            self.url_processing_times.append(processing_time)
            self.url_processing_time_map[url] = processing_time

    def add_blocked_url(self, url: str):
        """Add a URL blocked by robots.txt."""
        self.blocked_urls.add(url)
        self.urls_blocked_robots = len(self.blocked_urls)

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

    def report(self):
        """Generate a comprehensive performance report."""
        # Calculate eliminated names first
        self.calculate_eliminated_names()

        # Calculate derived metrics
        elapsed_time = time.time() - self.start_time

        # URL metrics
        url_success_rate = self.urls_processed / max(1, len(self.processed_urls) + len(self.failed_urls)) * 100
        cache_hit_rate = self.urls_cache_hit / max(1, self.urls_processed) * 100

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

        # Create report
        report = {
            "elapsed_time": elapsed_time,
            "url_metrics": {
                "discovered": len(self.processed_urls) + len(self.failed_urls) + len(self.blocked_urls),
                "processed": self.urls_processed,
                "blocked_by_robots": self.urls_blocked_robots,
                "skipped_duplicates": self.urls_skipped_duplicate,
                "failed": self.urls_failed,
                "cache_hits": self.urls_cache_hit,
                "success_rate": url_success_rate,
                "cache_hit_rate": cache_hit_rate
            },
            "startup_metrics": {
                "potential_found": self.potential_startups_found,
                "after_pattern_extraction": self.startups_after_pattern,
                "after_llm_extraction": self.startups_after_llm,
                "after_validation": self.startups_after_validation,
                "eliminated": self.startups_eliminated,
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
            }
        }

        return report
