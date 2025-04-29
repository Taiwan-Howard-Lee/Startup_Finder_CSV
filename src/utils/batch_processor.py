"""
Batch Processor for Gemini API calls.

This module provides a batch processor for parallel processing of Gemini API calls
with proper rate limiting, error handling, and retry mechanisms for transient errors.
"""

import time
import logging
import random
import concurrent.futures
import traceback
from typing import List, Dict, Any, Callable, Optional, Tuple, Set

# Set up logging
logger = logging.getLogger(__name__)


class GeminiAPIBatchProcessor:
    """
    A processor for batch processing Gemini API calls in parallel.

    This class handles parallel processing of Gemini API calls with
    proper rate limiting, error handling, and retry mechanisms for transient errors.
    """

    # Define transient errors that should be retried
    TRANSIENT_ERROR_MESSAGES = [
        "rate limit",
        "timeout",
        "connection",
        "network",
        "503",
        "500",
        "502",
        "504",
        "too many requests",
        "temporarily unavailable",
        "server error",
        "internal server error",
        "bad gateway",
        "gateway timeout",
        "service unavailable"
    ]

    def __init__(self, max_workers: int = 30, request_delay: float = 0.2,
                 max_retries: int = 3, retry_delay: float = 1.0,
                 memory_limit_mb: int = 500):
        """
        Initialize the batch processor.

        Args:
            max_workers: Maximum number of parallel workers.
            request_delay: Delay between requests to avoid rate limiting.
            max_retries: Maximum number of retry attempts for transient errors.
            retry_delay: Base delay between retry attempts (will be increased with backoff).
            memory_limit_mb: Memory limit in MB for batch processing.
        """
        self.max_workers = max_workers
        self.request_delay = request_delay
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.memory_limit_mb = memory_limit_mb
        self.last_request_time = 0

        logger.info(f"Initialized GeminiAPIBatchProcessor with {max_workers} workers, "
                   f"{max_retries} max retries, and {memory_limit_mb}MB memory limit")

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

    def _is_transient_error(self, error: Exception) -> bool:
        """
        Determine if an error is transient and should be retried.

        Args:
            error: The exception that occurred.

        Returns:
            True if the error is transient, False otherwise.
        """
        error_str = str(error).lower()

        # Check if the error message contains any of the transient error keywords
        for transient_msg in self.TRANSIENT_ERROR_MESSAGES:
            if transient_msg in error_str:
                return True

        # Check for specific exception types that are typically transient
        if isinstance(error, (ConnectionError, TimeoutError)):
            return True

        return False

    def _process_with_retry(self, process_func: Callable, api_client: Any,
                           item: Any, *args, **kwargs) -> Any:
        """
        Process an item with retry logic for transient errors.

        Args:
            process_func: Function to process the item.
            api_client: GeminiAPIClient instance.
            item: Item to process.
            *args, **kwargs: Additional arguments to pass to process_func.

        Returns:
            Processing result or error information.
        """
        retries = 0
        last_error = None

        while retries <= self.max_retries:
            try:
                # Respect rate limits before each attempt
                self._respect_rate_limits()

                # Process the item
                result = process_func(api_client, item, *args, **kwargs)

                # If successful, return the result
                if retries > 0:
                    logger.info(f"Successfully processed item after {retries} retries: {item}")
                return result

            except Exception as e:
                last_error = e
                error_traceback = traceback.format_exc()

                # Check if this is a transient error that should be retried
                if self._is_transient_error(e) and retries < self.max_retries:
                    retries += 1

                    # Calculate backoff delay with jitter
                    backoff_delay = self.retry_delay * (2 ** (retries - 1))
                    jitter = random.uniform(0, 0.1 * backoff_delay)  # 10% jitter
                    total_delay = backoff_delay + jitter

                    logger.warning(f"Transient error processing item {item} (attempt {retries}/{self.max_retries}): "
                                  f"{str(e)}. Retrying in {total_delay:.2f} seconds...")

                    # Wait before retrying
                    time.sleep(total_delay)
                else:
                    # Non-transient error or max retries reached
                    if retries > 0:
                        logger.error(f"Failed to process item {item} after {retries} retries: {str(e)}")
                    else:
                        logger.error(f"Error processing item {item}: {str(e)}")

                    logger.debug(f"Error traceback: {error_traceback}")
                    break

        # If we get here, all retries failed or it was a non-transient error
        return {"error": str(last_error), "item": item, "retries": retries}

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

        # Calculate batch size based on memory limit
        # This is a simple heuristic - adjust as needed
        estimated_item_size_kb = 50  # Assume average item size of 50KB
        max_batch_size = min(len(items),
                            int((self.memory_limit_mb * 1024) / estimated_item_size_kb))

        logger.info(f"Processing batch of {len(items)} items with {self.max_workers} parallel workers...")
        logger.info(f"Memory limit: {self.memory_limit_mb}MB, estimated max batch size: {max_batch_size}")

        # Process in smaller batches if needed to manage memory
        for batch_start in range(0, len(items), max_batch_size):
            batch_end = min(batch_start + max_batch_size, len(items))
            current_batch = items[batch_start:batch_end]

            if len(items) > max_batch_size:
                logger.info(f"Processing sub-batch {batch_start//max_batch_size + 1} of {(len(items) + max_batch_size - 1)//max_batch_size}: "
                           f"items {batch_start+1}-{batch_end} of {len(items)}")

            batch_results = []

            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit tasks with retry logic
                future_to_item = {}
                for item in current_batch:
                    # Submit task with retry wrapper
                    future = executor.submit(
                        self._process_with_retry, process_func, api_client, item, *args, **kwargs
                    )
                    future_to_item[future] = item

                # Process results as they complete
                for future in concurrent.futures.as_completed(future_to_item):
                    item = future_to_item[future]
                    try:
                        result = future.result()
                        batch_results.append(result)
                    except Exception as e:
                        # This should rarely happen since _process_with_retry handles exceptions
                        logger.error(f"Unexpected error in executor for item {item}: {e}")
                        batch_results.append({"error": str(e), "item": item})

            # Add batch results to overall results
            results.extend(batch_results)

            # Force garbage collection after each batch
            import gc
            gc.collect()

        logger.info(f"Completed batch processing with {len(results)} results")
        return results
