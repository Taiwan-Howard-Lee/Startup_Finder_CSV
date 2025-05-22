"""
Database manager for the Startup Finder.

This module provides utilities for storing and retrieving data from a database.
"""

import os
import json
import time
import sqlite3
import logging
from typing import List, Dict, Any, Optional, Tuple, Union

# Set up logging
logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manager for database operations."""
    
    def __init__(self, db_path: str = "output/data/startups.db"):
        """
        Initialize the database manager.
        
        Args:
            db_path: Path to the database file
        """
        self.db_path = db_path
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Initialize the database
        self._initialize_db()
    
    def _initialize_db(self):
        """
        Initialize the database schema.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Create startups table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS startups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            data TEXT,
            source TEXT,
            query TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create urls table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE,
            content TEXT,
            cleaned_content TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create queries table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS queries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT UNIQUE,
            expanded_queries TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create sessions table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE,
            status TEXT,
            data TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create metrics table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            metric_name TEXT,
            metric_value TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(session_id, metric_name)
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def _get_connection(self):
        """
        Get a connection to the database.
        
        Returns:
            SQLite connection
        """
        return sqlite3.connect(self.db_path)
    
    def save_startup(self, name: str, data: Dict[str, Any], source: str, query: str):
        """
        Save a startup to the database.
        
        Args:
            name: Name of the startup
            data: Startup data
            source: Source of the startup information
            query: Query used to find the startup
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "INSERT OR REPLACE INTO startups (name, data, source, query) VALUES (?, ?, ?, ?)",
                (name, json.dumps(data), source, query)
            )
            conn.commit()
            logger.debug(f"Saved startup: {name}")
        except Exception as e:
            logger.error(f"Error saving startup {name}: {e}")
        finally:
            conn.close()
    
    def get_startup(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get a startup from the database.
        
        Args:
            name: Name of the startup
            
        Returns:
            Startup data or None if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT data FROM startups WHERE name = ?", (name,))
            result = cursor.fetchone()
            
            if result:
                return json.loads(result[0])
            else:
                return None
        except Exception as e:
            logger.error(f"Error getting startup {name}: {e}")
            return None
        finally:
            conn.close()
    
    def get_all_startups(self) -> List[Dict[str, Any]]:
        """
        Get all startups from the database.
        
        Returns:
            List of startup data
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT name, data, source, query, timestamp FROM startups")
            results = cursor.fetchall()
            
            startups = []
            for name, data, source, query, timestamp in results:
                startup_data = json.loads(data)
                startup_data["name"] = name
                startup_data["source"] = source
                startup_data["query"] = query
                startup_data["timestamp"] = timestamp
                startups.append(startup_data)
            
            return startups
        except Exception as e:
            logger.error(f"Error getting all startups: {e}")
            return []
        finally:
            conn.close()
    
    def save_url_content(self, url: str, content: str, cleaned_content: str):
        """
        Save URL content to the database.
        
        Args:
            url: URL
            content: Raw content
            cleaned_content: Cleaned content
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "INSERT OR REPLACE INTO urls (url, content, cleaned_content) VALUES (?, ?, ?)",
                (url, content, cleaned_content)
            )
            conn.commit()
            logger.debug(f"Saved URL content: {url}")
        except Exception as e:
            logger.error(f"Error saving URL content {url}: {e}")
        finally:
            conn.close()
    
    def get_url_content(self, url: str) -> Optional[Tuple[str, str]]:
        """
        Get URL content from the database.
        
        Args:
            url: URL
            
        Returns:
            Tuple of (raw_content, cleaned_content) or None if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT content, cleaned_content FROM urls WHERE url = ?", (url,))
            result = cursor.fetchone()
            
            if result:
                return result
            else:
                return None
        except Exception as e:
            logger.error(f"Error getting URL content {url}: {e}")
            return None
        finally:
            conn.close()
    
    def save_query(self, query: str, expanded_queries: List[str]):
        """
        Save a query and its expansions to the database.
        
        Args:
            query: Original query
            expanded_queries: List of expanded queries
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "INSERT OR REPLACE INTO queries (query, expanded_queries) VALUES (?, ?)",
                (query, json.dumps(expanded_queries))
            )
            conn.commit()
            logger.debug(f"Saved query: {query}")
        except Exception as e:
            logger.error(f"Error saving query {query}: {e}")
        finally:
            conn.close()
    
    def get_expanded_queries(self, query: str) -> List[str]:
        """
        Get expanded queries for a query from the database.
        
        Args:
            query: Original query
            
        Returns:
            List of expanded queries or empty list if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT expanded_queries FROM queries WHERE query = ?", (query,))
            result = cursor.fetchone()
            
            if result:
                return json.loads(result[0])
            else:
                return []
        except Exception as e:
            logger.error(f"Error getting expanded queries for {query}: {e}")
            return []
        finally:
            conn.close()
    
    def save_session(self, session_id: str, status: str, data: Dict[str, Any]):
        """
        Save a session to the database.
        
        Args:
            session_id: Session ID
            status: Session status
            data: Session data
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "INSERT OR REPLACE INTO sessions (session_id, status, data) VALUES (?, ?, ?)",
                (session_id, status, json.dumps(data))
            )
            conn.commit()
            logger.debug(f"Saved session: {session_id}")
        except Exception as e:
            logger.error(f"Error saving session {session_id}: {e}")
        finally:
            conn.close()
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a session from the database.
        
        Args:
            session_id: Session ID
            
        Returns:
            Session data or None if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT status, data, timestamp FROM sessions WHERE session_id = ?", (session_id,))
            result = cursor.fetchone()
            
            if result:
                status, data, timestamp = result
                session_data = json.loads(data)
                session_data["status"] = status
                session_data["timestamp"] = timestamp
                return session_data
            else:
                return None
        except Exception as e:
            logger.error(f"Error getting session {session_id}: {e}")
            return None
        finally:
            conn.close()
    
    def get_latest_session(self) -> Optional[Dict[str, Any]]:
        """
        Get the latest session from the database.
        
        Returns:
            Latest session data or None if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT session_id, status, data, timestamp FROM sessions ORDER BY timestamp DESC LIMIT 1")
            result = cursor.fetchone()
            
            if result:
                session_id, status, data, timestamp = result
                session_data = json.loads(data)
                session_data["session_id"] = session_id
                session_data["status"] = status
                session_data["timestamp"] = timestamp
                return session_data
            else:
                return None
        except Exception as e:
            logger.error(f"Error getting latest session: {e}")
            return None
        finally:
            conn.close()
    
    def save_metric(self, session_id: str, metric_name: str, metric_value: Any):
        """
        Save a metric to the database.
        
        Args:
            session_id: Session ID
            metric_name: Metric name
            metric_value: Metric value
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "INSERT OR REPLACE INTO metrics (session_id, metric_name, metric_value) VALUES (?, ?, ?)",
                (session_id, metric_name, json.dumps(metric_value))
            )
            conn.commit()
            logger.debug(f"Saved metric: {metric_name}")
        except Exception as e:
            logger.error(f"Error saving metric {metric_name}: {e}")
        finally:
            conn.close()
    
    def get_metrics(self, session_id: str) -> Dict[str, Any]:
        """
        Get metrics for a session from the database.
        
        Args:
            session_id: Session ID
            
        Returns:
            Dictionary of metrics
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT metric_name, metric_value FROM metrics WHERE session_id = ?", (session_id,))
            results = cursor.fetchall()
            
            metrics = {}
            for metric_name, metric_value in results:
                metrics[metric_name] = json.loads(metric_value)
            
            return metrics
        except Exception as e:
            logger.error(f"Error getting metrics for session {session_id}: {e}")
            return {}
        finally:
            conn.close()
