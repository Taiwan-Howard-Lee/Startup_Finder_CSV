#!/usr/bin/env python3
"""
API Key Manager for handling multiple API keys and CX IDs.

This module provides a class for managing and rotating between multiple
Google Search API keys and Custom Search Engine IDs to avoid rate limits.
"""

import os
import time
import logging
import random
from typing import Tuple, Dict, List, Optional

# Get logger for this module
logger = logging.getLogger(__name__)

class APIKeyManager:
    """
    Manages multiple API keys and CX IDs for Google Search API.
    
    This class handles the rotation of API keys and CX IDs to maximize
    throughput and avoid rate limits. It tracks usage, errors, and
    implements cooldown periods for keys that hit rate limits.
    """
    
    def __init__(self):
        """Initialize the API Key Manager."""
        # Load all API keys and CX IDs from environment variables
        self.api_keys = []
        self.cx_ids = []
        
        # Load API keys
        i = 1
        while True:
            key = os.environ.get(f"GOOGLE_SEARCH_API_KEY_{i}")
            if not key:
                break
            self.api_keys.append(key)
            i += 1
        
        # Load CX IDs
        i = 1
        while True:
            cx = os.environ.get(f"GOOGLE_CX_ID_{i}")
            if not cx:
                break
            self.cx_ids.append(cx)
            i += 1
        
        # If no keys were found, try legacy keys
        if not self.api_keys:
            legacy_key = os.environ.get("GOOGLE_SEARCH_API_KEY")
            if legacy_key:
                self.api_keys.append(legacy_key)
                logger.warning("Using legacy GOOGLE_SEARCH_API_KEY. Consider updating to numbered keys.")
        
        if not self.cx_ids:
            legacy_cx = os.environ.get("GOOGLE_CX_ID")
            if legacy_cx:
                self.cx_ids.append(legacy_cx)
                logger.warning("Using legacy GOOGLE_CX_ID. Consider updating to numbered CX IDs.")
        
        # Validate that we have at least one key and CX ID
        if not self.api_keys:
            raise ValueError("No Google Search API keys found in environment variables")
        if not self.cx_ids:
            raise ValueError("No Google Custom Search Engine IDs found in environment variables")
        
        logger.info(f"Loaded {len(self.api_keys)} API keys and {len(self.cx_ids)} CX IDs")
        
        # Initialize counters
        self.current_key_index = 0
        self.current_cx_index = 0
        
        # Track usage and rate limits
        self.key_usage: Dict[str, int] = {key: 0 for key in self.api_keys}
        self.key_last_used: Dict[str, float] = {key: 0 for key in self.api_keys}
        self.key_cooldown: Dict[str, float] = {key: 0 for key in self.api_keys}
        
        # Track errors
        self.key_errors: Dict[str, int] = {key: 0 for key in self.api_keys}
        self.cx_errors: Dict[str, int] = {cx: 0 for cx in self.cx_ids}
        
        # Daily quota tracking (reset at midnight)
        self.daily_quota = 100  # Default daily quota per key
        self.daily_usage: Dict[str, int] = {key: 0 for key in self.api_keys}
        self.last_reset = time.time()
    
    def _check_reset_daily_quota(self) -> None:
        """Reset daily quota if it's a new day."""
        current_time = time.time()
        # Check if it's a new day (86400 seconds in a day)
        if current_time - self.last_reset > 86400:
            self.daily_usage = {key: 0 for key in self.api_keys}
            self.last_reset = current_time
            logger.info("Reset daily quota counters")
    
    def _get_available_keys(self) -> List[str]:
        """Get a list of available API keys (not in cooldown and not at quota)."""
        self._check_reset_daily_quota()
        current_time = time.time()
        
        available_keys = []
        for key in self.api_keys:
            # Skip keys in cooldown
            if current_time < self.key_cooldown[key]:
                continue
            
            # Skip keys at quota
            if self.daily_usage[key] >= self.daily_quota:
                continue
            
            available_keys.append(key)
        
        return available_keys
    
    def get_next_key_pair(self) -> Tuple[str, str]:
        """
        Get the next available API key and CX ID pair.
        
        Returns:
            Tuple[str, str]: A tuple containing (api_key, cx_id)
            
        Raises:
            RuntimeError: If no available keys are found
        """
        available_keys = self._get_available_keys()
        
        if not available_keys:
            # If all keys are in cooldown or at quota, use the one with the earliest cooldown end
            if self.api_keys:
                key = min(self.api_keys, key=lambda k: self.key_cooldown[k])
                cooldown_remaining = max(0, self.key_cooldown[key] - time.time())
                if cooldown_remaining > 0:
                    logger.warning(f"All keys in cooldown. Using key with shortest cooldown ({cooldown_remaining:.1f}s remaining)")
                else:
                    logger.warning("All keys at quota. Using first key anyway.")
            else:
                raise RuntimeError("No API keys available")
        else:
            # Choose a random key from available keys to distribute load
            key = random.choice(available_keys)
        
        # Choose a random CX ID
        cx = random.choice(self.cx_ids)
        
        # Update usage tracking
        self.key_usage[key] += 1
        self.daily_usage[key] += 1
        self.key_last_used[key] = time.time()
        
        # Log usage for debugging
        logger.debug(f"Using API key {key[:10]}... ({self.daily_usage[key]}/{self.daily_quota}) with CX {cx[:10]}...")
        
        return key, cx
    
    def report_error(self, key: str, cx: str, error_code: int) -> None:
        """
        Report an error with a key or CX ID.
        
        Args:
            key: The API key that encountered an error
            cx: The CX ID that encountered an error
            error_code: The HTTP error code
        """
        # Track errors
        self.key_errors[key] += 1
        self.cx_errors[cx] += 1
        
        # Handle rate limit errors
        if error_code == 429:  # Too Many Requests
            # Implement exponential backoff cooldown
            cooldown_duration = min(60 * (2 ** (self.key_errors[key] % 5)), 3600)  # Max 1 hour cooldown
            self.key_cooldown[key] = time.time() + cooldown_duration
            logger.warning(f"API key {key[:10]}... hit rate limit. Cooldown for {cooldown_duration} seconds")
        elif error_code == 403:  # Forbidden (possibly quota exceeded)
            # Assume daily quota is exceeded
            self.daily_usage[key] = self.daily_quota
            logger.warning(f"API key {key[:10]}... quota exceeded. Marked as unavailable for today")
        
        # Log the error
        logger.warning(f"API error with key {key[:10]}... and CX {cx[:10]}...: {error_code}")
    
    def get_usage_stats(self) -> Dict[str, any]:
        """Get usage statistics for all keys and CX IDs."""
        return {
            "api_keys": len(self.api_keys),
            "cx_ids": len(self.cx_ids),
            "total_usage": sum(self.key_usage.values()),
            "daily_usage": self.daily_usage,
            "errors": {key: self.key_errors[key] for key in self.api_keys},
            "cooldowns": {key: max(0, self.key_cooldown[key] - time.time()) for key in self.api_keys}
        }
