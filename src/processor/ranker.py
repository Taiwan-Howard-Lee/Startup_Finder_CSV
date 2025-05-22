"""
Ranker for Startup Intelligence Finder.

This module provides functionality to rank and score startup results based on
relevance to the original query and information quality.
"""

import re
from typing import Dict, List, Any, Optional, Set


class Ranker:
    """
    A ranker for startup search results.
    
    This class provides methods to calculate relevance scores for startups
    based on their content and the original search query.
    """
    
    def __init__(self):
        """Initialize the ranker."""
        # Define important fields for information quality assessment
        self.important_fields = [
            "Company Name",
            "Founded Year",
            "Location",
            "Website",
            "Founders",
            "Funding Information",
            "Technology Stack",
            "Product Description"
        ]
        
        # Define weights for different components of the overall score
        self.weights = {
            "content_relevance": 0.6,
            "information_quality": 0.4
        }
    
    def calculate_content_relevance(self, startup_data: Dict[str, Any], query: str) -> float:
        """
        Calculate how relevant a startup is to the search query based on content.
        
        Args:
            startup_data: Dictionary containing startup information.
            query: Original search query.
            
        Returns:
            Relevance score between 0 and 1.
        """
        # Extract query terms (excluding common words)
        query_terms = set(self._extract_terms(query))
        
        # Extract terms from startup data
        startup_terms = set()
        for field, value in startup_data.items():
            if isinstance(value, str):
                startup_terms.update(self._extract_terms(value))
        
        # Calculate overlap between query terms and startup terms
        if not query_terms:
            return 0.0
            
        overlap = len(query_terms.intersection(startup_terms))
        relevance = overlap / len(query_terms)
        
        return min(1.0, relevance)
    
    def calculate_information_quality(self, startup_data: Dict[str, Any]) -> float:
        """
        Calculate the quality of information available for a startup.
        
        Args:
            startup_data: Dictionary containing startup information.
            
        Returns:
            Quality score between 0 and 1.
        """
        # Count how many important fields are present and have meaningful values
        present_fields = 0
        
        for field in self.important_fields:
            if field in startup_data and startup_data[field] and startup_data[field] != "Unknown":
                present_fields += 1
        
        # Calculate quality as the proportion of important fields present
        quality = present_fields / len(self.important_fields)
        
        return quality
    
    def calculate_startup_relevance(self, startup_data: Dict[str, Any], query: str) -> float:
        """
        Calculate the overall relevance of a startup to the search query.
        
        Args:
            startup_data: Dictionary containing startup information.
            query: Original search query.
            
        Returns:
            Relevance score between 0 and 1.
        """
        # Calculate content relevance
        content_relevance = self.calculate_content_relevance(startup_data, query)
        
        # Calculate information quality
        information_quality = self.calculate_information_quality(startup_data)
        
        # Calculate weighted average
        relevance = (
            self.weights["content_relevance"] * content_relevance +
            self.weights["information_quality"] * information_quality
        )
        
        return relevance
    
    def calculate_overall_score(self, startup_data: Dict[str, Any], query: str) -> float:
        """
        Calculate the overall score for a startup.
        
        Args:
            startup_data: Dictionary containing startup information.
            query: Original search query.
            
        Returns:
            Overall score between 0 and 1.
        """
        # For now, this is the same as startup relevance
        return self.calculate_startup_relevance(startup_data, query)
    
    def rank_results(self, results: List[Dict[str, Any]], query: str, min_confidence: float = 0.0) -> List[Dict[str, Any]]:
        """
        Rank a list of startup results based on relevance to the query.
        
        Args:
            results: List of startup data dictionaries.
            query: Original search query.
            min_confidence: Minimum confidence score to include in results.
            
        Returns:
            Ranked list of startup data dictionaries with confidence scores.
        """
        # Calculate scores for each result
        scored_results = []
        
        for result in results:
            score = self.calculate_overall_score(result, query)
            
            # Only include results above the minimum confidence threshold
            if score >= min_confidence:
                # Create a copy of the result with the confidence score added
                scored_result = result.copy()
                scored_result["confidence"] = score
                scored_results.append(scored_result)
        
        # Sort by score in descending order
        ranked_results = sorted(scored_results, key=lambda x: x["confidence"], reverse=True)
        
        return ranked_results
    
    def _extract_terms(self, text: str) -> List[str]:
        """
        Extract meaningful terms from text.
        
        Args:
            text: Text to extract terms from.
            
        Returns:
            List of extracted terms.
        """
        if not text:
            return []
            
        # Convert to lowercase
        text = text.lower()
        
        # Remove punctuation and split into words
        words = re.findall(r'\b\w+\b', text)
        
        # Remove common stop words
        stop_words = {
            "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "with",
            "by", "about", "as", "of", "from", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will", "would", "shall",
            "should", "can", "could", "may", "might", "must", "that", "which", "who",
            "whom", "whose", "this", "these", "those", "i", "you", "he", "she", "it",
            "we", "they", "me", "him", "her", "us", "them"
        }
        
        terms = [word for word in words if word not in stop_words and len(word) > 1]
        
        return terms
