"""
Examine the chunks created by the ContentProcessor.
"""

import json
import sys
import os
from pathlib import Path

def examine_chunks(file_path):
    """Examine the chunks."""
    print(f"Examining chunks from: {file_path}")
    
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
    # Find the latest chunks
    chunks_dir = Path("output/chunks")
    
    chunk_files = list(chunks_dir.glob("content_processor_*.json"))
    chunk_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    if not chunk_files:
        print("No chunks found.")
        return
    
    # Examine the latest chunks
    examine_chunks(chunk_files[0])

if __name__ == "__main__":
    main()
