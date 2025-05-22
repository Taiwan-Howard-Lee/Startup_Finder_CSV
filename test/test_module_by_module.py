#!/usr/bin/env python3
"""
Test importing modules one by one.
"""

import os
import sys
import logging
import traceback

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_module(module_path):
    """Test importing a specific module."""
    try:
        logger.info(f"Testing import of {module_path}...")
        __import__(module_path)
        logger.info(f"✓ Successfully imported {module_path}")
        return True
    except Exception as e:
        logger.error(f"Error importing {module_path}: {e}")
        logger.error(traceback.format_exc())
        return False

def main():
    """Test importing various modules from the project."""
    # List of modules to test
    modules = [
        "src",
        "src.collector",
        "src.processor",
        "src.utils",
        "src.utils.api_client",
        "src.utils.api_key_manager",
        "src.utils.api_optimizer",
        "src.utils.batch_processor",
        "src.utils.content_processor",
        "src.utils.csv_appender",
        "src.utils.data_cleaner",
        "src.utils.database_manager",
        "src.utils.enhanced_google_search_client",
        "src.utils.google_search_client",
        "src.utils.logging_config",
        "src.utils.metrics_collector",
        "src.utils.optimization_utils",
        "src.utils.process_monitor",
        "src.utils.progressive_loader",
        "src.utils.query_optimizer",
        "src.utils.report_generator",
        "src.utils.smart_content_processor",
        "src.utils.startup_name_cleaner",
        "src.utils.text_chunker",
        "src.utils.text_cleaner",
        "src.utils.append_intermediate_results",
        "src.utils.deduplicate_and_overwrite",
        "src.utils.deduplicate_startups",
        "src.utils.run_with_monitoring",
        "src.modify_startup_finder"
    ]
    
    # Test each module
    results = {}
    for module in modules:
        results[module] = test_module(module)
    
    # Print summary
    print("\n=== IMPORT TEST SUMMARY ===")
    for module, success in results.items():
        status = "✓" if success else "✗"
        print(f"{status} {module}")
    
    # Return success if all modules imported successfully
    return all(results.values())

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
