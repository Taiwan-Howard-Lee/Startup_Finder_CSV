"""
Test script for the TextChunker.

This script tests the functionality of the TextChunker class.
"""

import sys
import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.text_chunker import TextChunker
from src.utils.text_cleaner import TextCleaner

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_sample_data(file_path: str) -> List[Dict[str, Any]]:
    """
    Load sample data from a JSON file.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        List of dictionaries containing sample data
    """
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        return data
    except Exception as e:
        logger.error(f"Error loading sample data: {e}")
        return []

def test_chunking_with_sample_data():
    """Test the TextChunker with sample data from a previous crawler run."""
    # Find the latest raw crawler results
    output_dir = Path("output/raw_results")
    result_files = list(output_dir.glob("raw_crawler_with_cleaned_content_*.json"))
    result_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    if not result_files:
        logger.error("No raw crawler results found.")
        return
    
    latest_file = result_files[0]
    logger.info(f"Using sample data from: {latest_file}")
    
    # Load the sample data
    sample_data = load_sample_data(latest_file)
    if not sample_data:
        logger.error("No sample data loaded.")
        return
    
    # Extract cleaned text and metadata
    texts = []
    metadata = []
    for item in sample_data:
        cleaned_content = item.get("cleaned_content", "")
        if cleaned_content:
            texts.append(cleaned_content)
            metadata.append({
                "url": item.get("url", ""),
                "title": item.get("title", ""),
                "search_query": item.get("search_query", "")
            })
    
    logger.info(f"Loaded {len(texts)} text samples with a total of {sum(len(t) for t in texts)} characters")
    
    # Initialize the TextChunker
    chunker = TextChunker(chunk_size=50000, overlap=1000)
    
    # Test individual chunking
    logger.info("Testing individual chunking...")
    for i, text in enumerate(texts):
        chunks = chunker.chunk_text(text)
        logger.info(f"Text {i+1} ({len(text)} chars) -> {len(chunks)} chunks")
        
        # Log chunk sizes
        chunk_sizes = [len(chunk) for chunk in chunks]
        logger.info(f"Chunk sizes: {chunk_sizes}")
        
        # Verify that chunks can be reassembled (accounting for overlap)
        if chunks:
            reassembled = chunks[0]
            for j in range(1, len(chunks)):
                # Find where the overlap begins in the next chunk
                overlap_start = 0
                min_overlap_length = min(1000, len(chunks[j-1]))
                for k in range(min_overlap_length, 0, -1):
                    if chunks[j-1][-k:] in chunks[j]:
                        overlap_start = chunks[j].find(chunks[j-1][-k:])
                        break
                
                if overlap_start > 0:
                    reassembled += chunks[j][overlap_start + min_overlap_length:]
                else:
                    reassembled += chunks[j]
            
            logger.info(f"Original length: {len(text)}, Reassembled length: {len(reassembled)}")
            
            # Check if the reassembled text matches the original (allowing for some differences due to overlap)
            similarity = len(set(text) & set(reassembled)) / len(set(text) | set(reassembled))
            logger.info(f"Similarity between original and reassembled: {similarity:.2%}")
    
    # Test batch chunking
    logger.info("\nTesting batch chunking...")
    chunk_objects = chunker.chunk_batch(texts, metadata)
    logger.info(f"Batch chunking created {len(chunk_objects)} chunks")
    
    # Log chunk information
    for i, chunk_obj in enumerate(chunk_objects):
        chunk = chunk_obj["chunk"]
        sources = chunk_obj["sources"]
        logger.info(f"Chunk {i+1}: {len(chunk)} chars, {len(sources)} sources")
        
        # Log source information
        for j, source in enumerate(sources):
            logger.info(f"  Source {j+1}: {source.get('title', 'No title')} ({source.get('url', 'No URL')})")
    
    # Save the chunks to a file for inspection
    output_file = "output/chunks/text_chunks_test_output.json"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(chunk_objects, f, indent=2)
    
    logger.info(f"Saved chunk objects to {output_file}")

def test_with_synthetic_data():
    """Test the TextChunker with synthetic data."""
    logger.info("\nTesting with synthetic data...")
    
    # Create synthetic paragraphs
    paragraph_lengths = [100, 200, 500, 1000, 2000, 5000, 10000, 20000, 30000, 60000]
    paragraphs = []
    
    for length in paragraph_lengths:
        # Create a paragraph of the specified length
        paragraph = f"This is a synthetic paragraph of length {length}. "
        paragraph += "Lorem ipsum dolor sit amet. " * ((length - len(paragraph)) // 30 + 1)
        paragraph = paragraph[:length]
        paragraphs.append(paragraph)
    
    # Create synthetic texts
    texts = [
        # Short text
        "\n\n".join(paragraphs[:3]),
        
        # Medium text
        "\n\n".join(paragraphs[2:7]),
        
        # Long text
        "\n\n".join(paragraphs),
        
        # Text with a very long paragraph
        paragraphs[0] + "\n\n" + paragraphs[-1] + "\n\n" + paragraphs[1]
    ]
    
    # Initialize the TextChunker
    chunker = TextChunker(chunk_size=50000, overlap=1000)
    
    # Test chunking
    for i, text in enumerate(texts):
        logger.info(f"Synthetic text {i+1} ({len(text)} chars)")
        chunks = chunker.chunk_text(text)
        logger.info(f"  -> {len(chunks)} chunks")
        
        # Log chunk sizes
        chunk_sizes = [len(chunk) for chunk in chunks]
        logger.info(f"  Chunk sizes: {chunk_sizes}")

if __name__ == "__main__":
    # Create output directory if it doesn't exist
    os.makedirs("output/chunks", exist_ok=True)
    
    # Run the tests
    test_with_synthetic_data()
    test_chunking_with_sample_data()
