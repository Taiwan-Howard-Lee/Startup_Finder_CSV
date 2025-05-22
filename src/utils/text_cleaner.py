"""
Text Cleaner for Startup Intelligence Finder.

This module provides utilities for cleaning and normalizing text content
from various sources including HTML, PDF, and plain text.
"""

import re
import logging
from typing import Optional, Dict, Any, List
from bs4 import BeautifulSoup, Comment
import html2text

# Set up logging
logger = logging.getLogger(__name__)

class TextCleaner:
    """
    A utility class for cleaning and normalizing text content from various sources.

    This class provides methods to clean HTML, PDF, and plain text content
    to improve the quality of text extraction for LLM processing.
    """

    def __init__(self):
        """Initialize the TextCleaner."""
        # Configure HTML2Text converter
        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = False
        self.html_converter.ignore_images = True
        self.html_converter.ignore_tables = False
        self.html_converter.body_width = 0  # No wrapping

        # Common patterns to remove
        self.url_pattern = re.compile(r'https?://\S+|www\.\S+')
        self.email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        self.special_chars_pattern = re.compile(r'[^\w\s.,;:!?()[\]{}"\'-]')

        # Elements to remove from HTML
        self.unwanted_tags = [
            'script', 'style', 'noscript', 'iframe', 'head',
            'meta', 'link', 'svg', 'path', 'button', 'form',
            'input', 'select', 'option', 'nav', 'footer', 'header'
        ]

        # Classes and IDs that typically contain non-content elements
        self.unwanted_classes = [
            'cookie', 'banner', 'ad', 'advertisement', 'popup',
            'modal', 'menu', 'nav', 'sidebar', 'footer', 'header',
            'comment', 'social', 'share', 'related', 'widget'
        ]

    # Basic Text Cleaning Methods

    def clean_text(self, text: str) -> str:
        """
        Clean text by removing excessive whitespace and normalizing line breaks.

        Args:
            text: The text to clean.

        Returns:
            Cleaned text.
        """
        if not text:
            return ""

        # Replace multiple whitespace with a single space
        cleaned = re.sub(r'\s+', ' ', text)

        # Normalize line breaks
        cleaned = re.sub(r'\n\s*\n', '\n\n', cleaned)

        # Remove leading/trailing whitespace
        cleaned = cleaned.strip()

        return cleaned

    def normalize_whitespace(self, text: str) -> str:
        """
        Replace all whitespace with single spaces.

        Args:
            text: The text to normalize.

        Returns:
            Text with normalized whitespace.
        """
        if not text:
            return ""

        # Replace all whitespace characters with a single space
        return re.sub(r'\s+', ' ', text).strip()

    def remove_urls(self, text: str) -> str:
        """
        Remove URLs from text.

        Args:
            text: The text to process.

        Returns:
            Text with URLs removed.
        """
        if not text:
            return ""

        return self.url_pattern.sub('', text)

    def remove_email_addresses(self, text: str) -> str:
        """
        Remove email addresses from text.

        Args:
            text: The text to process.

        Returns:
            Text with email addresses removed.
        """
        if not text:
            return ""

        return self.email_pattern.sub('', text)

    def remove_special_characters(self, text: str) -> str:
        """
        Remove special characters from text.

        Args:
            text: The text to process.

        Returns:
            Text with special characters removed.
        """
        if not text:
            return ""

        return self.special_chars_pattern.sub('', text)

    # HTML Cleaning Methods

    def extract_text_from_html(self, html_content: str) -> str:
        """
        Extract and clean text from HTML content.

        Args:
            html_content: The HTML content to process.

        Returns:
            Cleaned text extracted from HTML.
        """
        if not html_content:
            return ""

        # Limit content size for better performance
        if len(html_content) > 200000:  # 200K character limit
            logger.warning(f"HTML content too large ({len(html_content)} chars). Truncating to 200K chars.")
            html_content = html_content[:200000]

        try:
            # Check for Hacker News content
            if "news.ycombinator.com" in html_content:
                logger.info("Detected Hacker News content, applying special cleaning")
                return self._extract_hacker_news_content(html_content)

            # Parse HTML
            soup = BeautifulSoup(html_content, 'lxml')

            # Create a copy of the soup for fallback
            soup_copy = BeautifulSoup(html_content, 'lxml')

            # Remove unwanted elements
            for tag in self.unwanted_tags:
                for element in soup.find_all(tag):
                    element.decompose()

            # Remove elements with unwanted classes or IDs
            for class_name in self.unwanted_classes:
                for element in soup.find_all(class_=re.compile(class_name, re.I)):
                    element.decompose()
                for element in soup.find_all(id=re.compile(class_name, re.I)):
                    element.decompose()

            # Remove comments
            for comment in soup.find_all(text=lambda text: isinstance(text, Comment)):
                comment.extract()

            # Extract main content
            main_content = self._extract_main_content(soup)

            # Clean the content
            cleaned_text = self.clean_text(main_content)

            # If we got an empty string, try with the original soup
            if not cleaned_text.strip():
                logger.warning("First extraction attempt returned empty text. Trying with original soup.")
                main_content = self._extract_main_content(soup_copy)
                cleaned_text = self.clean_text(main_content)

            # If still empty, try html2text
            if not cleaned_text.strip():
                logger.warning("Second extraction attempt returned empty text. Falling back to html2text.")
                cleaned_text = self.html2text(html_content)

            # If still empty, use direct BeautifulSoup extraction
            if not cleaned_text.strip():
                logger.warning("html2text returned empty text. Using direct BeautifulSoup extraction.")
                cleaned_text = soup_copy.get_text(separator=' ', strip=True)

            # Limit output size
            if len(cleaned_text) > 100000:  # 100K character limit for output
                logger.warning(f"Cleaned text too large ({len(cleaned_text)} chars). Truncating to 100K chars.")
                cleaned_text = cleaned_text[:100000]

            return cleaned_text

        except Exception as e:
            logger.error(f"Error extracting text from HTML: {e}")
            try:
                # Fall back to basic HTML to text conversion
                return self.html2text(html_content)
            except Exception as e2:
                logger.error(f"Error with html2text fallback: {e2}")
                # Last resort: direct BeautifulSoup extraction
                try:
                    soup = BeautifulSoup(html_content, 'lxml')
                    return soup.get_text(separator=' ', strip=True)[:100000]  # Limit to 100K chars
                except Exception as e3:
                    logger.error(f"All extraction methods failed: {e3}")
                    return ""

    def _extract_hacker_news_content(self, html_content: str) -> str:
        """
        Special extraction for Hacker News content.

        Args:
            html_content: The HTML content from Hacker News.

        Returns:
            Cleaned text focused on job postings or comments.
        """
        try:
            # Parse HTML
            soup = BeautifulSoup(html_content, 'lxml')

            # Extract the main content - comments are in <tr class="athing comtr"> elements
            comments = soup.find_all('tr', class_='athing comtr')

            # If this is a job posting thread, extract job postings
            if "who is hiring" in html_content.lower():
                # Extract text from comments, focusing on job postings
                job_posts = []

                for comment in comments[:50]:  # Limit to 50 comments for performance
                    # Get the comment text
                    comment_div = comment.find('div', class_='comment')
                    if not comment_div:
                        continue

                    comment_text = comment_div.get_text(separator='\n', strip=True)

                    # Skip short comments (likely not job postings)
                    if len(comment_text) < 100:
                        continue

                    # Look for common job posting indicators
                    indicators = ['hiring', 'remote', 'onsite', 'full-time', 'fulltime', 'position',
                                 'engineer', 'developer', 'www.', 'http', 'apply', 'email', 'contact']

                    if any(indicator in comment_text.lower() for indicator in indicators):
                        # Clean the comment text
                        cleaned_text = re.sub(r'\s+', ' ', comment_text)

                        # Add to job posts
                        job_posts.append(cleaned_text)

                # Combine job posts with separators
                combined_text = "\n\n---\n\n".join(job_posts)

                # Limit output size
                if len(combined_text) > 50000:  # 50K character limit for Hacker News content
                    logger.warning(f"Hacker News content too large ({len(combined_text)} chars). Truncating to 50K chars.")
                    combined_text = combined_text[:50000]

                return combined_text

            # For regular Hacker News threads, extract the main content
            else:
                # Get the title
                title = soup.find('title')
                title_text = title.get_text() if title else ""

                # Get the main content
                main_content = []

                # Add the title
                if title_text:
                    main_content.append(f"# {title_text}")

                # Add the top comments (limited to 20)
                for comment in comments[:20]:
                    comment_div = comment.find('div', class_='comment')
                    if comment_div:
                        comment_text = comment_div.get_text(separator='\n', strip=True)
                        if comment_text:
                            main_content.append(comment_text)

                # Combine content with separators
                combined_text = "\n\n---\n\n".join(main_content)

                # Limit output size
                if len(combined_text) > 50000:
                    combined_text = combined_text[:50000]

                return combined_text

        except Exception as e:
            logger.error(f"Error extracting Hacker News content: {e}")
            # Fall back to regular extraction
            soup = BeautifulSoup(html_content, 'lxml')
            return soup.get_text(separator='\n', strip=True)[:50000]

    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """
        Extract main content from HTML using BeautifulSoup.

        Args:
            soup: BeautifulSoup object of the HTML.

        Returns:
            Main content as text.
        """
        # First, try to find specific content IDs (common in popular websites)
        content_ids = ['mw-content-text', 'content', 'main-content', 'article-content', 'post-content']
        for content_id in content_ids:
            content_element = soup.find(id=content_id)
            if content_element and len(content_element.get_text(strip=True)) > 100:
                return content_element.get_text(separator=' ', strip=True)

        # Try to find main content containers by tag and class
        main_elements = soup.find_all(['main', 'article', 'section', 'div'],
                                     class_=lambda c: c and any(x in c.lower() for x in ['content', 'main', 'article', 'post']))

        if main_elements:
            # Use the largest content container
            main_element = max(main_elements, key=lambda x: len(x.get_text()))
            return main_element.get_text(separator=' ', strip=True)

        # If no main content container found, use the body
        body = soup.find('body')
        if body:
            return body.get_text(separator=' ', strip=True)

        # Last resort: use the entire document
        return soup.get_text(separator=' ', strip=True)

    def clean_element(self, element: BeautifulSoup) -> BeautifulSoup:
        """
        Clean HTML elements by removing unwanted tags and attributes.

        Args:
            element: BeautifulSoup element to clean.

        Returns:
            Cleaned BeautifulSoup element.
        """
        # Remove unwanted tags
        for tag in self.unwanted_tags:
            for unwanted in element.find_all(tag):
                unwanted.decompose()

        # Remove elements with unwanted classes or IDs
        for class_name in self.unwanted_classes:
            for unwanted in element.find_all(class_=re.compile(class_name, re.I)):
                unwanted.decompose()
            for unwanted in element.find_all(id=re.compile(class_name, re.I)):
                unwanted.decompose()

        # Remove comments
        for comment in element.find_all(text=lambda text: isinstance(text, Comment)):
            comment.extract()

        return element

    def html2text(self, html_content: str) -> str:
        """
        Convert HTML to Markdown-structured text.

        Args:
            html_content: The HTML content to convert.

        Returns:
            Markdown-structured text.
        """
        if not html_content:
            return ""

        try:
            return self.html_converter.handle(html_content)
        except Exception as e:
            logger.error(f"Error converting HTML to text: {e}")
            # Fall back to BeautifulSoup
            soup = BeautifulSoup(html_content, 'lxml')
            return soup.get_text(separator=' ', strip=True)

    # PDF Cleaning Methods

    def _clean_pdf_text(self, pdf_text: str) -> str:
        """
        Clean PDF text and convert to markdown.

        Args:
            pdf_text: The text extracted from a PDF.

        Returns:
            Cleaned text in markdown format.
        """
        if not pdf_text:
            return ""

        # Remove form feed characters
        cleaned = pdf_text.replace('\f', '\n\n')

        # Normalize whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned)

        # Fix line breaks
        cleaned = re.sub(r'(\w) (\w)', r'\1 \2', cleaned)

        # Add proper paragraph breaks
        cleaned = re.sub(r'\n\s*\n', '\n\n', cleaned)

        return cleaned.strip()

    def _clean_pdf_text_to_html(self, pdf_text: str) -> str:
        """
        Clean PDF text and convert to HTML.

        Args:
            pdf_text: The text extracted from a PDF.

        Returns:
            Cleaned text in HTML format.
        """
        if not pdf_text:
            return ""

        # Basic cleaning
        cleaned = self._clean_pdf_text(pdf_text)

        # Convert to HTML
        html = cleaned.replace('\n\n', '</p><p>')
        html = f"<p>{html}</p>"

        return html

    # Content Processing Methods

    def _process_text_content(self, content: str) -> str:
        """
        Process and clean plain text content.

        Args:
            content: The text content to process.

        Returns:
            Processed text content.
        """
        if not content:
            return ""

        # Apply all basic cleaning methods
        cleaned = self.clean_text(content)
        cleaned = self.remove_urls(cleaned)
        cleaned = self.remove_email_addresses(cleaned)

        return cleaned

    def _process_html_content(self, content: str) -> str:
        """
        Process HTML content with appropriate handlers.

        Args:
            content: The HTML content to process.

        Returns:
            Processed text content.
        """
        if not content:
            return ""

        # Extract text from HTML
        text = self.extract_text_from_html(content)

        # Apply additional cleaning
        cleaned = self._process_text_content(text)

        return cleaned

    def _process_pdf_content(self, content: str) -> str:
        """
        Process PDF content with appropriate handlers.

        Args:
            content: The PDF content to process.

        Returns:
            Processed text content.
        """
        if not content:
            return ""

        # Clean PDF text
        cleaned = self._clean_pdf_text(content)

        # Apply additional cleaning
        cleaned = self._process_text_content(cleaned)

        return cleaned

    def _process_image_content(self, content: str) -> str:
        """
        Process image content with appropriate handlers.

        Args:
            content: The image content description to process.

        Returns:
            Processed text content.
        """
        if not content:
            return ""

        # For image content, we just clean the text description
        cleaned = self._process_text_content(content)

        return cleaned

    def process_content(self, content: str, content_type: str = "text") -> str:
        """
        Process content based on its type.

        Args:
            content: The content to process.
            content_type: The type of content ('html', 'pdf', 'text', 'image').

        Returns:
            Processed content.
        """
        if not content:
            return ""

        content_type = content_type.lower()

        if content_type == "html":
            return self._process_html_content(content)
        elif content_type == "pdf":
            return self._process_pdf_content(content)
        elif content_type == "image":
            return self._process_image_content(content)
        else:  # Default to text
            return self._process_text_content(content)
