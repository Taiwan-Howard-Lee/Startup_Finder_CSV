"""
Batch Processor for Gemini API calls.

This module provides a batch processor for parallel processing of Gemini API calls
with proper rate limiting and error handling.
"""

import time
import logging
import concurrent.futures
from typing import List, Dict, Any, Callable, Optional

# Set up logging
logger = logging.getLogger(__name__)


class GeminiAPIBatchProcessor:
    """
    A processor for batch processing Gemini API calls in parallel.
    
    This class handles parallel processing of Gemini API calls with
    proper rate limiting and error handling.
    """
    
    def __init__(self, max_workers: int = 30, request_delay: float = 0.2):
        """
        Initialize the batch processor.
        
        Args:
            max_workers: Maximum number of parallel workers.
            request_delay: Delay between requests to avoid rate limiting.
        """
        self.max_workers = max_workers
        self.request_delay = request_delay
        self.last_request_time = 0
        
        logger.info(f"Initialized GeminiAPIBatchProcessor with {max_workers} workers")
        
    def _respect_rate_limits(self):
        """
        Ensure we respect rate limits by adding delays between requests.
        """
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.request_delay:
            sleep_time = self.request_delay - time_since_last_request
            time.sleep(sleep_time)
            
        self.last_request_time = time.time()
        
    def process_batch(self, api_client: Any, items: List[Any], 
                     process_func: Callable, *args, **kwargs) -> List[Any]:
        """
        Process a batch of items in parallel using the Gemini API.
        
        Args:
            api_client: GeminiAPIClient instance.
            items: List of items to process.
            process_func: Function to process each item.
            *args, **kwargs: Additional arguments to pass to process_func.
            
        Returns:
            List of results.
        """
        results = []
        
        print(f"Processing batch of {len(items)} items with {self.max_workers} parallel workers...")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit tasks
            future_to_item = {}
            for item in items:
                # Respect rate limits
                self._respect_rate_limits()
                
                # Submit task
                future = executor.submit(process_func, api_client, item, *args, **kwargs)
                future_to_item[future] = item
                
            # Process results as they complete
            for future in concurrent.futures.as_completed(future_to_item):
                item = future_to_item[future]
                try:
                    result = future.result()
                    results.append(result)
                    logger.debug(f"Successfully processed item: {item}")
                except Exception as e:
                    logger.error(f"Error processing item {item}: {e}")
                    # Add a placeholder result to maintain order
                    results.append({"error": str(e), "item": item})
                    
        print(f"Completed batch processing with {len(results)} results")
        return results
