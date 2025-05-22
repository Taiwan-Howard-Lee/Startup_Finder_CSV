"""
API Configuration for Startup Intelligence Finder.

This module provides configuration settings for API interactions.
"""

import os
from typing import Dict, Union


# Default configuration
DEFAULT_CONFIG = {
    "max_results": 50,        # Maximum results per search
    "min_confidence": 0.8,    # Minimum confidence score
    "include_sources": True,  # Include source URLs
    "export_format": "csv"    # Default export format
}


def get_api_key() -> str:
    """
    Get the Gemini API key from environment variables.

    Returns:
        API key string.

    Raises:
        ValueError: If API key is not found.
    """
    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        raise ValueError(
            "Gemini API key not found. Please set the GEMINI_API_KEY "
            "environment variable."
        )

    return api_key


def get_config(custom_config: Dict[str, Union[int, float, bool, str]] = None) -> Dict[str, Union[int, float, bool, str]]:
    """
    Get configuration with custom overrides.

    Args:
        custom_config: Custom configuration overrides.

    Returns:
        Configuration dictionary.
    """
    config = DEFAULT_CONFIG.copy()

    if custom_config:
        config.update(custom_config)

    return config


# API rate limiting settings
RATE_LIMIT_CONFIG = {
    "requests_per_minute": 60,
    "requests_per_day": 1000,
    "retry_after_seconds": 5,
    "max_retries": 3
}


# Gemini API settings
GEMINI_API_CONFIG = {
    "model": "gemini-2.0-flash",
    "temperature": 0.2,
    "max_output_tokens": 1024,
    "top_p": 0.8,
    "top_k": 40
}
