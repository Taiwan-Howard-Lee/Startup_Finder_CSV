"""
Check the overlap between chunks.
"""

import json
import sys
import os

def main():
    """Main function to check the overlap between chunks."""
    # Load the chunks
    with open('output/chunks/text_chunks_test_output.json', 'r') as f:
        data = json.load(f)
    
    print(f"Number of chunks: {len(data)}")
    
    if len(data) < 2:
        print("Not enough chunks to check overlap.")
        return
    
    # Get the last 1000 characters of the first chunk
    last_1000_first_chunk = data[0]['chunk'][-1000:]
    
    # Get the first 1000 characters of the second chunk
    first_1000_second_chunk = data[1]['chunk'][:1000]
    
    print("Last 100 chars of first chunk:")
    print(data[0]['chunk'][-100:])
    
    print("\nFirst 100 chars of second chunk:")
    print(data[1]['chunk'][:100])
    
    print("\nChecking for overlap...")
    
    # Check for overlap
    overlap_found = False
    for i in range(1, min(1000, len(last_1000_first_chunk), len(first_1000_second_chunk))):
        if last_1000_first_chunk[-i:] in first_1000_second_chunk:
            print(f"Found overlap of {i} characters")
            print(f"Overlapping text: {last_1000_first_chunk[-i:]}")
            overlap_found = True
            break
    
    if not overlap_found:
        print("No overlap found")
        
        # Check if there's a separator between chunks
        if "---" in first_1000_second_chunk:
            print("Found separator '---' in second chunk")
        
        # Check the sources of each chunk
        print("\nSources in first chunk:")
        for source in data[0]['sources']:
            print(f"  {source.get('title', 'No title')} ({source.get('url', 'No URL')})")
        
        print("\nSources in second chunk:")
        for source in data[1]['sources']:
            print(f"  {source.get('title', 'No title')} ({source.get('url', 'No URL')})")

if __name__ == "__main__":
    main()
