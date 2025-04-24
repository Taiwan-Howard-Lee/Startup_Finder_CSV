"""
Ranker for Startup Intelligence Finder.

This module handles ranking and scoring of search results.
"""

import re
from typing import Dict, List, Optional, Tuple, Union


class Ranker:
    """
    A utility for ranking and scoring startup search results.
    
    This class evaluates and ranks startup data based on relevance to the
    original query, information quality, and other factors.
    """
    
    def __init__(self):
        """Initialize the ranker."""
        # Scoring weights
        self.weights = {
            "content_relevance": 0.4,  # How relevant the startup is to the query
            "information_quality": 0.3,  # How complete and reliable the information is
            "startup_relevance": 0.3,  # How relevant the startup is in its field
        }
    
    def calculate_content_relevance(self, 
                                   startup_data: Dict[str, str], 
                                   query: str) -> float:
        """
        Calculate how relevant the startup is to the search query.
        
        Args:
            startup_data: Startup data dictionary.
            query: Original search query.
            
        Returns:
            Relevance score between 0 and 1.
        """
        # Convert query to lowercase and split into words
        query_words = set(query.lower().split())
        
        # Count matches in different fields with different weights
        field_weights = {
            "Company Name": 3.0,
            "Product Description": 2.0,
            "Technology Stack": 1.5,
            "Business Model": 1.5,
            "Target Market": 1.5,
            "Founders": 1.0,
            "Location": 0.5,
        }
        
        total_weight = sum(field_weights.values())
        weighted_score = 0.0
        
        for field, weight in field_weights.items():
            if field in startup_data:
                field_value = str(startup_data[field]).lower()
                
                # Count how many query words appear in this field
                matches = sum(1 for word in query_words if word in field_value)
                
                # Calculate weighted score for this field
                field_score = (matches / len(query_words)) * weight
                weighted_score += field_score
        
        # Normalize to 0-1 range
        normalized_score = min(weighted_score / total_weight, 1.0)
        
        return normalized_score
    
    def calculate_information_quality(self, startup_data: Dict[str, str]) -> float:
        """
        Calculate the quality and completeness of the startup information.
        
        Args:
            startup_data: Startup data dictionary.
            
        Returns:
            Quality score between 0 and 1.
        """
        # Define essential fields and their weights
        field_weights = {
            "Company Name": 1.0,
            "Founded Year": 0.8,
            "Location": 0.8,
            "Website": 0.9,
            "Founders": 0.7,
            "Funding Information": 0.6,
            "Technology Stack": 0.5,
            "Product Description": 0.7,
            "Team Size": 0.4,
            "Business Model": 0.6,
            "Target Market": 0.5,
        }
        
        total_weight = sum(field_weights.values())
        weighted_score = 0.0
        
        for field, weight in field_weights.items():
            if field in startup_data:
                value = startup_data[field]
                
                # Check if the field has valid content
                if value and value.lower() not in ["unknown", "not available", "n/a"]:
                    # Check the quality of the content
                    if len(str(value)) > 10:  # More detailed information
                        weighted_score += weight
                    else:  # Basic information
                        weighted_score += weight * 0.7
        
        # Normalize to 0-1 range
        normalized_score = weighted_score / total_weight
        
        return normalized_score
    
    def calculate_startup_relevance(self, 
                                   startup_data: Dict[str, str], 
                                   query: str) -> float:
        """
        Calculate how relevant the startup is in its field.
        
        Args:
            startup_data: Startup data dictionary.
            query: Original search query.
            
        Returns:
            Relevance score between 0 and 1.
        """
        # This is a simplified implementation
        # In a real-world scenario, this would use more sophisticated analysis
        
        # For now, use a simple heuristic based on funding and founding year
        score = 0.5  # Default score
        
        # Check funding information
        funding_info = startup_data.get("Funding Information", "").lower()
        if "series c" in funding_info or "series d" in funding_info:
            score += 0.3
        elif "series b" in funding_info:
            score += 0.2
        elif "series a" in funding_info:
            score += 0.1
        elif "seed" in funding_info:
            score += 0.05
        
        # Check founding year
        founded_year = startup_data.get("Founded Year", "")
        if founded_year and founded_year != "Unknown":
            try:
                year = int(founded_year)
                current_year = 2024  # This should be dynamic in a real implementation
                
                # Newer startups might be more relevant for trending topics
                years_old = current_year - year
                if years_old <= 2:
                    score += 0.2
                elif years_old <= 5:
                    score += 0.1
                elif years_old <= 10:
                    score += 0.05
            except ValueError:
                pass
        
        # Cap at 1.0
        return min(score, 1.0)
    
    def calculate_overall_score(self, 
                               startup_data: Dict[str, str], 
                               query: str) -> float:
        """
        Calculate the overall score for a startup.
        
        Args:
            startup_data: Startup data dictionary.
            query: Original search query.
            
        Returns:
            Overall score between 0 and 1.
        """
        # Calculate individual scores
        content_relevance = self.calculate_content_relevance(startup_data, query)
        information_quality = self.calculate_information_quality(startup_data)
        startup_relevance = self.calculate_startup_relevance(startup_data, query)
        
        # Calculate weighted average
        overall_score = (
            content_relevance * self.weights["content_relevance"] +
            information_quality * self.weights["information_quality"] +
            startup_relevance * self.weights["startup_relevance"]
        )
        
        return overall_score
    
    def rank_results(self, 
                    results: List[Dict[str, str]], 
                    query: str,
                    min_confidence: float = 0.0) -> List[Dict[str, Union[str, float]]]:
        """
        Rank search results by relevance.
        
        Args:
            results: List of startup data dictionaries.
            query: Original search query.
            min_confidence: Minimum confidence score to include in results.
            
        Returns:
            List of ranked startup data dictionaries with confidence scores.
        """
        scored_results = []
        
        for result in results:
            # Calculate overall score
            score = self.calculate_overall_score(result, query)
            
            # Only include results above the minimum confidence threshold
            if score >= min_confidence:
                # Add score to the result
                result_with_score = result.copy()
                result_with_score["confidence"] = round(score, 2)
                
                scored_results.append(result_with_score)
        
        # Sort by score in descending order
        ranked_results = sorted(
            scored_results, 
            key=lambda x: x["confidence"], 
            reverse=True
        )
        
        return ranked_results
