#!/usr/bin/env python3
"""
Test imports for the Startup Finder project.
"""

import os
import sys
import logging

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_imports():
    """Test importing various modules from the project."""
    try:
        # Test importing from src
        logger.info("Testing import from src...")
        import src
        logger.info("✓ Successfully imported src")
        
        # Test importing from src.utils
        logger.info("Testing import from src.utils...")
        from src import utils
        logger.info("✓ Successfully imported src.utils")
        
        # Test importing specific utility modules
        logger.info("Testing import of specific utility modules...")
        from src.utils import append_intermediate_results
        from src.utils import deduplicate_and_overwrite
        from src.utils import deduplicate_startups
        from src.utils import run_with_monitoring
        logger.info("✓ Successfully imported utility modules")
        
        # Test importing from src.processor
        logger.info("Testing import from src.processor...")
        from src import processor
        logger.info("✓ Successfully imported src.processor")
        
        # Test importing from src.collector
        logger.info("Testing import from src.collector...")
        from src import collector
        logger.info("✓ Successfully imported src.collector")
        
        # Test importing modify_startup_finder
        logger.info("Testing import of modify_startup_finder...")
        from src import modify_startup_finder
        logger.info("✓ Successfully imported modify_startup_finder")
        
        logger.info("All imports successful!")
        return True
    
    except ImportError as e:
        logger.error(f"Import error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
