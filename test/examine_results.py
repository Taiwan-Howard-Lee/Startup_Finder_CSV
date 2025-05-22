"""
Examine the results of the crawler, cleaner, and chunker test.
"""

import json
import sys
import os
from pathlib import Path

def examine_raw_results(file_path):
    """Examine the raw results."""
    print(f"Examining raw results from: {file_path}")
    
    with open(file_path, "r") as f:
        data = json.load(f)
    
    print(f"Number of results: {len(data)}")
    
    for i, result in enumerate(data):
        print(f"\nResult {i+1}:")
        print(f"URL: {result.get('url', 'No URL')}")
        print(f"Title: {result.get('title', 'No title')}")
        print(f"Raw content length: {result.get('raw_content_length', 0)}")
        print(f"Cleaned content length: {result.get('cleaned_content_length', 0)}")
        print(f"Content reduction: {result.get('content_reduction_percentage', 0)}%")
        
        # Print a preview of the cleaned content
        cleaned_content = result.get("cleaned_content", "")
        print("\nCleaned content preview:")
        print(cleaned_content[:500] + "..." if len(cleaned_content) > 500 else cleaned_content)

def examine_chunks(file_path):
    """Examine the chunks."""
    print(f"\nExamining chunks from: {file_path}")
    
    with open(file_path, "r") as f:
        data = json.load(f)
    
    print(f"Number of chunks: {len(data)}")
    
    for i, chunk in enumerate(data):
        print(f"\nChunk {i+1}:")
        print(f"Chunk index: {chunk.get('chunk_index', 0)}/{chunk.get('total_chunks', 0)}")
        print(f"Chunk size: {len(chunk.get('chunk', ''))}")
        
        # Print source information
        sources = chunk.get("sources", [])
        print(f"Number of sources: {len(sources)}")
        
        for j, source in enumerate(sources):
            print(f"  Source {j+1}: {source.get('title', 'No title')} ({source.get('url', 'No URL')})")
        
        # Print a preview of the chunk content
        chunk_content = chunk.get("chunk", "")
        print("\nChunk content preview:")
        print(chunk_content[:500] + "..." if len(chunk_content) > 500 else chunk_content)
        
        # Check for overlap markers
        overlap_marker = "--- OVERLAP MARKER"
        if overlap_marker in chunk_content:
            print("\nOverlap markers found:")
            start_pos = 0
            while True:
                pos = chunk_content.find(overlap_marker, start_pos)
                if pos == -1:
                    break
                
                marker_end = chunk_content.find("\n", pos)
                if marker_end == -1:
                    marker_end = pos + 50
                
                marker = chunk_content[pos:marker_end]
                print(f"  {marker} at position {pos}")
                
                # Show context around the marker
                context_start = max(0, pos - 50)
                context_end = min(len(chunk_content), pos + 50)
                context = chunk_content[context_start:context_end]
                print(f"  Context: ...{context}...")
                
                start_pos = pos + 1

def main():
    """Main function."""
    # Find the latest results
    raw_results_dir = Path("output/raw_results")
    chunks_dir = Path("output/chunks")
    
    raw_files = list(raw_results_dir.glob("crawler_cleaner_chunker_*.json"))
    chunk_files = list(chunks_dir.glob("chunks_*.json"))
    
    raw_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    chunk_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    if not raw_files:
        print("No raw results found.")
        return
    
    if not chunk_files:
        print("No chunks found.")
        return
    
    # Examine the latest results
    examine_raw_results(raw_files[0])
    examine_chunks(chunk_files[0])

if __name__ == "__main__":
    main()
