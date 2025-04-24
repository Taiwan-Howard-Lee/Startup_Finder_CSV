"""
Test script for AutoScraper implementation in the Startup Intelligence Finder.
"""

import os
import sys
import unittest

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import setup_env

from src.processor.autoscraper_mock import AutoScraperDataSource


class TestAutoScraper(unittest.TestCase):
    """Tests for the AutoScraperDataSource class."""

    def setUp(self):
        """Set up test fixtures."""
        # Ensure environment is set up
        setup_env.setup_environment(test_apis=False)

        # Create AutoScraperDataSource
        self.auto_scraper = AutoScraperDataSource()

        # Sample data for training
        # Using GitHub as it has a more stable structure
        self.sample_url = "https://github.com/alirezamika/autoscraper"
        self.sample_data = {
            "Project Name": ["autoscraper"],
            "Description": ["A Smart, Automatic, Fast and Lightweight Web Scraper for Python"],
            "Stars": ["6.7k"],
            "Language": ["Python"]
        }

    def test_train_scraper(self):
        """Test training the AutoScraper."""
        # Train the scraper
        success = self.auto_scraper.train_scraper(self.sample_url, self.sample_data)

        # Check if training was successful
        self.assertTrue(success)
        self.assertTrue(self.auto_scraper.is_trained)

        # Print training results
        print("\nAutoScraper training successful")

    def test_extract_data(self):
        """Test extracting data with AutoScraper."""
        # Skip if not trained
        if not self.auto_scraper.is_trained:
            self.skipTest("AutoScraper not trained")

        # Extract data from the same URL
        data = self.auto_scraper.extract_startup_data(self.sample_url)

        # Check if data was extracted
        self.assertIsNotNone(data)
        self.assertIn("Company Name", data)
        self.assertIn("Website", data)

        # Print extracted data
        print("\nExtracted data:")
        for key, value in data.items():
            print(f"{key}: {value}")

    def test_save_and_load_model(self):
        """Test saving and loading the AutoScraper model."""
        # Skip if not trained
        if not self.auto_scraper.is_trained:
            self.skipTest("AutoScraper not trained")

        # Save the model
        model_path = "autoscraper_model"
        success = self.auto_scraper.save_model(model_path)

        # Check if saving was successful
        self.assertTrue(success)
        self.assertTrue(os.path.exists(model_path))

        # Create a new AutoScraperDataSource and load the model
        new_scraper = AutoScraperDataSource(model_path=model_path)

        # Check if loading was successful
        self.assertTrue(new_scraper.is_trained)

        # Clean up
        if os.path.exists(model_path):
            os.remove(model_path)

        # Print results
        print("\nSaved and loaded AutoScraper model successfully")


if __name__ == "__main__":
    unittest.main()
