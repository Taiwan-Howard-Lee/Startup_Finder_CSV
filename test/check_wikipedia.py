"""
Test script to check Wikipedia content extraction.
"""

import requests
from bs4 import BeautifulSoup
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.text_cleaner import TextCleaner

def main():
    """Main function to test Wikipedia content extraction."""
    # Initialize text cleaner
    cleaner = TextCleaner()
    
    # Fetch Wikipedia page
    url = 'https://en.wikipedia.org/wiki/Diamond-like_carbon'
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'}
    
    response = requests.get(url, headers=headers)
    html_content = response.text
    
    # Parse with BeautifulSoup
    soup = BeautifulSoup(html_content, 'lxml')
    
    # Check if main content exists
    main_content = soup.find(id='mw-content-text')
    print(f"Main content found: {main_content is not None}")
    
    if main_content:
        # Get text from main content
        main_text = main_content.get_text(separator=' ', strip=True)
        print(f"Main content length: {len(main_text)}")
        print(f"Main content preview: {main_text[:500]}...")
        
        # Check content containers
        content_containers = soup.find_all(['main', 'article', 'section', 'div'], 
                                         class_=lambda c: c and any(x in c.lower() for x in ['content', 'main', 'article', 'post']))
        
        print(f"\nFound {len(content_containers)} content containers")
        if content_containers:
            largest = max(content_containers, key=lambda x: len(x.get_text()))
            print(f"Largest container class/id: {largest.get('class', 'No class')} / {largest.get('id', 'No id')}")
            print(f"Largest container text length: {len(largest.get_text())}")
        
        # Try our text cleaner
        cleaned_text = cleaner.extract_text_from_html(html_content)
        print(f"\nCleaned text length: {len(cleaned_text)}")
        print(f"Cleaned text preview: {cleaned_text[:500] if cleaned_text else 'No text extracted'}...")
        
        # Try fallback method
        fallback_text = cleaner.html2text(html_content)
        print(f"\nFallback text length: {len(fallback_text)}")
        print(f"Fallback text preview: {fallback_text[:500]}...")
        
        # Try direct BeautifulSoup extraction
        direct_text = soup.get_text(separator=' ', strip=True)
        print(f"\nDirect BeautifulSoup text length: {len(direct_text)}")
        print(f"Direct text preview: {direct_text[:500]}...")

if __name__ == "__main__":
    main()
