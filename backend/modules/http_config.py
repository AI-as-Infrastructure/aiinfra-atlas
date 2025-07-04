"""
HTTP Client Configuration for LLM APIs

This module provides optimized HTTP client configurations for high-concurrency
LLM API usage, including connection pooling and timeout settings.
"""

import os
import httpx
import asyncio
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

# HTTP client configurations for different providers
HTTP_CLIENT_CONFIGS = {
    'openai': {
        'timeout': httpx.Timeout(60.0, connect=10.0),
        'limits': httpx.Limits(
            max_keepalive_connections=20,
            max_connections=100,
            keepalive_expiry=30.0
        ),
        'retries': 3,
    },
    'anthropic': {
        'timeout': httpx.Timeout(60.0, connect=10.0),
        'limits': httpx.Limits(
            max_keepalive_connections=20,
            max_connections=100,
            keepalive_expiry=30.0
        ),
        'retries': 3,
    },
    'default': {
        'timeout': httpx.Timeout(30.0, connect=5.0),
        'limits': httpx.Limits(
            max_keepalive_connections=10,
            max_connections=50,
            keepalive_expiry=30.0
        ),
        'retries': 2,
    }
}

class OptimizedHTTPClient:
    """
    Optimized HTTP client with connection pooling and retry logic.
    """
    
    def __init__(self, provider: str = 'default'):
        """
        Initialize optimized HTTP client.
        
        Args:
            provider: Provider name (openai, anthropic, default)
        """
        self.provider = provider
        self.config = HTTP_CLIENT_CONFIGS.get(provider, HTTP_CLIENT_CONFIGS['default'])
        self._client: Optional[httpx.AsyncClient] = None
        self._sync_client: Optional[httpx.Client] = None
    
    def get_sync_client(self) -> httpx.Client:
        """
        Get synchronous HTTP client with optimized settings.
        
        Returns:
            Configured httpx.Client instance
        """
        if self._sync_client is None:
            self._sync_client = httpx.Client(
                timeout=self.config['timeout'],
                limits=self.config['limits'],
                http2=True,  # Enable HTTP/2 for better performance
                verify=True,  # Always verify SSL certificates
            )
        return self._sync_client
    
    def get_async_client(self) -> httpx.AsyncClient:
        """
        Get asynchronous HTTP client with optimized settings.
        
        Returns:
            Configured httpx.AsyncClient instance
        """
        if self._async_client is None:
            self._async_client = httpx.AsyncClient(
                timeout=self.config['timeout'],
                limits=self.config['limits'],
                http2=True,  # Enable HTTP/2 for better performance
                verify=True,  # Always verify SSL certificates
            )
        return self._async_client
    
    async def close(self):
        """Close all HTTP clients."""
        if self._async_client:
            await self._async_client.aclose()
            self._async_client = None
        if self._sync_client:
            self._sync_client.close()
            self._sync_client = None
    
    def __enter__(self):
        return self.get_sync_client()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._sync_client:
            self._sync_client.close()
            self._sync_client = None
    
    async def __aenter__(self):
        return self.get_async_client()
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

# Global HTTP clients for different providers
_http_clients: Dict[str, OptimizedHTTPClient] = {}

def get_http_client(provider: str = 'default') -> OptimizedHTTPClient:
    """
    Get HTTP client for a specific provider.
    
    Args:
        provider: Provider name (openai, anthropic, default)
        
    Returns:
        OptimizedHTTPClient instance
    """
    if provider not in _http_clients:
        _http_clients[provider] = OptimizedHTTPClient(provider)
    return _http_clients[provider]

async def cleanup_http_clients():
    """
    Clean up all HTTP clients.
    """
    for client in _http_clients.values():
        await client.close()
    _http_clients.clear()

def configure_langchain_http_clients():
    """
    Configure LangChain HTTP clients with optimized settings.
    
    This function sets environment variables that LangChain uses
    for its internal HTTP client configuration.
    """
    # OpenAI configuration
    os.environ.setdefault('OPENAI_API_REQUEST_TIMEOUT', '60')
    os.environ.setdefault('OPENAI_API_MAX_RETRIES', '3')
    
    # Anthropic configuration  
    os.environ.setdefault('ANTHROPIC_API_REQUEST_TIMEOUT', '60')
    os.environ.setdefault('ANTHROPIC_API_MAX_RETRIES', '3')
    
    # General HTTP configuration
    os.environ.setdefault('HTTPX_LOG_LEVEL', 'WARNING')  # Reduce HTTP logging noise
    
    logger.info("Configured LangChain HTTP clients with optimized settings")

def get_provider_config(provider: str) -> Dict[str, Any]:
    """
    Get HTTP configuration for a specific provider.
    
    Args:
        provider: Provider name
        
    Returns:
        Configuration dictionary
    """
    return HTTP_CLIENT_CONFIGS.get(provider, HTTP_CLIENT_CONFIGS['default'])

def update_provider_config(provider: str, config_updates: Dict[str, Any]):
    """
    Update HTTP configuration for a specific provider.
    
    Args:
        provider: Provider name
        config_updates: Configuration updates to apply
    """
    if provider in HTTP_CLIENT_CONFIGS:
        HTTP_CLIENT_CONFIGS[provider].update(config_updates)
        logger.info(f"Updated HTTP config for provider {provider}: {config_updates}")
    else:
        logger.warning(f"Unknown provider {provider}, skipping config update")

# Initialize LangChain HTTP configuration on import
configure_langchain_http_clients()