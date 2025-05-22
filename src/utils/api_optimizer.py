"""
API optimization utilities for the Startup Finder.

This module provides utilities for optimizing API usage,
including batching, rate limiting, and retry logic.
"""

import time
import random
import logging
from typing import List, Dict, Any, Callable, Optional, Tuple, Union
from functools import wraps

# Set up logging
logger = logging.getLogger(__name__)

class APIOptimizer:
    """Utilities for optimizing API usage."""
    
    @staticmethod
    def batch_api_requests(items: List[Any], processor: Callable, batch_size: int = 10):
        """
        Process items in batches to reduce API calls.
        
        Args:
            items: List of items to process
            processor: Function to process a batch of items
            batch_size: Size of each batch
            
        Yields:
            Processed batches
        """
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            yield processor(batch)
    
    @staticmethod
    def api_call_with_backoff(func: Callable, max_retries: int = 5, 
                             initial_wait: float = 1.0, 
                             backoff_factor: float = 2.0,
                             jitter: float = 0.1):
        """
        Make an API call with exponential backoff for rate limits.
        
        Args:
            func: Function to call
            max_retries: Maximum number of retries
            initial_wait: Initial wait time in seconds
            backoff_factor: Factor to increase wait time by
            jitter: Random jitter factor to add to wait time
            
        Returns:
            Result of the function call
        """
        retries = 0
        while retries <= max_retries:
            try:
                return func()
            except Exception as e:
                retries += 1
                
                # Check if we've exceeded max retries
                if retries > max_retries:
                    logger.error(f"Max retries exceeded: {e}")
                    raise
                
                # Calculate wait time with exponential backoff and jitter
                wait_time = initial_wait * (backoff_factor ** (retries - 1))
                wait_time += random.uniform(0, jitter * wait_time)
                
                logger.warning(f"API call failed: {e}. Retrying in {wait_time:.2f} seconds...")
                time.sleep(wait_time)

class RateLimiter:
    """Rate limiter for API calls."""
    
    def __init__(self, calls_per_second: float = 1.0, calls_per_minute: float = 60.0):
        """
        Initialize the rate limiter.
        
        Args:
            calls_per_second: Maximum calls per second
            calls_per_minute: Maximum calls per minute
        """
        self.calls_per_second = calls_per_second
        self.calls_per_minute = calls_per_minute
        self.last_call_time = 0
        self.call_history = []
    
    def wait_if_needed(self):
        """
        Wait if necessary to respect rate limits.
        """
        current_time = time.time()
        
        # Check calls per second
        time_since_last_call = current_time - self.last_call_time
        min_interval = 1.0 / self.calls_per_second
        
        if time_since_last_call < min_interval:
            # Wait to respect calls per second
            wait_time = min_interval - time_since_last_call
            logger.debug(f"Rate limiting: waiting {wait_time:.2f} seconds")
            time.sleep(wait_time)
            current_time = time.time()
        
        # Check calls per minute
        self.call_history = [t for t in self.call_history if current_time - t < 60.0]
        
        if len(self.call_history) >= self.calls_per_minute:
            # Wait to respect calls per minute
            oldest_call = min(self.call_history)
            wait_time = 60.0 - (current_time - oldest_call)
            
            if wait_time > 0:
                logger.debug(f"Rate limiting: waiting {wait_time:.2f} seconds to respect calls per minute")
                time.sleep(wait_time)
                current_time = time.time()
        
        # Update state
        self.last_call_time = current_time
        self.call_history.append(current_time)

class CircuitBreaker:
    """Circuit breaker for API calls."""
    
    def __init__(self, failure_threshold: int = 5, reset_timeout: int = 60):
        """
        Initialize the circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening the circuit
            reset_timeout: Time in seconds before trying to close the circuit
        """
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF-OPEN
    
    def execute(self, func: Callable, *args, **kwargs):
        """
        Execute a function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            Result of the function call
            
        Raises:
            Exception: If the circuit is open or the function call fails
        """
        if self.state == "OPEN":
            # Check if timeout has elapsed
            if time.time() - self.last_failure_time > self.reset_timeout:
                logger.info("Circuit breaker: moving from OPEN to HALF-OPEN")
                self.state = "HALF-OPEN"
            else:
                logger.warning("Circuit breaker: circuit is OPEN")
                raise Exception("Circuit breaker is open")
        
        try:
            result = func(*args, **kwargs)
            
            # If successful and in HALF-OPEN, close the circuit
            if self.state == "HALF-OPEN":
                logger.info("Circuit breaker: moving from HALF-OPEN to CLOSED")
                self.state = "CLOSED"
                self.failure_count = 0
            
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            # If failure count exceeds threshold, open the circuit
            if self.failure_count >= self.failure_threshold:
                logger.warning(f"Circuit breaker: moving from {self.state} to OPEN after {self.failure_count} failures")
                self.state = "OPEN"
            
            raise e

def rate_limited(calls_per_second: float = 1.0, calls_per_minute: float = 60.0):
    """
    Decorator to rate limit a function.
    
    Args:
        calls_per_second: Maximum calls per second
        calls_per_minute: Maximum calls per minute
        
    Returns:
        Decorated function
    """
    rate_limiter = RateLimiter(calls_per_second, calls_per_minute)
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            rate_limiter.wait_if_needed()
            return func(*args, **kwargs)
        return wrapper
    return decorator

def with_circuit_breaker(failure_threshold: int = 5, reset_timeout: int = 60):
    """
    Decorator to add circuit breaker to a function.
    
    Args:
        failure_threshold: Number of failures before opening the circuit
        reset_timeout: Time in seconds before trying to close the circuit
        
    Returns:
        Decorated function
    """
    circuit_breaker = CircuitBreaker(failure_threshold, reset_timeout)
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return circuit_breaker.execute(func, *args, **kwargs)
        return wrapper
    return decorator

def with_retry(max_retries: int = 3, initial_wait: float = 1.0, 
              backoff_factor: float = 2.0, jitter: float = 0.1):
    """
    Decorator to add retry logic to a function.
    
    Args:
        max_retries: Maximum number of retries
        initial_wait: Initial wait time in seconds
        backoff_factor: Factor to increase wait time by
        jitter: Random jitter factor to add to wait time
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            def call_func():
                return func(*args, **kwargs)
            
            return APIOptimizer.api_call_with_backoff(
                call_func, 
                max_retries=max_retries,
                initial_wait=initial_wait,
                backoff_factor=backoff_factor,
                jitter=jitter
            )
        return wrapper
    return decorator
