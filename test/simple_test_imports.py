#!/usr/bin/env python3
"""
Simple test script to verify imports.
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
        from src.utils import api_client
        logger.info("✓ Successfully imported api_client")
        
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
