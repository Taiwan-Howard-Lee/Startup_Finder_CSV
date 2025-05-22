"""
Progressive loader for the Startup Finder.

This module provides utilities for progressive loading and processing,
including incremental processing, early stopping, and feedback.
"""

import time
import logging
from typing import List, Dict, Any, Callable, Optional, Tuple, Union, Generator

# Set up logging
logger = logging.getLogger(__name__)

class ProgressiveLoader:
    """Utilities for progressive loading and processing."""
    
    @staticmethod
    def process_with_feedback(items: List[Any], processor: Callable, 
                             feedback_interval: int = 10,
                             callback: Optional[Callable] = None):
        """
        Process items with periodic feedback.
        
        Args:
            items: List of items to process
            processor: Function to process each item
            feedback_interval: Interval for feedback
            callback: Callback function for feedback
            
        Yields:
            Processed items
        """
        start_time = time.time()
        total_items = len(items)
        
        for i, item in enumerate(items):
            # Process the item
            result = processor(item)
            
            # Provide feedback at intervals
            if callback and (i % feedback_interval == 0 or i == total_items - 1):
                elapsed_time = time.time() - start_time
                remaining_items = total_items - (i + 1)
                
                # Estimate time remaining
                if i > 0:
                    avg_time_per_item = elapsed_time / (i + 1)
                    estimated_time_remaining = avg_time_per_item * remaining_items
                else:
                    estimated_time_remaining = 0
                
                # Call the callback with progress information
                callback({
                    "current": i + 1,
                    "total": total_items,
                    "percent": (i + 1) / total_items * 100,
                    "elapsed_time": elapsed_time,
                    "estimated_time_remaining": estimated_time_remaining
                })
            
            yield result
    
    @staticmethod
    def process_until_sufficient(items: List[Any], processor: Callable,
                                quality_checker: Callable,
                                min_results: int = 10,
                                max_results: Optional[int] = None,
                                callback: Optional[Callable] = None):
        """
        Process items until a sufficient number of good results are found.
        
        Args:
            items: List of items to process
            processor: Function to process each item
            quality_checker: Function to check if a result is good
            min_results: Minimum number of good results required
            max_results: Maximum number of results to return
            callback: Callback function for feedback
            
        Returns:
            List of good results
        """
        good_results = []
        total_processed = 0
        
        for item in items:
            # Process the item
            result = processor(item)
            total_processed += 1
            
            # Check if the result is good
            if quality_checker(result):
                good_results.append(result)
                
                # Provide feedback
                if callback:
                    callback({
                        "good_results": len(good_results),
                        "total_processed": total_processed,
                        "min_results": min_results,
                        "max_results": max_results
                    })
                
                # Check if we have enough good results
                if len(good_results) >= min_results and (max_results is None or len(good_results) >= max_results):
                    logger.info(f"Found {len(good_results)} good results after processing {total_processed} items")
                    break
        
        return good_results
    
    @staticmethod
    def process_with_timeout(items: List[Any], processor: Callable,
                            timeout_seconds: float,
                            callback: Optional[Callable] = None):
        """
        Process items until a timeout is reached.
        
        Args:
            items: List of items to process
            processor: Function to process each item
            timeout_seconds: Timeout in seconds
            callback: Callback function for feedback
            
        Yields:
            Processed items
        """
        start_time = time.time()
        total_items = len(items)
        
        for i, item in enumerate(items):
            # Check if timeout has been reached
            elapsed_time = time.time() - start_time
            if elapsed_time >= timeout_seconds:
                logger.info(f"Timeout reached after processing {i} items in {elapsed_time:.2f} seconds")
                break
            
            # Process the item
            result = processor(item)
            
            # Provide feedback
            if callback:
                callback({
                    "current": i + 1,
                    "total": total_items,
                    "percent": (i + 1) / total_items * 100,
                    "elapsed_time": elapsed_time,
                    "timeout": timeout_seconds
                })
            
            yield result
    
    @staticmethod
    def process_in_batches(items: List[Any], processor: Callable,
                          batch_size: int = 10,
                          callback: Optional[Callable] = None):
        """
        Process items in batches.
        
        Args:
            items: List of items to process
            processor: Function to process a batch of items
            batch_size: Size of each batch
            callback: Callback function for feedback
            
        Yields:
            Processed batches
        """
        total_items = len(items)
        num_batches = (total_items + batch_size - 1) // batch_size
        
        for i in range(0, total_items, batch_size):
            # Get the batch
            batch = items[i:i + batch_size]
            batch_num = i // batch_size + 1
            
            # Process the batch
            result = processor(batch)
            
            # Provide feedback
            if callback:
                callback({
                    "batch": batch_num,
                    "total_batches": num_batches,
                    "percent": batch_num / num_batches * 100,
                    "items_processed": min(i + batch_size, total_items),
                    "total_items": total_items
                })
            
            yield result
    
    @staticmethod
    def process_with_priority(items: List[Tuple[Any, float]], processor: Callable,
                             max_items: Optional[int] = None,
                             callback: Optional[Callable] = None):
        """
        Process items in order of priority.
        
        Args:
            items: List of (item, priority) tuples
            processor: Function to process each item
            max_items: Maximum number of items to process
            callback: Callback function for feedback
            
        Yields:
            Processed items
        """
        # Sort items by priority (descending)
        sorted_items = sorted(items, key=lambda x: x[1], reverse=True)
        
        # Limit the number of items if specified
        if max_items is not None:
            sorted_items = sorted_items[:max_items]
        
        total_items = len(sorted_items)
        
        for i, (item, priority) in enumerate(sorted_items):
            # Process the item
            result = processor(item)
            
            # Provide feedback
            if callback:
                callback({
                    "current": i + 1,
                    "total": total_items,
                    "percent": (i + 1) / total_items * 100,
                    "priority": priority
                })
            
            yield result

class ProgressTracker:
    """Track progress of long-running operations."""
    
    def __init__(self, total_items: int, description: str = "Processing"):
        """
        Initialize the progress tracker.
        
        Args:
            total_items: Total number of items to process
            description: Description of the operation
        """
        self.total_items = total_items
        self.description = description
        self.processed_items = 0
        self.start_time = time.time()
        self.last_update_time = self.start_time
        self.update_interval = 1.0  # Update every 1 second
    
    def update(self, items_processed: int = 1, force: bool = False):
        """
        Update the progress tracker.
        
        Args:
            items_processed: Number of items processed in this update
            force: Whether to force an update regardless of the update interval
        """
        self.processed_items += items_processed
        current_time = time.time()
        
        # Only update at intervals to avoid excessive logging
        if force or current_time - self.last_update_time >= self.update_interval:
            self.last_update_time = current_time
            self._log_progress()
    
    def _log_progress(self):
        """Log the current progress."""
        elapsed_time = time.time() - self.start_time
        percent_complete = self.processed_items / self.total_items * 100 if self.total_items > 0 else 0
        
        # Calculate items per second
        items_per_second = self.processed_items / elapsed_time if elapsed_time > 0 else 0
        
        # Estimate time remaining
        if items_per_second > 0:
            remaining_items = self.total_items - self.processed_items
            estimated_time_remaining = remaining_items / items_per_second
        else:
            estimated_time_remaining = 0
        
        logger.info(
            f"{self.description}: {self.processed_items}/{self.total_items} "
            f"({percent_complete:.1f}%) - "
            f"{items_per_second:.1f} items/sec - "
            f"Elapsed: {elapsed_time:.1f}s - "
            f"Remaining: {estimated_time_remaining:.1f}s"
        )
    
    def complete(self):
        """Mark the operation as complete."""
        self.processed_items = self.total_items
        self._log_progress()
        
        # Log completion
        elapsed_time = time.time() - self.start_time
        logger.info(f"{self.description} completed in {elapsed_time:.1f} seconds")

def progress_callback(progress_info: Dict[str, Any]):
    """
    Default callback function for progress updates.
    
    Args:
        progress_info: Dictionary of progress information
    """
    if "percent" in progress_info:
        logger.info(f"Progress: {progress_info['percent']:.1f}% complete")
    elif "good_results" in progress_info:
        logger.info(f"Found {progress_info['good_results']} good results out of {progress_info['total_processed']} processed")
    elif "batch" in progress_info:
        logger.info(f"Processed batch {progress_info['batch']}/{progress_info['total_batches']} ({progress_info['percent']:.1f}%)")
    else:
        logger.info(f"Progress update: {progress_info}")
