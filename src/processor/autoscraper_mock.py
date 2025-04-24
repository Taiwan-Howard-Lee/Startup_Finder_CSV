"""
Mock implementation of AutoScraperDataSource for testing.
"""

import logging
from typing import Dict, Any, Optional

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AutoScraperDataSource:
    """
    Mock implementation of AutoScraperDataSource for testing.
    """

    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize the AutoScraper data source.

        Args:
            model_path: Path to a saved model file. If provided, will load the model.
        """
        self.is_trained = False
        if model_path:
            self.load_model(model_path)
            self.is_trained = True
        
        logger.info("Initialized mock AutoScraperDataSource")

    def train_scraper(self, url: str, data: Dict[str, Any]) -> bool:
        """
        Train the AutoScraper on a sample URL.

        Args:
            url: URL to train on.
            data: Dictionary of data to extract, with keys as field names and values as lists of examples.

        Returns:
            True if training was successful, False otherwise.
        """
        logger.info(f"Mock training AutoScraper on {url}")
        self.is_trained = True
        return True

    def extract_startup_data(self, url: str) -> Dict[str, Any]:
        """
        Extract startup data from a URL.

        Args:
            url: URL to extract data from.

        Returns:
            Dictionary of extracted data.
        """
        logger.info(f"Mock extracting data from {url}")
        
        # Return mock data
        return {
            "Company Name": "MockStartup",
            "Website": url,
            "Description": "This is a mock startup for testing purposes.",
            "Founded Year": "2023",
            "Location": "Test City, Test Country",
            "Team": "Mock Founder, Mock CTO",
            "Contact": "info@mockstartup.com"
        }

    def save_model(self, model_path: str) -> bool:
        """
        Save the trained model to a file.

        Args:
            model_path: Path to save the model to.

        Returns:
            True if saving was successful, False otherwise.
        """
        logger.info(f"Mock saving model to {model_path}")
        
        # Create an empty file to simulate saving
        with open(model_path, "w") as f:
            f.write("Mock AutoScraper model")
        
        return True

    def load_model(self, model_path: str) -> bool:
        """
        Load a trained model from a file.

        Args:
            model_path: Path to load the model from.

        Returns:
            True if loading was successful, False otherwise.
        """
        logger.info(f"Mock loading model from {model_path}")
        self.is_trained = True
        return True
