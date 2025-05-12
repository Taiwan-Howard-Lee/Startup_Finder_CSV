"""
Test script for consolidated reports.
"""

import os
import sys
import time
import logging

# Add the src directory to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.metrics_collector import MetricsCollector
from src.utils.report_generator import export_consolidated_reports

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_consolidated_reports():
    """Test the consolidated reports function."""
    # Create a metrics collector
    metrics_collector = MetricsCollector()

    # Add some test data
    metrics_collector.add_query("test query")
    metrics_collector.add_potential_startup_name("Test Startup 1", "https://example.com")
    metrics_collector.add_potential_startup_name("Test Startup 2", "https://example.com")
    metrics_collector.add_potential_startup_name("Test Startup 3", "https://example.com")
    metrics_collector.add_llm_extracted_name("Test Startup 1")
    metrics_collector.add_llm_extracted_name("Test Startup 2")
    metrics_collector.add_validated_name("Test Startup 1")
    metrics_collector.add_final_startup(
        "Test Startup 1", 
        {
            "Company Name": "Test Startup 1",
            "Website": "https://example.com",
            "Industry": "Technology",
            "Founded Year": "2020"
        }
    )

    # Export consolidated reports
    report_files = export_consolidated_reports(metrics_collector, "test_consolidated")

    # Check if the files were created
    for report_type, file_path in report_files.items():
        if os.path.exists(file_path):
            logger.info(f"Report file created: {file_path}")
        else:
            logger.error(f"Report file not created: {file_path}")

    return report_files

if __name__ == "__main__":
    test_consolidated_reports()
