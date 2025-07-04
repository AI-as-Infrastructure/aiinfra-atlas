"""
Rate Limiting and Backoff Strategies for LLM API Calls

This module provides rate limiting and exponential backoff functionality
to handle API rate limits gracefully and improve overall system resilience.
"""

import asyncio
import time
import random
import logging
from typing import Dict, Optional, Callable, Any
from functools import wraps
from collections import defaultdict
import threading

logger = logging.getLogger(__name__)

class RateLimiter:
    """
    Token bucket rate limiter for controlling API call frequency.
    """
    
    def __init__(self, max_tokens: int = 50, refill_rate: float = 10.0):
        """
        Initialize rate limiter.
        
        Args:
            max_tokens: Maximum number of tokens in the bucket
            refill_rate: Rate at which tokens are refilled (tokens per second)
        """
        self.max_tokens = max_tokens
        self.refill_rate = refill_rate
        self.tokens = max_tokens
        self.last_refill = time.time()
        self.lock = threading.Lock()
    
    def acquire(self, tokens: int = 1, timeout: Optional[float] = None) -> bool:
        """
        Acquire tokens from the bucket.
        
        Args:
            tokens: Number of tokens to acquire
            timeout: Maximum time to wait for tokens (None = no timeout)
            
        Returns:
            True if tokens acquired, False if timeout exceeded
        """
        start_time = time.time()
        
        while True:
            with self.lock:
                # Refill tokens based on elapsed time
                now = time.time()
                elapsed = now - self.last_refill
                self.tokens = min(self.max_tokens, self.tokens + elapsed * self.refill_rate)
                self.last_refill = now
                
                # Check if we have enough tokens
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return True
            
            # Check timeout
            if timeout and (time.time() - start_time) > timeout:
                return False
            
            # Wait before trying again
            time.sleep(0.01)  # 10ms sleep
    
    async def acquire_async(self, tokens: int = 1, timeout: Optional[float] = None) -> bool:
        """
        Async version of acquire.
        """
        start_time = time.time()
        
        while True:
            with self.lock:
                # Refill tokens based on elapsed time
                now = time.time()
                elapsed = now - self.last_refill
                self.tokens = min(self.max_tokens, self.tokens + elapsed * self.refill_rate)
                self.last_refill = now
                
                # Check if we have enough tokens
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return True
            
            # Check timeout
            if timeout and (time.time() - start_time) > timeout:
                return False
            
            # Wait before trying again
            await asyncio.sleep(0.01)  # 10ms sleep

class ExponentialBackoff:
    """
    Exponential backoff strategy for handling API failures.
    """
    
    def __init__(self, 
                 base_delay: float = 1.0,
                 max_delay: float = 60.0,
                 multiplier: float = 2.0,
                 jitter: bool = True):
        """
        Initialize exponential backoff.
        
        Args:
            base_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            multiplier: Backoff multiplier
            jitter: Whether to add random jitter
        """
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.multiplier = multiplier
        self.jitter = jitter
        self.attempt_count = 0
    
    def get_delay(self) -> float:
        """
        Get the delay for the current attempt.
        
        Returns:
            Delay in seconds
        """
        delay = self.base_delay * (self.multiplier ** self.attempt_count)
        delay = min(delay, self.max_delay)
        
        if self.jitter:
            # Add random jitter (±20%)
            jitter_range = delay * 0.2
            delay += random.uniform(-jitter_range, jitter_range)
        
        return max(0, delay)
    
    def increment(self):
        """Increment the attempt count."""
        self.attempt_count += 1
    
    def reset(self):
        """Reset the attempt count."""
        self.attempt_count = 0

# Global rate limiters for different providers
_rate_limiters: Dict[str, RateLimiter] = {
    'openai': RateLimiter(max_tokens=50, refill_rate=10.0),  # 10 req/s, burst to 50
    'anthropic': RateLimiter(max_tokens=40, refill_rate=8.0),  # 8 req/s, burst to 40
    'default': RateLimiter(max_tokens=30, refill_rate=5.0),   # 5 req/s, burst to 30
}

def get_rate_limiter(provider: str = 'default') -> RateLimiter:
    """
    Get rate limiter for a specific provider.
    
    Args:
        provider: Provider name (openai, anthropic, default)
        
    Returns:
        RateLimiter instance
    """
    return _rate_limiters.get(provider.lower(), _rate_limiters['default'])

def with_rate_limit(provider: str = 'default', tokens: int = 1, timeout: float = 30.0):
    """
    Decorator to apply rate limiting to a function.
    
    Args:
        provider: Provider name for rate limiting
        tokens: Number of tokens to acquire
        timeout: Maximum time to wait for tokens
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            limiter = get_rate_limiter(provider)
            if not limiter.acquire(tokens=tokens, timeout=timeout):
                raise Exception(f"Rate limit timeout exceeded for {provider}")
            return func(*args, **kwargs)
        return wrapper
    return decorator

def with_rate_limit_async(provider: str = 'default', tokens: int = 1, timeout: float = 30.0):
    """
    Async decorator to apply rate limiting to an async function.
    
    Args:
        provider: Provider name for rate limiting
        tokens: Number of tokens to acquire
        timeout: Maximum time to wait for tokens
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            limiter = get_rate_limiter(provider)
            if not await limiter.acquire_async(tokens=tokens, timeout=timeout):
                raise Exception(f"Rate limit timeout exceeded for {provider}")
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def with_exponential_backoff(max_retries: int = 3, 
                           base_delay: float = 1.0,
                           max_delay: float = 60.0,
                           exceptions: tuple = (Exception,)):
    """
    Decorator to apply exponential backoff retry logic.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exceptions: Tuple of exceptions to catch and retry
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            backoff = ExponentialBackoff(base_delay=base_delay, max_delay=max_delay)
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_retries:
                        logger.error(f"Max retries ({max_retries}) exceeded for {func.__name__}: {e}")
                        raise
                    
                    delay = backoff.get_delay()
                    logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}. Retrying in {delay:.2f}s")
                    time.sleep(delay)
                    backoff.increment()
            
            return None  # Should never reach here
        return wrapper
    return decorator

def with_exponential_backoff_async(max_retries: int = 3,
                                 base_delay: float = 1.0,
                                 max_delay: float = 60.0,
                                 exceptions: tuple = (Exception,)):
    """
    Async decorator to apply exponential backoff retry logic.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exceptions: Tuple of exceptions to catch and retry
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            backoff = ExponentialBackoff(base_delay=base_delay, max_delay=max_delay)
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_retries:
                        logger.error(f"Max retries ({max_retries}) exceeded for {func.__name__}: {e}")
                        raise
                    
                    delay = backoff.get_delay()
                    logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}. Retrying in {delay:.2f}s")
                    await asyncio.sleep(delay)
                    backoff.increment()
            
            return None  # Should never reach here
        return wrapper
    return decorator

# Convenience functions for common use cases
def rate_limit_openai_call(func: Callable, *args, **kwargs) -> Any:
    """
    Apply OpenAI rate limiting to a function call.
    """
    limiter = get_rate_limiter('openai')
    if not limiter.acquire(timeout=30.0):
        raise Exception("OpenAI rate limit timeout exceeded")
    return func(*args, **kwargs)

def rate_limit_anthropic_call(func: Callable, *args, **kwargs) -> Any:
    """
    Apply Anthropic rate limiting to a function call.
    """
    limiter = get_rate_limiter('anthropic')
    if not limiter.acquire(timeout=30.0):
        raise Exception("Anthropic rate limit timeout exceeded")
    return func(*args, **kwargs)

async def rate_limit_openai_call_async(func: Callable, *args, **kwargs) -> Any:
    """
    Apply OpenAI rate limiting to an async function call.
    """
    limiter = get_rate_limiter('openai')
    if not await limiter.acquire_async(timeout=30.0):
        raise Exception("OpenAI rate limit timeout exceeded")
    return await func(*args, **kwargs)

async def rate_limit_anthropic_call_async(func: Callable, *args, **kwargs) -> Any:
    """
    Apply Anthropic rate limiting to an async function call.
    """
    limiter = get_rate_limiter('anthropic')
    if not await limiter.acquire_async(timeout=30.0):
        raise Exception("Anthropic rate limit timeout exceeded")
    return await func(*args, **kwargs)