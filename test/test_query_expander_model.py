#!/usr/bin/env python3
"""
Test script to verify that the query expander is using Gemini 2.5 Flash.
"""

import os
import sys
import logging

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_query_expander_model():
    """Test that the query expander is using Gemini 2.5 Flash."""
    try:
        # Import the necessary modules
        from src.utils.api_client import GeminiAPIClient
        from src.collector.query_expander import QueryExpander
        
        logger.info("Testing query expander model configuration...")
        
        # Create an API client
        api_client = GeminiAPIClient()
        
        # Check the model configuration
        logger.info(f"Flash model: {api_client.flash_model.model_name}")
        logger.info(f"Pro model (used for query expansion): {api_client.pro_model.model_name}")
        
        # Verify that the pro model is using Gemini 2.5 Flash
        if 'gemini-2.5-flash' in api_client.pro_model.model_name:
            logger.info("✓ Query expander is correctly configured to use Gemini 2.5 Flash")
            return True
        else:
            logger.error(f"✗ Query expander is using {api_client.pro_model.model_name} instead of gemini-2.5-flash")
            return False
            
    except Exception as e:
        logger.error(f"Error testing query expander model: {e}")
        return False

if __name__ == "__main__":
    success = test_query_expander_model()
    sys.exit(0 if success else 1)
