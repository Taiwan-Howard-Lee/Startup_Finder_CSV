"""
Check the results of the raw crawler test.
"""

import json
import sys
import os
from pathlib import Path

def main():
    """Main function to check the results."""
    # Find the latest results file
    output_dir = Path("output/raw_results")
    result_files = list(output_dir.glob("raw_crawler_with_cleaned_content_*.json"))
    result_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    if not result_files:
        print("No result files found.")
        return
    
    latest_file = result_files[0]
    print(f"Checking results from: {latest_file}")
    
    # Load the results
    with open(latest_file, "r") as f:
        data = json.load(f)
    
    print(f"Found {len(data)} results.")
    
    # Print statistics for each result
    for i, sample in enumerate(data):
        print(f"\nSample {i+1}:")
        print(f"URL: {sample['url']}")
        print(f"Title: {sample['title']}")
        print(f"Raw content length: {sample['raw_content_length']}")
        print(f"Cleaned content length: {sample['cleaned_content_length']}")
        print(f"Content reduction: {sample['content_reduction_percentage']}%")
        
        # Print a preview of the cleaned content
        print("\nCleaned content preview:")
        cleaned_content = sample.get("cleaned_content", "")
        print(cleaned_content[:500] + "..." if len(cleaned_content) > 500 else cleaned_content)

if __name__ == "__main__":
    main()
