"""
Universal prompt caching for all LLM providers.

This module implements application-level prompt caching that works across
all supported providers (OpenAI, Anthropic, Google, Ollama, Bedrock).
"""

import hashlib
import json
import logging
import os
import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    """Represents a cached prompt entry."""
    prompt_hash: str
    system_prompt: str
    context: str
    created_at: datetime
    last_used: datetime
    hit_count: int
    ttl_minutes: int

class UniversalPromptCache:
    """
    Universal prompt cache that works with all LLM providers.
    
    This provides application-level caching by storing and reusing
    formatted prompts and context, reducing redundant processing
    and token usage across all providers.
    """
    
    def __init__(self):
        self.cache: Dict[str, CacheEntry] = {}
        self.enabled = os.getenv("PROMPT_CACHING_ENABLED", "true").lower() in ["true", "1", "yes"]
        self.cache_system = os.getenv("PROMPT_CACHE_SYSTEM", "true").lower() in ["true", "1", "yes"]
        self.cache_context = os.getenv("PROMPT_CACHE_CONTEXT", "true").lower() in ["true", "1", "yes"]
        
        # Parse TTL (default 5 minutes)
        ttl_str = os.getenv("PROMPT_CACHE_TTL", "5m")
        if ttl_str.endswith("m"):
            self.default_ttl_minutes = int(ttl_str[:-1])
        elif ttl_str.endswith("h"):
            self.default_ttl_minutes = int(ttl_str[:-1]) * 60
        else:
            self.default_ttl_minutes = 5
            
        logger.info(f"Universal prompt cache initialized: enabled={self.enabled}, "
                   f"system={self.cache_system}, context={self.cache_context}, "
                   f"ttl={self.default_ttl_minutes}m")

    def _create_cache_key(self, system_prompt: str, context: str = "", 
                         provider: str = "", model: str = "") -> str:
        """Create a hash-based cache key from prompt components."""
        # Include provider and model in key to avoid cross-provider issues
        cache_data = {
            "system_prompt": system_prompt if self.cache_system else "",
            "context": context if self.cache_context else "",
            "provider": provider.lower(),
            "model": model.lower()
        }
        
        cache_string = json.dumps(cache_data, sort_keys=True)
        return hashlib.sha256(cache_string.encode()).hexdigest()[:16]

    def _is_expired(self, entry: CacheEntry) -> bool:
        """Check if a cache entry has expired."""
        expiry_time = entry.last_used + timedelta(minutes=entry.ttl_minutes)
        return datetime.now() > expiry_time

    def _cleanup_expired(self):
        """Remove expired entries from cache."""
        expired_keys = [
            key for key, entry in self.cache.items() 
            if self._is_expired(entry)
        ]
        
        for key in expired_keys:
            del self.cache[key]
            
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        self._cleanup_expired()
        
        total_entries = len(self.cache)
        total_hits = sum(entry.hit_count for entry in self.cache.values())
        
        return {
            "enabled": self.enabled,
            "cache_system": self.cache_system,
            "cache_context": self.cache_context,
            "total_entries": total_entries,
            "total_hits": total_hits,
            "ttl_minutes": self.default_ttl_minutes
        }

    def get_cached_prompt(self, system_prompt: str, context: str = "",
                         provider: str = "", model: str = "") -> Optional[Tuple[str, Dict[str, Any]]]:
        """
        Get cached prompt if available.
        
        Args:
            system_prompt: System prompt text
            context: Document context
            provider: LLM provider name
            model: Model name
            
        Returns:
            Tuple of (formatted_prompt, cache_info) if cache hit, None if miss
        """
        if not self.enabled:
            return None
            
        cache_key = self._create_cache_key(system_prompt, context, provider, model)
        
        # Clean up expired entries
        self._cleanup_expired()
        
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            
            if not self._is_expired(entry):
                # Cache hit - update usage stats
                entry.last_used = datetime.now()
                entry.hit_count += 1
                
                # Build formatted prompt
                formatted_prompt = self._build_formatted_prompt(
                    entry.system_prompt, entry.context
                )
                
                cache_info = {
                    "cache_hit": True,
                    "hit_count": entry.hit_count,
                    "created_at": entry.created_at,
                    "last_used": entry.last_used,
                    "prompt_length": len(formatted_prompt),
                    "system_length": len(entry.system_prompt),
                    "context_length": len(entry.context)
                }
                
                logger.debug(f"Cache hit for key {cache_key[:8]}... "
                           f"(hit #{entry.hit_count})")
                
                return formatted_prompt, cache_info
            else:
                # Expired entry
                del self.cache[cache_key]
                
        return None

    def cache_prompt(self, system_prompt: str, context: str = "",
                    provider: str = "", model: str = "", 
                    ttl_minutes: Optional[int] = None) -> str:
        """
        Cache a prompt and return the cache key.
        
        Args:
            system_prompt: System prompt text
            context: Document context
            provider: LLM provider name
            model: Model name
            ttl_minutes: Custom TTL (defaults to configured TTL)
            
        Returns:
            Cache key for the stored prompt
        """
        if not self.enabled:
            return ""
            
        cache_key = self._create_cache_key(system_prompt, context, provider, model)
        ttl = ttl_minutes or self.default_ttl_minutes
        
        # Store in cache
        entry = CacheEntry(
            prompt_hash=cache_key,
            system_prompt=system_prompt if self.cache_system else "",
            context=context if self.cache_context else "",
            created_at=datetime.now(),
            last_used=datetime.now(),
            hit_count=0,
            ttl_minutes=ttl
        )
        
        self.cache[cache_key] = entry
        
        logger.debug(f"Cached prompt with key {cache_key[:8]}... "
                   f"(system: {len(system_prompt)} chars, "
                   f"context: {len(context)} chars, ttl: {ttl}m)")
        
        return cache_key

    def _build_formatted_prompt(self, system_prompt: str, context: str) -> str:
        """Build formatted prompt from cached components."""
        if context:
            return f"{system_prompt}\n\nContext information is below.\n{context}\n\n"
        else:
            return system_prompt

    def build_optimized_prompt(self, system_prompt: str, context: str = "",
                              provider: str = "", model: str = "") -> Tuple[str, Dict[str, Any]]:
        """
        Build an optimized prompt using cache when possible.
        
        This is the main method to use for all LLM providers.
        
        Args:
            system_prompt: System prompt text
            context: Document context  
            provider: LLM provider name
            model: Model name
            
        Returns:
            Tuple of (formatted_prompt, optimization_info)
        """
        # Try to get from cache first
        cached_result = self.get_cached_prompt(system_prompt, context, provider, model)
        
        if cached_result:
            formatted_prompt, cache_info = cached_result
            optimization_info = {
                **cache_info,
                "optimization": "cache_hit",
                "token_savings_estimated": len(formatted_prompt) // 4  # Rough token estimate
            }
            return formatted_prompt, optimization_info
        
        # Cache miss - build new prompt and cache it
        formatted_prompt = self._build_formatted_prompt(system_prompt, context)
        cache_key = self.cache_prompt(system_prompt, context, provider, model)
        
        optimization_info = {
            "cache_hit": False,
            "cache_key": cache_key,
            "optimization": "cached_for_future",
            "prompt_length": len(formatted_prompt),
            "system_length": len(system_prompt),
            "context_length": len(context)
        }
        
        return formatted_prompt, optimization_info

    def invalidate_cache(self, pattern: Optional[str] = None):
        """
        Invalidate cache entries.
        
        Args:
            pattern: If provided, only invalidate entries matching this pattern.
                    If None, clear entire cache.
        """
        if pattern:
            keys_to_remove = [
                key for key in self.cache.keys() 
                if pattern in key
            ]
            for key in keys_to_remove:
                del self.cache[key]
            logger.info(f"Invalidated {len(keys_to_remove)} cache entries matching '{pattern}'")
        else:
            cache_size = len(self.cache)
            self.cache.clear()
            logger.info(f"Cleared entire cache ({cache_size} entries)")

# Global cache instance
_prompt_cache = None

def get_prompt_cache() -> UniversalPromptCache:
    """Get the global prompt cache instance."""
    global _prompt_cache
    if _prompt_cache is None:
        _prompt_cache = UniversalPromptCache()
    return _prompt_cache

def optimize_prompt_for_provider(system_prompt: str, context: str = "",
                               provider: str = "", model: str = "") -> Tuple[str, Dict[str, Any]]:
    """
    Optimize prompt for any LLM provider using universal caching.
    
    This is the main function to use from other modules.
    
    Args:
        system_prompt: System prompt text
        context: Document context
        provider: LLM provider name
        model: Model name
        
    Returns:
        Tuple of (optimized_prompt, optimization_info)
    """
    cache = get_prompt_cache()
    return cache.build_optimized_prompt(system_prompt, context, provider, model)

def get_cache_statistics() -> Dict[str, Any]:
    """Get prompt cache statistics."""
    cache = get_prompt_cache()
    return cache.get_cache_stats()

def clear_prompt_cache(pattern: Optional[str] = None):
    """Clear prompt cache."""
    cache = get_prompt_cache()
    cache.invalidate_cache(pattern)