"""
Optimization utilities for the Startup Finder.

This module provides utilities for optimizing the performance of the Startup Finder,
including caching, parallel processing, memory optimization, and more.
"""

import os
import time
import pickle
import hashlib
import logging
import asyncio
import sqlite3
import numpy as np
from typing import List, Dict, Any, Callable, Optional, Tuple, Set, Union
from functools import lru_cache, wraps
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor

# Set up logging
logger = logging.getLogger(__name__)

# ===== Memory and Processing Optimizations =====

class MemoryOptimizer:
    """Utilities for optimizing memory usage."""
    
    @staticmethod
    def process_large_file_streaming(file_path: str, processor: Callable):
        """
        Process a large file line by line to avoid loading it all into memory.
        
        Args:
            file_path: Path to the file to process
            processor: Function to process each line
            
        Yields:
            Processed lines
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                yield processor(line)
    
    @staticmethod
    def chunk_large_list(items: List[Any], chunk_size: int = 100):
        """
        Process a large list in chunks to reduce memory usage.
        
        Args:
            items: List of items to process
            chunk_size: Size of each chunk
            
        Yields:
            Chunks of the list
        """
        for i in range(0, len(items), chunk_size):
            yield items[i:i + chunk_size]

# ===== Parallel Processing Optimizations =====

class ParallelProcessor:
    """Utilities for parallel processing."""
    
    @staticmethod
    def get_optimal_workers():
        """
        Get the optimal number of worker threads based on system resources.
        
        Returns:
            Optimal number of worker threads
        """
        return min(32, os.cpu_count() * 5)  # 5 threads per CPU core, max 32
    
    @staticmethod
    async def fetch_url_async(url: str, headers: Dict[str, str] = None, timeout: int = 30):
        """
        Fetch a URL asynchronously.
        
        Args:
            url: URL to fetch
            headers: HTTP headers
            timeout: Timeout in seconds
            
        Returns:
            Response text
        """
        import aiohttp
        
        if headers is None:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
            }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=timeout) as response:
                    response.raise_for_status()
                    return await response.text()
        except Exception as e:
            logger.error(f"Error fetching {url} asynchronously: {e}")
            return None
    
    @staticmethod
    async def process_urls_async(urls: List[str], headers: Dict[str, str] = None):
        """
        Process multiple URLs asynchronously.
        
        Args:
            urls: List of URLs to process
            headers: HTTP headers
            
        Returns:
            Dictionary mapping URLs to their content
        """
        tasks = [ParallelProcessor.fetch_url_async(url, headers) for url in urls]
        results = await asyncio.gather(*tasks)
        return {url: result for url, result in zip(urls, results) if result is not None}

# ===== Caching Optimizations =====

class CacheManager:
    """Manager for various caching strategies."""
    
    def __init__(self, cache_dir: str = "cache"):
        """
        Initialize the cache manager.
        
        Args:
            cache_dir: Directory to store cache files
        """
        self.cache_dir = cache_dir
        self.memory_cache = {}
        os.makedirs(cache_dir, exist_ok=True)
    
    def cache_to_disk(self, key: str, value: Any):
        """
        Cache a value to disk.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        key_hash = hashlib.md5(key.encode()).hexdigest()
        cache_file = os.path.join(self.cache_dir, f"{key_hash}.pkl")
        
        try:
            with open(cache_file, "wb") as f:
                pickle.dump(value, f)
        except Exception as e:
            logger.error(f"Error caching to disk: {e}")
    
    def load_from_disk_cache(self, key: str):
        """
        Load a value from disk cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        key_hash = hashlib.md5(key.encode()).hexdigest()
        cache_file = os.path.join(self.cache_dir, f"{key_hash}.pkl")
        
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "rb") as f:
                    return pickle.load(f)
            except Exception as e:
                logger.error(f"Error loading from disk cache: {e}")
        
        return None
    
    def cache_to_memory(self, key: str, value: Any):
        """
        Cache a value to memory.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        self.memory_cache[key] = value
    
    def load_from_memory_cache(self, key: str):
        """
        Load a value from memory cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        return self.memory_cache.get(key)
    
    def get_cached_value(self, key: str, memory_first: bool = True):
        """
        Get a cached value from memory or disk.
        
        Args:
            key: Cache key
            memory_first: Whether to check memory cache first
            
        Returns:
            Cached value or None if not found
        """
        if memory_first:
            # Check memory cache first
            value = self.load_from_memory_cache(key)
            if value is not None:
                return value
            
            # Then check disk cache
            value = self.load_from_disk_cache(key)
            if value is not None:
                # Cache in memory for faster access next time
                self.cache_to_memory(key, value)
            return value
        else:
            # Check disk cache first
            value = self.load_from_disk_cache(key)
            if value is not None:
                # Cache in memory for faster access next time
                self.cache_to_memory(key, value)
                return value
            
            # Then check memory cache
            return self.load_from_memory_cache(key)
    
    def cache_value(self, key: str, value: Any, memory: bool = True, disk: bool = True):
        """
        Cache a value to memory and/or disk.
        
        Args:
            key: Cache key
            value: Value to cache
            memory: Whether to cache to memory
            disk: Whether to cache to disk
        """
        if memory:
            self.cache_to_memory(key, value)
        
        if disk:
            self.cache_to_disk(key, value)

# Create a global cache manager instance
cache_manager = CacheManager()

# LRU cache decorator for API calls
def lru_cache_api_call(maxsize: int = 1000):
    """
    Decorator to cache API calls using LRU cache.
    
    Args:
        maxsize: Maximum size of the cache
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @lru_cache(maxsize=maxsize)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator
