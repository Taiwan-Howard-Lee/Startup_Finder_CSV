"""
Query optimization utilities for the Startup Finder.

This module provides utilities for optimizing search queries,
including query clustering, semantic deduplication, and query expansion.
"""

import re
import logging
import numpy as np
from typing import List, Dict, Any, Optional, Set, Tuple

# Set up logging
logger = logging.getLogger(__name__)

class QueryOptimizer:
    """Utilities for optimizing search queries."""
    
    @staticmethod
    def normalize_query(query: str) -> str:
        """
        Normalize a query by removing special characters and extra whitespace.
        
        Args:
            query: Query to normalize
            
        Returns:
            Normalized query
        """
        # Convert to lowercase
        query = query.lower()
        
        # Remove special characters
        query = re.sub(r'[^\w\s]', ' ', query)
        
        # Replace multiple spaces with a single space
        query = re.sub(r'\s+', ' ', query)
        
        # Remove leading and trailing whitespace
        query = query.strip()
        
        return query
    
    @staticmethod
    def remove_stopwords(query: str) -> str:
        """
        Remove stopwords from a query.
        
        Args:
            query: Query to process
            
        Returns:
            Query without stopwords
        """
        stopwords = {
            'a', 'an', 'the', 'and', 'or', 'but', 'if', 'because', 'as', 'what',
            'which', 'this', 'that', 'these', 'those', 'then', 'just', 'so', 'than',
            'such', 'both', 'through', 'about', 'for', 'is', 'of', 'while', 'during',
            'to', 'from', 'in', 'on', 'by', 'with', 'at', 'into'
        }
        
        # Split query into words
        words = query.split()
        
        # Filter out stopwords
        filtered_words = [word for word in words if word.lower() not in stopwords]
        
        # Join words back into a query
        return ' '.join(filtered_words)
    
    @staticmethod
    def extract_keywords(query: str) -> List[str]:
        """
        Extract keywords from a query.
        
        Args:
            query: Query to extract keywords from
            
        Returns:
            List of keywords
        """
        # Normalize query
        query = QueryOptimizer.normalize_query(query)
        
        # Remove stopwords
        query = QueryOptimizer.remove_stopwords(query)
        
        # Split into words
        words = query.split()
        
        # Filter out short words
        keywords = [word for word in words if len(word) > 2]
        
        return keywords
    
    @staticmethod
    def cluster_queries(queries: List[str], n_clusters: int = 5) -> List[str]:
        """
        Cluster queries and return a representative query from each cluster.
        
        Args:
            queries: List of queries to cluster
            n_clusters: Number of clusters
            
        Returns:
            List of representative queries
        """
        if not queries:
            return []
        
        # Ensure we don't try to create more clusters than queries
        n_clusters = min(n_clusters, len(queries))
        
        try:
            # Try to use scikit-learn if available
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.cluster import KMeans
            
            # Convert queries to vectors
            vectorizer = TfidfVectorizer(stop_words='english')
            X = vectorizer.fit_transform(queries)
            
            # Cluster queries
            kmeans = KMeans(n_clusters=n_clusters, random_state=42)
            kmeans.fit(X)
            
            # Get cluster centers
            centers = kmeans.cluster_centers_
            
            # Find the query closest to each cluster center
            representative_queries = []
            for i in range(n_clusters):
                # Get queries in this cluster
                cluster_queries = [queries[j] for j in range(len(queries)) if kmeans.labels_[j] == i]
                
                if not cluster_queries:
                    continue
                
                # If only one query in cluster, use it
                if len(cluster_queries) == 1:
                    representative_queries.append(cluster_queries[0])
                    continue
                
                # Find query closest to center
                cluster_vectors = vectorizer.transform(cluster_queries)
                center = centers[i].reshape(1, -1)
                distances = np.sqrt(((cluster_vectors - center) ** 2).sum(axis=1))
                closest_idx = distances.argmin()
                
                representative_queries.append(cluster_queries[closest_idx])
            
            return representative_queries
        
        except ImportError:
            logger.warning("scikit-learn not installed. Using simple clustering instead.")
            return QueryOptimizer._simple_cluster_queries(queries, n_clusters)
    
    @staticmethod
    def _simple_cluster_queries(queries: List[str], n_clusters: int = 5) -> List[str]:
        """
        Simple clustering of queries based on word overlap.
        
        Args:
            queries: List of queries to cluster
            n_clusters: Number of clusters
            
        Returns:
            List of representative queries
        """
        if not queries:
            return []
        
        # Extract keywords for each query
        query_keywords = [(query, set(QueryOptimizer.extract_keywords(query))) for query in queries]
        
        # Calculate similarity matrix
        n = len(queries)
        similarity_matrix = np.zeros((n, n))
        
        for i in range(n):
            for j in range(i, n):
                _, keywords_i = query_keywords[i]
                _, keywords_j = query_keywords[j]
                
                # Calculate Jaccard similarity
                if not keywords_i or not keywords_j:
                    similarity = 0.0
                else:
                    intersection = len(keywords_i.intersection(keywords_j))
                    union = len(keywords_i.union(keywords_j))
                    similarity = intersection / union if union > 0 else 0.0
                
                similarity_matrix[i, j] = similarity
                similarity_matrix[j, i] = similarity
        
        # Simple greedy clustering
        remaining_indices = set(range(n))
        clusters = []
        
        while len(clusters) < n_clusters and remaining_indices:
            # Find the query with the most connections
            best_idx = -1
            best_connections = -1
            
            for i in remaining_indices:
                connections = sum(1 for j in remaining_indices if similarity_matrix[i, j] > 0.3)
                if connections > best_connections:
                    best_connections = connections
                    best_idx = i
            
            if best_idx == -1:
                # No more connections, just take the first remaining index
                best_idx = next(iter(remaining_indices))
            
            # Create a new cluster
            cluster = {best_idx}
            remaining_indices.remove(best_idx)
            
            # Add similar queries to the cluster
            for j in list(remaining_indices):
                if similarity_matrix[best_idx, j] > 0.3:
                    cluster.add(j)
                    remaining_indices.remove(j)
            
            clusters.append(cluster)
        
        # Get a representative query from each cluster
        representative_queries = []
        
        for cluster in clusters:
            if not cluster:
                continue
            
            # Use the query with the most keywords
            best_query = ""
            most_keywords = 0
            
            for idx in cluster:
                query, keywords = query_keywords[idx]
                if len(keywords) > most_keywords:
                    most_keywords = len(keywords)
                    best_query = query
            
            if best_query:
                representative_queries.append(best_query)
        
        return representative_queries
    
    @staticmethod
    def deduplicate_semantically(texts: List[str], threshold: float = 0.85) -> List[str]:
        """
        Deduplicate texts based on semantic similarity.
        
        Args:
            texts: List of texts to deduplicate
            threshold: Similarity threshold for deduplication
            
        Returns:
            List of deduplicated texts
        """
        if not texts:
            return []
        
        try:
            # Try to use sentence-transformers if available
            from sentence_transformers import SentenceTransformer
            
            # Load model
            model = SentenceTransformer('all-MiniLM-L6-v2')
            
            # Encode all texts
            embeddings = model.encode(texts)
            
            # Compute similarity matrix
            similarity_matrix = np.inner(embeddings, embeddings)
            
            # Find duplicates
            unique_indices = []
            for i in range(len(texts)):
                if not any(similarity_matrix[i][j] > threshold for j in unique_indices):
                    unique_indices.append(i)
            
            return [texts[i] for i in unique_indices]
        
        except ImportError:
            logger.warning("sentence-transformers not installed. Using keyword-based deduplication instead.")
            return QueryOptimizer._keyword_based_deduplication(texts, threshold)
    
    @staticmethod
    def _keyword_based_deduplication(texts: List[str], threshold: float = 0.85) -> List[str]:
        """
        Deduplicate texts based on keyword overlap.
        
        Args:
            texts: List of texts to deduplicate
            threshold: Similarity threshold for deduplication
            
        Returns:
            List of deduplicated texts
        """
        if not texts:
            return []
        
        # Extract keywords for each text
        text_keywords = [(text, set(QueryOptimizer.extract_keywords(text))) for text in texts]
        
        # Find unique texts
        unique_texts = []
        
        for i, (text, keywords_i) in enumerate(text_keywords):
            # Check if this text is similar to any already selected unique text
            is_duplicate = False
            
            for unique_text, keywords_j in [(texts[j], text_keywords[j][1]) for j in range(i) if texts[j] in unique_texts]:
                # Calculate Jaccard similarity
                if not keywords_i or not keywords_j:
                    similarity = 0.0
                else:
                    intersection = len(keywords_i.intersection(keywords_j))
                    union = len(keywords_i.union(keywords_j))
                    similarity = intersection / union if union > 0 else 0.0
                
                if similarity > threshold:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_texts.append(text)
        
        return unique_texts
