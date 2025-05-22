"""
Content Processor for Startup Intelligence Finder.

This module provides utilities for processing text content from various sources,
including cleaning, chunking, and preparing for LLM processing.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from src.utils.text_cleaner import TextCleaner
from src.utils.text_chunker import TextChunker

# Set up logging
logger = logging.getLogger(__name__)

class ContentProcessor:
    """
    A utility class for processing content from various sources.

    This class combines text cleaning and chunking to prepare content for LLM processing.
    """

    def __init__(self, chunk_size: int = 50000, overlap: int = 1000):
        """
        Initialize the ContentProcessor.

        Args:
            chunk_size: Target size of each chunk in characters (default: 50000)
            overlap: Number of characters to overlap between chunks (default: 1000)
        """
        self.text_cleaner = TextCleaner()
        self.text_chunker = TextChunker(chunk_size=chunk_size, overlap=overlap)
        logger.info(f"Initialized ContentProcessor with chunk_size={chunk_size}, overlap={overlap}")

    def process_raw_content(self, raw_content: str, content_type: str = "html") -> str:
        """
        Process raw content based on its type.

        Args:
            raw_content: Raw content to process
            content_type: Type of content ('html', 'pdf', 'text')

        Returns:
            Cleaned text content
        """
        if not raw_content:
            logger.warning("Empty content provided to process_raw_content")
            return ""

        # Clean the content based on its type
        if content_type.lower() == "html":
            cleaned_content = self.text_cleaner.extract_text_from_html(raw_content)
        elif content_type.lower() == "pdf":
            cleaned_content = self.text_cleaner.extract_text_from_pdf(raw_content)
        else:
            # Assume plain text
            cleaned_content = self.text_cleaner.clean_text(raw_content)

        return cleaned_content

    def process_batch(self, raw_items: List[Dict[str, Any]], content_key: str = "raw_html",
                     content_type: str = "html") -> List[Dict[str, Any]]:
        """
        Process a batch of raw content items.

        Args:
            raw_items: List of dictionaries containing raw content
            content_key: Key in the dictionaries that contains the raw content
            content_type: Type of content ('html', 'pdf', 'text')

        Returns:
            List of dictionaries with cleaned content added
        """
        processed_items = []

        for item in raw_items:
            raw_content = item.get(content_key, "")
            if not raw_content:
                logger.warning(f"Empty content for item: {item.get('url', 'unknown')}")
                continue

            # Clean the content
            cleaned_content = self.process_raw_content(raw_content, content_type)

            # Add the cleaned content to the item
            processed_item = item.copy()
            processed_item["cleaned_content"] = cleaned_content
            processed_item["cleaned_content_length"] = len(cleaned_content)

            # Calculate content reduction percentage
            raw_length = len(raw_content)
            if raw_length > 0:
                reduction_percentage = round((raw_length - len(cleaned_content)) / raw_length * 100, 2)
                processed_item["content_reduction_percentage"] = reduction_percentage

            processed_items.append(processed_item)

        logger.info(f"Processed {len(processed_items)} items")
        return processed_items

    def chunk_processed_content(self, processed_items: List[Dict[str, Any]],
                               content_key: str = "cleaned_content") -> List[Dict[str, Any]]:
        """
        Chunk processed content for LLM processing.

        Args:
            processed_items: List of dictionaries containing processed content
            content_key: Key in the dictionaries that contains the processed content

        Returns:
            List of chunk objects
        """
        # Extract content and metadata
        texts = []
        metadata = []

        for item in processed_items:
            content = item.get(content_key, "")
            if not content:
                logger.warning(f"Empty content for item: {item.get('url', 'unknown')}")
                continue

            # Skip or truncate very large content
            if len(content) > 200000:  # 200K character limit
                logger.warning(f"Content too large ({len(content)} chars) for item: {item.get('url', 'unknown')}. Truncating to 200K chars.")
                content = content[:200000]

            texts.append(content)
            metadata.append({
                "url": item.get("url", ""),
                "title": item.get("title", ""),
                "search_query": item.get("search_query", "")
            })

        # Chunk the content
        chunk_objects = self.text_chunker.chunk_batch(texts, metadata)
        logger.info(f"Created {len(chunk_objects)} chunks from {len(texts)} texts")

        return chunk_objects

    def chunk_batch(self, texts: List[str], metadata: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Delegate to text_chunker.chunk_batch for compatibility.

        This method is added to fix the 'ContentProcessor' object has no attribute 'chunk_batch' error.

        Args:
            texts: List of text strings to chunk
            metadata: Optional metadata for each text

        Returns:
            List of chunk objects
        """
        logger.info(f"ContentProcessor.chunk_batch called with {len(texts)} texts")

        # Process texts to ensure they're not too large
        processed_texts = []
        processed_metadata = []

        for i, text in enumerate(texts):
            # Skip empty texts
            if not text:
                continue

            # Truncate very large texts
            if len(text) > 200000:  # 200K character limit
                logger.warning(f"Text {i} too large ({len(text)} chars). Truncating to 200K chars.")
                text = text[:200000]

            processed_texts.append(text)
            if metadata and i < len(metadata):
                processed_metadata.append(metadata[i])
            else:
                processed_metadata.append({})

        # Delegate to the text_chunker
        return self.text_chunker.chunk_batch(processed_texts, processed_metadata)

    def save_chunks(self, chunks: List[Dict[str, Any]], output_file: str) -> bool:
        """
        Save chunks to a file.

        Args:
            chunks: List of chunk objects
            output_file: Path to the output file

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create directory if it doesn't exist
            output_dir = os.path.dirname(output_file)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)

            # Save the chunks
            with open(output_file, 'w') as f:
                json.dump(chunks, f, indent=2)

            logger.info(f"Saved {len(chunks)} chunks to {output_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving chunks: {e}")
            return False

    def process_and_chunk(self, raw_items: List[Dict[str, Any]], content_key: str = "raw_html",
                         content_type: str = "html", output_file: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Process and chunk raw content in one step.

        Args:
            raw_items: List of dictionaries containing raw content
            content_key: Key in the dictionaries that contains the raw content
            content_type: Type of content ('html', 'pdf', 'text')
            output_file: Optional path to save the chunks

        Returns:
            List of chunk objects
        """
        # Process the raw content
        processed_items = self.process_batch(raw_items, content_key, content_type)

        # Chunk the processed content
        chunks = self.chunk_processed_content(processed_items)

        # Save the chunks if an output file is provided
        if output_file:
            self.save_chunks(chunks, output_file)

        return chunks
