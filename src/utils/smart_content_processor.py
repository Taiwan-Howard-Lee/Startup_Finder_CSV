"""
Smart content processing utilities for the Startup Finder.

This module provides utilities for smarter content processing,
including content relevance filtering, NLP-based entity extraction,
and site-specific content extraction.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Set
from urllib.parse import urlparse
from bs4 import BeautifulSoup

# Set up logging
logger = logging.getLogger(__name__)

class ContentRelevanceFilter:
    """Filter content based on relevance to a query."""
    
    @staticmethod
    def is_relevant_content(content: str, query: str, threshold: float = 0.1) -> bool:
        """
        Check if content is relevant to a query.
        
        Args:
            content: Content to check
            query: Query to check against
            threshold: Minimum relevance threshold
            
        Returns:
            True if content is relevant, False otherwise
        """
        if not content or not query:
            return False
        
        # Convert to lowercase for case-insensitive matching
        content_lower = content.lower()
        query_lower = query.lower()
        
        # Extract query terms (excluding common words)
        query_terms = [term for term in query_lower.split() if len(term) > 3]
        
        # Count how many query terms appear in the content
        matches = sum(1 for term in query_terms if term in content_lower)
        
        # Calculate relevance score
        if not query_terms:
            return False
            
        relevance_score = matches / len(query_terms)
        
        return relevance_score >= threshold
    
    @staticmethod
    def extract_relevant_paragraphs(content: str, query: str, max_paragraphs: int = 10) -> List[str]:
        """
        Extract paragraphs from content that are relevant to a query.
        
        Args:
            content: Content to extract paragraphs from
            query: Query to check against
            max_paragraphs: Maximum number of paragraphs to extract
            
        Returns:
            List of relevant paragraphs
        """
        if not content or not query:
            return []
        
        # Split content into paragraphs
        paragraphs = re.split(r'\n\s*\n', content)
        
        # Filter out empty paragraphs
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        # Score paragraphs by relevance
        scored_paragraphs = []
        query_terms = [term.lower() for term in query.split() if len(term) > 3]
        
        for paragraph in paragraphs:
            paragraph_lower = paragraph.lower()
            
            # Count matches
            matches = sum(1 for term in query_terms if term in paragraph_lower)
            
            # Calculate score (matches per paragraph length)
            score = matches / (len(paragraph) / 100) if paragraph else 0
            
            scored_paragraphs.append((paragraph, score))
        
        # Sort by score (descending)
        scored_paragraphs.sort(key=lambda x: x[1], reverse=True)
        
        # Return top paragraphs
        return [p for p, _ in scored_paragraphs[:max_paragraphs]]

class EntityExtractor:
    """Extract entities from text using NLP."""
    
    def __init__(self):
        """Initialize the entity extractor."""
        self.nlp = None
    
    def _load_spacy(self):
        """Load spaCy model if not already loaded."""
        if self.nlp is None:
            try:
                import spacy
                try:
                    # Try to load the model
                    self.nlp = spacy.load("en_core_web_sm")
                except OSError:
                    # If model not found, download it
                    import subprocess
                    logger.info("Downloading spaCy model...")
                    subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"], check=True)
                    self.nlp = spacy.load("en_core_web_sm")
            except ImportError:
                logger.warning("spaCy not installed. Using regex-based entity extraction instead.")
                return False
        return True
    
    def extract_organizations(self, text: str) -> List[str]:
        """
        Extract organization names from text using spaCy.
        
        Args:
            text: Text to extract organizations from
            
        Returns:
            List of organization names
        """
        # Fall back to regex-based extraction if spaCy is not available
        if not self._load_spacy():
            return self._extract_organizations_regex(text)
        
        # Use spaCy for extraction
        doc = self.nlp(text[:100000])  # Limit text size to avoid memory issues
        organizations = [ent.text for ent in doc.ents if ent.label_ == "ORG"]
        
        # Filter out common non-startup organizations
        filtered_orgs = []
        common_orgs = {"Facebook", "Google", "Microsoft", "Apple", "Amazon", "Twitter", "LinkedIn"}
        
        for org in organizations:
            if org not in common_orgs and len(org) > 2:
                filtered_orgs.append(org)
        
        return filtered_orgs
    
    def _extract_organizations_regex(self, text: str) -> List[str]:
        """
        Extract organization names using regex patterns.
        
        Args:
            text: Text to extract organizations from
            
        Returns:
            List of organization names
        """
        # Simple regex patterns for organization names
        patterns = [
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:Inc|LLC|Ltd|Corp|Corporation|Company)',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+Technologies',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+Solutions',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+Systems',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+Software'
        ]
        
        organizations = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            organizations.extend(matches)
        
        return list(set(organizations))

class SiteSpecificExtractor:
    """Extract content from specific websites."""
    
    @staticmethod
    def extract_content(url: str, html: str) -> str:
        """
        Extract content from a website using site-specific extractors.
        
        Args:
            url: URL of the website
            html: HTML content
            
        Returns:
            Extracted content
        """
        domain = urlparse(url).netloc.lower()
        
        # Use site-specific extractors
        if "linkedin.com" in domain:
            return SiteSpecificExtractor.extract_linkedin_content(html)
        elif "crunchbase.com" in domain:
            return SiteSpecificExtractor.extract_crunchbase_content(html)
        elif "techcrunch.com" in domain:
            return SiteSpecificExtractor.extract_techcrunch_content(html)
        elif "news.ycombinator.com" in domain:
            return SiteSpecificExtractor.extract_hacker_news_content(html)
        else:
            return SiteSpecificExtractor.extract_generic_content(html)
    
    @staticmethod
    def extract_linkedin_content(html: str) -> str:
        """
        Extract content from LinkedIn.
        
        Args:
            html: HTML content
            
        Returns:
            Extracted content
        """
        soup = BeautifulSoup(html, 'lxml')
        
        # Extract company name
        company_name = ""
        name_element = soup.find('h1', class_='org-top-card-summary__title')
        if name_element:
            company_name = name_element.text.strip()
        
        # Extract description
        description = ""
        desc_element = soup.find('p', class_='org-about-us-organization-description__text')
        if desc_element:
            description = desc_element.text.strip()
        
        # Extract other details
        details = []
        detail_elements = soup.find_all('dd', class_='org-about-company-module__company-size-definition-text')
        for element in detail_elements:
            details.append(element.text.strip())
        
        # Combine all extracted content
        content = []
        if company_name:
            content.append(f"Company Name: {company_name}")
        if description:
            content.append(f"Description: {description}")
        if details:
            content.append(f"Details: {', '.join(details)}")
        
        return "\n\n".join(content)
    
    @staticmethod
    def extract_crunchbase_content(html: str) -> str:
        """
        Extract content from Crunchbase.
        
        Args:
            html: HTML content
            
        Returns:
            Extracted content
        """
        soup = BeautifulSoup(html, 'lxml')
        
        # Extract company name
        company_name = ""
        name_element = soup.find('h1', class_='profile-name')
        if name_element:
            company_name = name_element.text.strip()
        
        # Extract description
        description = ""
        desc_element = soup.find('span', class_='description')
        if desc_element:
            description = desc_element.text.strip()
        
        # Extract funding information
        funding = ""
        funding_element = soup.find('span', class_='funding-total')
        if funding_element:
            funding = funding_element.text.strip()
        
        # Combine all extracted content
        content = []
        if company_name:
            content.append(f"Company Name: {company_name}")
        if description:
            content.append(f"Description: {description}")
        if funding:
            content.append(f"Funding: {funding}")
        
        return "\n\n".join(content)
    
    @staticmethod
    def extract_techcrunch_content(html: str) -> str:
        """
        Extract content from TechCrunch.
        
        Args:
            html: HTML content
            
        Returns:
            Extracted content
        """
        soup = BeautifulSoup(html, 'lxml')
        
        # Extract article title
        title = ""
        title_element = soup.find('h1', class_='article__title')
        if title_element:
            title = title_element.text.strip()
        
        # Extract article content
        content_text = ""
        content_element = soup.find('div', class_='article-content')
        if content_element:
            paragraphs = content_element.find_all('p')
            content_text = "\n\n".join(p.text.strip() for p in paragraphs)
        
        # Combine all extracted content
        content = []
        if title:
            content.append(f"Title: {title}")
        if content_text:
            content.append(f"Content: {content_text}")
        
        return "\n\n".join(content)
    
    @staticmethod
    def extract_hacker_news_content(html: str) -> str:
        """
        Extract content from Hacker News.
        
        Args:
            html: HTML content
            
        Returns:
            Extracted content
        """
        soup = BeautifulSoup(html, 'lxml')
        
        # Extract the title
        title = ""
        title_element = soup.find('title')
        if title_element:
            title = title_element.text.strip()
        
        # Extract comments
        comments = []
        comment_elements = soup.find_all('div', class_='comment')
        for element in comment_elements[:20]:  # Limit to 20 comments
            comment_text = element.text.strip()
            if comment_text:
                comments.append(comment_text)
        
        # Combine all extracted content
        content = []
        if title:
            content.append(f"Title: {title}")
        if comments:
            content.append("Comments:\n" + "\n\n".join(comments))
        
        return "\n\n".join(content)
    
    @staticmethod
    def extract_generic_content(html: str) -> str:
        """
        Extract content from a generic website.
        
        Args:
            html: HTML content
            
        Returns:
            Extracted content
        """
        try:
            # Try to use readability-lxml if available
            from readability import Document
            doc = Document(html)
            return doc.summary()
        except ImportError:
            # Fall back to BeautifulSoup
            soup = BeautifulSoup(html, 'lxml')
            
            # Extract title
            title = ""
            title_element = soup.find('title')
            if title_element:
                title = title_element.text.strip()
            
            # Extract main content
            content = ""
            
            # Try to find main content container
            main_elements = soup.find_all(['main', 'article', 'div'], 
                                         class_=lambda c: c and any(x in str(c).lower() for x in ['content', 'main', 'article']))
            
            if main_elements:
                # Use the largest content container
                main_element = max(main_elements, key=lambda x: len(x.get_text()))
                paragraphs = main_element.find_all('p')
                content = "\n\n".join(p.text.strip() for p in paragraphs)
            else:
                # If no main content container found, use all paragraphs
                paragraphs = soup.find_all('p')
                content = "\n\n".join(p.text.strip() for p in paragraphs)
            
            # Combine all extracted content
            result = []
            if title:
                result.append(f"Title: {title}")
            if content:
                result.append(f"Content: {content}")
            
            return "\n\n".join(result)
