"""
Span Registry for ATLAS Telemetry

This module provides interfaces and implementations for storing and retrieving span IDs
across different environments (development, staging, production) using either
in-memory storage or Redis for multi-worker support.
"""

import abc
import os
import logging
import sqlite3
import time
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse, ParseResult

logger = logging.getLogger(__name__)

def mask_redis_url(url: str) -> str:
    """Mask sensitive information in a Redis URL.
    
    Args:
        url: The Redis URL to mask
        
    Returns:
        A masked version of the URL with sensitive information replaced with asterisks
    """
    try:
        parsed = urlparse(url)
        # Create a new ParseResult with masked password
        masked = ParseResult(
            scheme=parsed.scheme,
            netloc=f"{parsed.username}:****@{parsed.hostname}:{parsed.port}" if parsed.password else parsed.netloc,
            path=parsed.path,
            params=parsed.params,
            query=parsed.query,
            fragment=parsed.fragment
        )
        return masked.geturl()
    except Exception:
        # If parsing fails, return a generic masked string
        return "redis://****@****"

class SpanRegistry(abc.ABC):
    """Abstract base class for span registry implementations"""
    
    @abc.abstractmethod
    def register_span(self, session_id: str, qa_id: str, span_id: str, trace_id: Optional[str] = None) -> None:
        """Register a span ID for a session and QA pair with optional trace_id"""
        pass
    
    @abc.abstractmethod
    def register_root_span(self, session_id: str, span_id: str, trace_id: Optional[str] = None) -> None:
        """Register a root span ID for a session with optional trace_id"""
        pass
    
    @abc.abstractmethod
    def find_span(self, session_id: str, qa_id: str) -> Optional[str]:
        """Find a span ID for a session and QA pair"""
        pass
    
    @abc.abstractmethod
    def find_span_by_trace(self, trace_id: str) -> Optional[str]:
        """Find a span ID by trace_id"""
        pass
    
    @abc.abstractmethod
    def find_root_span(self, session_id: str) -> Optional[str]:
        """Find the root span ID for a session"""
        pass
    
    @abc.abstractmethod
    def list_spans(self, session_id: str) -> Dict[str, str]:
        """List all spans for a session"""
        pass


class MemorySpanRegistry(SpanRegistry):
    """In-memory implementation of span registry for development"""
    
    def __init__(self):
        self._registry = {}  # session_id -> {qa_id -> span_id}
        self._trace_registry = {}  # trace_id -> span_id
        logger.info("Using in-memory span registry (development mode)")
    
    def register_span(self, session_id: str, qa_id: str, span_id: str, trace_id: Optional[str] = None) -> None:
        if not session_id:
            logger.warning("Cannot register span without session_id")
            return
            
        if session_id not in self._registry:
            self._registry[session_id] = {}
        
        self._registry[session_id][qa_id] = str(span_id)
        
        # Register with trace_id if provided
        if trace_id:
            self._trace_registry[trace_id] = str(span_id)
        
        if qa_id and qa_id.endswith("_response"):
            logger.info(f"Registered response span: session={session_id}, qa_id={qa_id}, span_id={span_id}")
        else:
            logger.debug(f"Registered span: session={session_id}, qa_id={qa_id}, span_id={span_id}")
    
    def register_root_span(self, session_id: str, span_id: str, trace_id: Optional[str] = None) -> None:
        if not session_id:
            logger.warning("Cannot register root span without session_id")
            return
            
        if session_id not in self._registry:
            self._registry[session_id] = {}
        
        # Use None as special key for root span
        self._registry[session_id][None] = str(span_id)
        # Also with string key for consistent API
        self._registry[session_id]["root"] = str(span_id)
        
        # Register with trace_id if provided
        if trace_id:
            self._trace_registry[trace_id] = str(span_id)
            self._trace_registry[f"root:{trace_id}"] = str(span_id)
        
        logger.info(f"Registered root span: session={session_id}, span_id={span_id}")
    
    def find_span(self, session_id: str, qa_id: str) -> Optional[str]:
        if not session_id or qa_id is None:
            return None
            
        if session_id in self._registry and qa_id in self._registry[session_id]:
            span_id = self._registry[session_id][qa_id]
            logger.debug(f"Found span: session={session_id}, qa_id={qa_id}, span_id={span_id}")
            return span_id
        
        logger.warning(f"Could not find span: session={session_id}, qa_id={qa_id}")
        return None
    
    def find_span_by_trace(self, trace_id: str) -> Optional[str]:
        if not trace_id:
            return None
            
        if trace_id in self._trace_registry:
            span_id = self._trace_registry[trace_id]
            logger.debug(f"Found span by trace_id: {trace_id}, span_id={span_id}")
            return span_id
        
        logger.warning(f"Could not find span by trace_id: {trace_id}")
        return None
    
    def find_root_span(self, session_id: str) -> Optional[str]:
        if not session_id:
            return None
            
        # Check for explicit root span (None key)
        if session_id in self._registry and None in self._registry[session_id]:
            return self._registry[session_id][None]
        
        # Check for string root key
        if session_id in self._registry and "root" in self._registry[session_id]:
            return self._registry[session_id]["root"]
        
        # If no root span is explicitly registered, use the first span ID
        if session_id in self._registry and self._registry[session_id]:
            first_qa_id = next(iter(self._registry[session_id]))
            if first_qa_id is not None and first_qa_id != "root":
                return self._registry[session_id][first_qa_id]
        
        logger.warning(f"Could not find root span for session: {session_id}")
        return None
    
    def list_spans(self, session_id: str) -> Dict[str, str]:
        return {
            k: v for k, v in self._registry.get(session_id, {}).items() 
            if k is not None
        }


class SQLiteSpanRegistry(SpanRegistry):
    """SQLite-based implementation of span registry for development"""

    def __init__(self, db_path="./telemetry_span_registry.db", key_expiry_seconds=86400):
        self.db_path = db_path
        self.key_expiry_seconds = key_expiry_seconds
        self._conn = None
        self._ensure_connection()
        self._create_table()
        logger.info(f"Using SQLite span registry (development mode) at {self.db_path}")

    def _ensure_connection(self):
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row # Access columns by name

    def _create_table(self):
        self._ensure_connection()
        try:
            with self._conn:
                self._conn.execute("""
                    CREATE TABLE IF NOT EXISTS span_mappings (
                        key TEXT PRIMARY KEY,
                        session_id TEXT NOT NULL,
                        qa_id TEXT, 
                        span_id TEXT NOT NULL,
                        trace_id TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                self._conn.execute("CREATE INDEX IF NOT EXISTS idx_session_id ON span_mappings (session_id)")
                self._conn.execute("CREATE INDEX IF NOT EXISTS idx_qa_id ON span_mappings (qa_id)")
                self._conn.execute("CREATE INDEX IF NOT EXISTS idx_trace_id ON span_mappings (trace_id)")
                self._conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON span_mappings (timestamp)")
        except sqlite3.Error as e:
            logger.error(f"SQLite error creating table: {e}")

    def _cleanup_expired_entries(self):
        self._ensure_connection()
        try:
            with self._conn:
                self._conn.execute(
                    "DELETE FROM span_mappings WHERE timestamp < datetime('now', ?)",
                    (f'-{self.key_expiry_seconds} seconds',)
                )
        except sqlite3.Error as e:
            logger.error(f"SQLite error cleaning up expired entries: {e}")

    def register_span(self, session_id: str, qa_id: str, span_id: str, trace_id: Optional[str] = None) -> None:
        if not session_id or not qa_id:
            logger.warning("Cannot register span without session_id and qa_id for SQLite registry")
            return
        
        self._ensure_connection()
        self._cleanup_expired_entries() # Periodically cleanup
        key = f"{session_id}:{qa_id}"
        try:
            with self._conn:
                self._conn.execute("""
                    INSERT OR REPLACE INTO span_mappings (key, session_id, qa_id, span_id, trace_id, timestamp)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (key, session_id, qa_id, str(span_id), trace_id))
            logger.debug(f"SQLite Registered span: key={key}, span_id={span_id}")
        except sqlite3.Error as e:
            logger.error(f"SQLite error registering span {key}: {e}")

    def find_span(self, session_id: str, qa_id: str) -> Optional[str]:
        if not session_id or not qa_id:
            return None
        
        self._ensure_connection()
        key = f"{session_id}:{qa_id}"
        try:
            with self._conn:
                cursor = self._conn.execute("SELECT span_id FROM span_mappings WHERE key = ?", (key,))
                row = cursor.fetchone()
            if row:
                logger.debug(f"SQLite Found span: key={key}, span_id={row['span_id']}")
                return row['span_id']
        except sqlite3.Error as e:
            logger.error(f"SQLite error finding span {key}: {e}")
        
        logger.warning(f"SQLite Could not find span: key={key}")
        return None

    def register_root_span(self, session_id: str, span_id: str, trace_id: Optional[str] = None) -> None:
        if not session_id:
            logger.warning("Cannot register root span without session_id for SQLite registry")
            return
        self.register_span(session_id, "_root_", span_id, trace_id)
        logger.debug(f"SQLite Registered root span: session={session_id}, span_id={span_id}")

    def find_span_by_trace(self, trace_id: str) -> Optional[str]:
        if not trace_id:
            return None
        self._ensure_connection()
        try:
            with self._conn:
                cursor = self._conn.execute("SELECT span_id FROM span_mappings WHERE trace_id = ? ORDER BY timestamp DESC LIMIT 1", (trace_id,))
                row = cursor.fetchone()
            if row:
                logger.debug(f"SQLite Found span by trace_id={trace_id}, span_id={row['span_id']}")
                return row['span_id']
        except sqlite3.Error as e:
            logger.error(f"SQLite error finding span by trace_id {trace_id}: {e}")
        return None

    def find_root_span(self, session_id: str) -> Optional[str]:
        if not session_id:
            return None
        span_id = self.find_span(session_id, "_root_")
        if span_id:
            logger.debug(f"SQLite Found root span: session={session_id}, span_id={span_id}")
        return span_id

    def list_spans(self, session_id: str) -> Dict[str, str]:
        if not session_id:
            return {}
        self._ensure_connection()
        spans = {}
        try:
            with self._conn:
                cursor = self._conn.execute("SELECT qa_id, span_id FROM span_mappings WHERE session_id = ?", (session_id,))
                for row in cursor.fetchall():
                    if row['qa_id'] and row['qa_id'] != "_root_": # Exclude special root key from this list
                        spans[row['qa_id']] = row['span_id']
        except sqlite3.Error as e:
            logger.error(f"SQLite error listing spans for session {session_id}: {e}")
        return spans

    def __del__(self):
        if self._conn:
            self._conn.close()


class RedisSpanRegistry(SpanRegistry):
    """Redis-based implementation of span registry for staging/production"""
    
    def __init__(self, redis_url=None, db=None, key_prefix="atlas:span:", key_expiry=3600):
        self.key_prefix = key_prefix
        self.key_expiry = key_expiry
        self._registry = {}
        self._trace_registry = {}
        self._pool = None
        self._redis_available = False
        
        # Use environment variable if no URL provided
        if not redis_url:
            redis_url = os.getenv('REDIS_URL')
            
        if not redis_url:
            logger.warning("No Redis URL provided. Using in-memory fallback.")
            return
            
        try:
            import redis
            from redis.connection import ConnectionPool
            from redis.exceptions import ConnectionError as RedisConnectionError
            
            self._pool = ConnectionPool.from_url(redis_url)
            # Test connection
            client = redis.Redis(connection_pool=self._pool)
            client.ping()
            self._redis_available = True
        except ImportError:
            logger.error("Redis package not installed. Using in-memory fallback.")
            self._pool = None
            self._redis_available = False
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}. Using in-memory fallback.")
            self._pool = None
            self._redis_available = False
    
    def register_span(self, session_id: str, qa_id: str, span_id: str, trace_id: Optional[str] = None) -> None:
        if not session_id:
            logger.warning("Cannot register span without session_id")
            return
            
        # Always update in-memory fallback
        if session_id not in self._registry:
            self._registry[session_id] = {}
        self._registry[session_id][qa_id] = str(span_id)
        
        # Register with trace_id in memory if provided
        if trace_id:
            self._trace_registry[trace_id] = str(span_id)
        
        # Try Redis if available
        if self._redis_available and self._pool:
            try:
                import redis
                client = redis.Redis(connection_pool=self._pool)
                
                # Store in main session hash
                session_key = f"{self.key_prefix}{session_id}"
                client.hset(session_key, qa_id, str(span_id))
                client.expire(session_key, self.key_expiry)
                
                # Store trace_id mapping if provided
                if trace_id:
                    trace_key = f"{self.key_prefix}trace:{trace_id}"
                    client.set(trace_key, str(span_id))
                    client.expire(trace_key, self.key_expiry)
                    
                    # Also store in session hash for redundancy
                    client.hset(session_key, f"trace:{trace_id}", str(span_id))
                
                if qa_id and qa_id.endswith("_response"):
                    logger.info(f"Registered response span in Redis: session={session_id}, qa_id={qa_id}")
                else:
                    logger.debug(f"Registered span in Redis: session={session_id}, qa_id={qa_id}")
            except Exception as e:
                logger.warning(f"Failed to register span in Redis: {e}")
    
    def register_root_span(self, session_id: str, span_id: str, trace_id: Optional[str] = None) -> None:
        if not session_id:
            logger.warning("Cannot register root span without session_id")
            return
            
        # Always update in-memory fallback
        if session_id not in self._registry:
            self._registry[session_id] = {}
        self._registry[session_id][None] = str(span_id)
        self._registry[session_id]["root"] = str(span_id)
        
        # Register with trace_id in memory if provided
        if trace_id:
            self._trace_registry[trace_id] = str(span_id)
            self._trace_registry[f"root:{trace_id}"] = str(span_id)
        
        # Try Redis if available
        if self._redis_available and self._pool:
            try:
                import redis
                client = redis.Redis(connection_pool=self._pool)
                
                # Store in session hash
                session_key = f"{self.key_prefix}{session_id}"
                client.hset(session_key, "root", str(span_id))
                client.expire(session_key, self.key_expiry)
                
                # Store trace_id mapping if provided
                if trace_id:
                    trace_key = f"{self.key_prefix}trace:{trace_id}"
                    client.set(trace_key, str(span_id))
                    client.expire(trace_key, self.key_expiry)
                    
                    # Mark as root
                    root_trace_key = f"{self.key_prefix}trace:root:{trace_id}"
                    client.set(root_trace_key, str(span_id))
                    client.expire(root_trace_key, self.key_expiry)
                
                logger.info(f"Registered root span in Redis: session={session_id}")
            except Exception as e:
                logger.warning(f"Failed to register root span in Redis: {e}")
    
    def find_span(self, session_id: str, qa_id: str) -> Optional[str]:
        if not session_id or qa_id is None:
            return None
            
        # Try Redis first if available
        if self._redis_available and self._pool:
            try:
                import redis
                client = redis.Redis(connection_pool=self._pool)
                
                # Look up in session hash
                session_key = f"{self.key_prefix}{session_id}"
                span_id = client.hget(session_key, qa_id)
                
                if span_id:
                    span_id_str = span_id.decode('utf-8')
                    logger.debug(f"Found span in Redis: session={session_id}, qa_id={qa_id}, span_id={span_id_str}")
                    return span_id_str
            except Exception as e:
                logger.warning(f"Failed to find span in Redis: {e}")
        
        # Fall back to in-memory
        if session_id in self._registry and qa_id in self._registry[session_id]:
            span_id = self._registry[session_id][qa_id]
            logger.debug(f"Found span in memory: session={session_id}, qa_id={qa_id}, span_id={span_id}")
            return span_id
        
        logger.warning(f"Could not find span: session={session_id}, qa_id={qa_id}")
        return None
    
    def find_span_by_trace(self, trace_id: str) -> Optional[str]:
        if not trace_id:
            return None
            
        # Try Redis first if available
        if self._redis_available and self._pool:
            try:
                import redis
                client = redis.Redis(connection_pool=self._pool)
                
                # Look up by trace_id
                trace_key = f"{self.key_prefix}trace:{trace_id}"
                span_id = client.get(trace_key)
                
                if span_id:
                    span_id_str = span_id.decode('utf-8')
                    logger.debug(f"Found span in Redis by trace_id: {trace_id}, span_id={span_id_str}")
                    return span_id_str
            except Exception as e:
                logger.warning(f"Failed to find span by trace_id in Redis: {e}")
        
        # Fall back to in-memory
        if trace_id in self._trace_registry:
            span_id = self._trace_registry[trace_id]
            logger.debug(f"Found span in memory by trace_id: {trace_id}, span_id={span_id}")
            return span_id
        
        logger.warning(f"Could not find span by trace_id: {trace_id}")
        return None
    
    def find_root_span(self, session_id: str) -> Optional[str]:
        if not session_id:
            return None
            
        # Try Redis first if available
        if self._redis_available and self._pool:
            try:
                import redis
                client = redis.Redis(connection_pool=self._pool)
                
                # Look up explicit root span
                session_key = f"{self.key_prefix}{session_id}"
                root_span_id = client.hget(session_key, "root")
                
                if root_span_id:
                    span_id_str = root_span_id.decode('utf-8')
                    logger.debug(f"Found root span in Redis: session={session_id}, span_id={span_id_str}")
                    return span_id_str
                
                # If no explicit root span, get any span from the session
                all_spans = client.hgetall(session_key)
                if all_spans:
                    # Get first span ID
                    for k, v in all_spans.items():
                        key_str = k.decode('utf-8')
                        if key_str not in ("root", "") and not key_str.startswith("trace:"):
                            span_id_str = v.decode('utf-8')
                            logger.debug(f"Using first span as root in Redis: session={session_id}, span_id={span_id_str}")
                            return span_id_str
            except Exception as e:
                logger.warning(f"Failed to find root span in Redis: {e}")
        
        # Fall back to in-memory
        return self._find_root_span_in_memory(session_id)
    
    def _find_root_span_in_memory(self, session_id: str) -> Optional[str]:
        # Check for explicit root span (None key)
        if session_id in self._registry and None in self._registry[session_id]:
            return self._registry[session_id][None]
        
        # Check for string root key
        if session_id in self._registry and "root" in self._registry[session_id]:
            return self._registry[session_id]["root"]
        
        # If no root span is explicitly registered, use the first span ID
        if session_id in self._registry and self._registry[session_id]:
            first_qa_id = next(iter(self._registry[session_id]))
            if first_qa_id is not None and first_qa_id != "root":
                return self._registry[session_id][first_qa_id]
        
        logger.warning(f"Could not find root span for session in memory: {session_id}")
        return None
    
    def list_spans(self, session_id: str) -> Dict[str, str]:
        spans = {}
        
        # Try Redis first if available
        if self._redis_available and self._pool:
            try:
                import redis
                client = redis.Redis(connection_pool=self._pool)
                
                # Get all spans for session
                session_key = f"{self.key_prefix}{session_id}"
                all_spans = client.hgetall(session_key)
                
                if all_spans:
                    for k, v in all_spans.items():
                        key_str = k.decode('utf-8')
                        # Skip special keys
                        if not key_str.startswith("trace:"):
                            spans[key_str] = v.decode('utf-8')
            except Exception as e:
                logger.warning(f"Failed to list spans from Redis: {e}")
        
        # Merge with in-memory (Redis takes precedence)
        if session_id in self._registry:
            for qa_id, span_id in self._registry[session_id].items():
                if qa_id is not None and qa_id not in spans:
                    spans[qa_id] = span_id
        
        return spans


def create_span_registry():
    """Factory function to create the appropriate span registry based on environment"""
    environment = os.getenv("ENVIRONMENT", "development")
    # Prefer ATLAS_ENV if set, otherwise use ENVIRONMENT
    atlas_env = os.getenv("ATLAS_ENV", environment).lower()
    use_redis = os.getenv("USE_REDIS_FOR_TELEMETRY", "").lower() in ("true", "1", "yes")
    
    if (atlas_env in ("staging", "production")) or use_redis:
        # Use Redis in staging/production or if explicitly enabled
        redis_db = int(os.getenv("REDIS_TELEMETRY_DB", "1"))
        redis_url = os.getenv("REDIS_URL") # Allow full URL override
        return RedisSpanRegistry(redis_url=redis_url, db=redis_db)
    elif atlas_env == "development":
        # Use SQLite for development, with no fallback
        db_path = os.getenv("SQLITE_SPAN_REGISTRY_DB_PATH", "./telemetry_span_registry.db")
        logger.info(f"Using SQLite span registry for development at {db_path}")
        return SQLiteSpanRegistry(db_path=db_path)
    else:
        # For any other unspecified environment, raise an error
        error_msg = f"Unsupported environment: {atlas_env}. Must be 'development', 'staging', or 'production'."
        logger.error(error_msg)
        raise ValueError(error_msg)

# Create the global registry instance
span_registry = create_span_registry()
