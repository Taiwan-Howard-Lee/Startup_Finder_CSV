"""
Text Chunker for Startup Intelligence Finder.

This module provides utilities for chunking text content into manageable pieces
for API processing, with a focus on preserving paragraph integrity.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple

# Set up logging
logger = logging.getLogger(__name__)

class TextChunker:
    """
    A utility class for chunking text content into manageable pieces for API processing.

    This class provides methods to chunk text based on paragraph boundaries,
    with configurable chunk size and overlap between chunks.
    """

    def __init__(self, chunk_size: int = 8000, overlap: int = 500):
        """
        Initialize the TextChunker.

        Args:
            chunk_size: Target size of each chunk in characters (default: 8000)
            overlap: Number of characters to overlap between chunks (default: 500)
        """
        self.chunk_size = chunk_size
        self.overlap = overlap

        # Validate parameters
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if overlap < 0:
            raise ValueError("overlap must be non-negative")
        if overlap >= chunk_size:
            raise ValueError("overlap must be less than chunk_size")

        logger.info(f"Initialized TextChunker with chunk_size={chunk_size}, overlap={overlap}")

    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into chunks of approximately chunk_size characters,
        with overlap between chunks, splitting at paragraph boundaries.

        Args:
            text: The text to chunk

        Returns:
            List of text chunks
        """
        if not text:
            logger.warning("Empty text provided to chunk_text")
            return []

        # Split text into paragraphs
        paragraphs = self._split_into_paragraphs(text)

        if not paragraphs:
            logger.warning("No paragraphs found in text")
            return []

        # Handle case where text is shorter than chunk_size
        if len(text) <= self.chunk_size:
            logger.info(f"Text length ({len(text)}) is less than chunk_size ({self.chunk_size}), returning as single chunk")
            return [text]

        # Create chunks based on paragraphs
        chunks = []
        current_chunk = []
        current_length = 0

        for paragraph in paragraphs:
            paragraph_length = len(paragraph)

            # Handle extremely long paragraphs
            if paragraph_length > self.chunk_size:
                # If we have content in the current chunk, add it as a chunk
                if current_chunk:
                    chunks.append("\n\n".join(current_chunk))
                    current_chunk = []
                    current_length = 0

                # Split the long paragraph and add as separate chunks
                long_paragraph_chunks = self._split_long_paragraph(paragraph)
                chunks.extend(long_paragraph_chunks)
                continue

            # If adding this paragraph would exceed chunk_size, start a new chunk
            if current_length + paragraph_length > self.chunk_size and current_chunk:
                chunks.append("\n\n".join(current_chunk))

                # Add overlap by including the last few paragraphs in the next chunk
                overlap_paragraphs, overlap_length = self._get_overlap_paragraphs(current_chunk)
                current_chunk = overlap_paragraphs
                current_length = overlap_length

            # Add the paragraph to the current chunk
            current_chunk.append(paragraph)
            current_length += paragraph_length + 4  # +4 for the "\n\n" separator

        # Add the last chunk if it's not empty
        if current_chunk:
            chunks.append("\n\n".join(current_chunk))

        logger.info(f"Split text into {len(chunks)} chunks")
        return chunks

    def chunk_batch(self, texts: List[str], source_metadata: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """
        Process a batch of texts, combining them and then chunking.

        Args:
            texts: List of cleaned text strings from different URLs
            source_metadata: Optional list of metadata dictionaries for each text

        Returns:
            List of dictionaries containing chunks and their metadata
        """
        if not texts:
            logger.warning("Empty list of texts provided to chunk_batch")
            return []

        # Filter out empty texts
        filtered_texts = []
        filtered_metadata = []

        for i, text in enumerate(texts):
            if text and text.strip():
                # Truncate very large texts to improve performance
                if len(text) > 100000:  # 100K character limit
                    logger.warning(f"Text {i} too large ({len(text)} chars). Truncating to 100K chars.")
                    text = text[:100000]

                filtered_texts.append(text)
                if source_metadata and i < len(source_metadata):
                    filtered_metadata.append(source_metadata[i])
                else:
                    filtered_metadata.append({})

        if not filtered_texts:
            logger.warning("No non-empty texts found")
            return []

        # Check if all texts fit within a single chunk
        total_length = sum(len(text) for text in filtered_texts)
        separators_length = (len(filtered_texts) - 1) * 6  # Length of "\n\n---\n\n"

        # If total content is very large, process each text separately
        if total_length > self.chunk_size * 5:  # If content is more than 5 chunks
            logger.info(f"Content too large ({total_length} chars), processing texts separately")
            return self._process_texts_separately(filtered_texts, filtered_metadata)

        if total_length + separators_length <= self.chunk_size:
            logger.info(f"All texts fit within a single chunk (total length: {total_length + separators_length})")

            # Combine all texts into a single chunk
            combined_text = ""
            for i, text in enumerate(filtered_texts):
                if i > 0:
                    # Add a more substantial separator with source information
                    separator = f"\n\n--- SOURCE: {filtered_metadata[i].get('title', 'Unknown')} | URL: {filtered_metadata[i].get('url', 'Unknown')} ---\n\n"
                    combined_text += separator
                combined_text += text

            return [{
                "chunk": combined_text,
                "chunk_index": 0,
                "total_chunks": 1,
                "sources": filtered_metadata
            }]

        # For multiple chunks, use a more efficient approach
        logger.info(f"Texts need multiple chunks (total length: {total_length + separators_length})")

        # Process each text individually to create paragraph-based chunks
        all_paragraphs = []
        paragraph_metadata = []

        for i, text in enumerate(filtered_texts):
            # Split text into paragraphs
            paragraphs = self._split_into_paragraphs(text)

            # Limit the number of paragraphs to improve performance
            if len(paragraphs) > 1000:
                logger.warning(f"Text {i} has too many paragraphs ({len(paragraphs)}). Limiting to 1000.")
                paragraphs = paragraphs[:1000]

            # Add source separator before each text except the first
            if all_paragraphs:
                # Add a more substantial separator with source information
                separator = f"--- SOURCE: {filtered_metadata[i].get('title', 'Unknown')} | URL: {filtered_metadata[i].get('url', 'Unknown')} ---"
                all_paragraphs.append(separator)
                paragraph_metadata.append(None)  # No metadata for separator

            # Add paragraphs and metadata
            for paragraph in paragraphs:
                all_paragraphs.append(paragraph)
                paragraph_metadata.append(filtered_metadata[i])

        # Now create chunks based on paragraphs - use a simpler approach for better performance
        chunks = []
        chunk_sources = []
        current_chunk = []
        current_sources = {}  # Use a dictionary with URL as key to avoid duplicate sources
        current_length = 0

        for i, paragraph in enumerate(all_paragraphs):
            paragraph_length = len(paragraph)

            # Skip extremely long paragraphs
            if paragraph_length > self.chunk_size:
                logger.warning(f"Paragraph {i} too long ({paragraph_length} chars). Splitting.")
                # Split the paragraph into smaller pieces
                for j in range(0, paragraph_length, self.chunk_size - 100):
                    sub_para = paragraph[j:j + self.chunk_size - 100]
                    chunks.append(sub_para)

                    # Add sources for this chunk
                    if paragraph_metadata[i]:
                        chunk_sources.append([paragraph_metadata[i]])
                    else:
                        chunk_sources.append([])
                continue

            # If adding this paragraph would exceed chunk_size, start a new chunk
            if current_length + paragraph_length > self.chunk_size and current_chunk:
                # Add the current chunk
                chunks.append("\n\n".join(current_chunk))
                chunk_sources.append(list(current_sources.values()))

                # Start a new chunk with minimal overlap
                current_chunk = []
                current_length = 0
                current_sources = {}

            # Add the paragraph to the current chunk
            current_chunk.append(paragraph)
            current_length += paragraph_length + 4  # +4 for the "\n\n" separator

            # Add the source metadata
            if paragraph_metadata[i]:
                metadata = paragraph_metadata[i]
                url = metadata.get('url', '')
                if url:
                    current_sources[url] = metadata

        # Add the last chunk if it's not empty
        if current_chunk:
            chunks.append("\n\n".join(current_chunk))
            chunk_sources.append(list(current_sources.values()))

        # Create chunk objects
        chunk_objects = []
        for i, (chunk, sources) in enumerate(zip(chunks, chunk_sources)):
            chunk_objects.append({
                "chunk": chunk,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "sources": sources
            })

        logger.info(f"Created {len(chunk_objects)} chunk objects from {len(filtered_texts)} texts")
        return chunk_objects

    def _process_texts_separately(self, texts: List[str], metadata: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process each text separately for very large content.

        Args:
            texts: List of text strings
            metadata: List of metadata dictionaries

        Returns:
            List of chunk objects
        """
        all_chunks = []

        for i, text in enumerate(texts):
            # Skip empty texts
            if not text:
                continue

            # Get metadata for this text
            text_metadata = metadata[i] if i < len(metadata) else {}

            # Split text into paragraphs
            paragraphs = self._split_into_paragraphs(text)

            # Limit the number of paragraphs to improve performance
            if len(paragraphs) > 500:
                logger.warning(f"Text {i} has too many paragraphs ({len(paragraphs)}). Limiting to 500.")
                paragraphs = paragraphs[:500]

            # Create chunks from paragraphs
            chunks = []
            current_chunk = []
            current_length = 0

            for paragraph in paragraphs:
                paragraph_length = len(paragraph)

                # Skip extremely long paragraphs
                if paragraph_length > self.chunk_size:
                    # If we have content in the current chunk, add it
                    if current_chunk:
                        chunks.append("\n\n".join(current_chunk))
                        current_chunk = []
                        current_length = 0

                    # Split the paragraph and add as separate chunks
                    for j in range(0, paragraph_length, self.chunk_size - 100):
                        chunks.append(paragraph[j:j + self.chunk_size - 100])

                    continue

                # If adding this paragraph would exceed chunk_size, start a new chunk
                if current_length + paragraph_length > self.chunk_size and current_chunk:
                    chunks.append("\n\n".join(current_chunk))
                    current_chunk = []
                    current_length = 0

                # Add the paragraph to the current chunk
                current_chunk.append(paragraph)
                current_length += paragraph_length + 4  # +4 for the "\n\n" separator

            # Add the last chunk if it's not empty
            if current_chunk:
                chunks.append("\n\n".join(current_chunk))

            # Create chunk objects for this text
            for j, chunk in enumerate(chunks):
                all_chunks.append({
                    "chunk": chunk,
                    "chunk_index": j,
                    "total_chunks": len(chunks),
                    "sources": [text_metadata]
                })

        logger.info(f"Created {len(all_chunks)} chunk objects by processing {len(texts)} texts separately")
        return all_chunks

    def _split_into_paragraphs(self, text: str) -> List[str]:
        """
        Split text into paragraphs.

        Args:
            text: The text to split

        Returns:
            List of paragraphs
        """
        # Split on double newlines
        paragraphs = re.split(r'\n\s*\n', text)

        # Filter out empty paragraphs and strip whitespace
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        return paragraphs

    def _split_long_paragraph(self, paragraph: str) -> List[str]:
        """
        Split a long paragraph into multiple chunks.

        Args:
            paragraph: The paragraph to split

        Returns:
            List of paragraph chunks
        """
        # Try to split at sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+', paragraph)

        chunks = []
        current_chunk = []
        current_length = 0

        for sentence in sentences:
            sentence_length = len(sentence)

            # If a single sentence is longer than chunk_size, split it by characters
            if sentence_length > self.chunk_size:
                # If we have content in the current chunk, add it as a chunk
                if current_chunk:
                    chunks.append(" ".join(current_chunk))

                # Split the sentence by characters
                for i in range(0, sentence_length, self.chunk_size):
                    chunks.append(sentence[i:i + self.chunk_size])

                current_chunk = []
                current_length = 0
                continue

            # If adding this sentence would exceed chunk_size, start a new chunk
            if current_length + sentence_length > self.chunk_size and current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = []
                current_length = 0

            # Add the sentence to the current chunk
            current_chunk.append(sentence)
            current_length += sentence_length + 1  # +1 for the space

        # Add the last chunk if it's not empty
        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks

    def _get_overlap_paragraphs(self, paragraphs: List[str]) -> Tuple[List[str], int]:
        """
        Get paragraphs to include in the overlap between chunks.

        Args:
            paragraphs: List of paragraphs in the current chunk

        Returns:
            Tuple of (overlap_paragraphs, overlap_length)
        """
        if not paragraphs:
            return [], 0

        # Start with the last paragraph
        overlap_paragraphs = []
        overlap_length = 0

        # Add paragraphs from the end until we reach the desired overlap
        for paragraph in reversed(paragraphs):
            paragraph_length = len(paragraph)

            # If adding this paragraph would exceed the overlap, stop
            if overlap_length + paragraph_length > self.overlap:
                # Only add the paragraph if we haven't added any paragraphs yet
                # or if adding it doesn't exceed twice the overlap
                if not overlap_paragraphs or overlap_length + paragraph_length <= 2 * self.overlap:
                    overlap_paragraphs.insert(0, paragraph)
                    overlap_length += paragraph_length + 4  # +4 for the "\n\n" separator
                break

            # Add the paragraph to the overlap
            overlap_paragraphs.insert(0, paragraph)
            overlap_length += paragraph_length + 4  # +4 for the "\n\n" separator

            # If we've reached the desired overlap, stop
            if overlap_length >= self.overlap:
                break

        return overlap_paragraphs, overlap_length
