"""
LLM Resource Manager for ATLAS.

This module provides resource management for LLM instances, including
concurrency control, memory cleanup, and response size limits.
"""

import asyncio
import gc
import logging
import os
import time
import weakref

logger = logging.getLogger(__name__)


class LLMResourceManager:
    """Manages LLM resources including concurrency, memory, and response limits."""

    def __init__(self):
        # Limit concurrent LLM requests to prevent memory exhaustion
        self.max_concurrent_requests = int(os.getenv("LLM_MAX_CONCURRENT", "10"))
        self.request_semaphore = asyncio.Semaphore(self.max_concurrent_requests)

        # Track active LLM instances for memory cleanup
        self.active_llm_instances = weakref.WeakSet()
        self.last_cleanup = time.time()
        self.cleanup_interval = 300  # 5 minutes

        # Response size limits
        self.max_response_tokens = int(os.getenv("LLM_MAX_RESPONSE_TOKENS", "4000"))
        self.max_response_chars = int(os.getenv("LLM_MAX_RESPONSE_CHARS", "32000"))

        logger.info(f"LLM Resource Manager initialized: max_concurrent={self.max_concurrent_requests}")

    async def acquire_llm_slot(self):
        """Acquire a slot for LLM processing"""
        await self.request_semaphore.acquire()

        # Periodic cleanup
        if time.time() - self.last_cleanup > self.cleanup_interval:
            self.cleanup_memory()

    def release_llm_slot(self):
        """Release a slot for LLM processing"""
        self.request_semaphore.release()

    def cleanup_memory(self):
        """Perform memory cleanup"""
        try:
            # Clean up LLM instances
            self._cleanup_llm_instances()

            # Clean up vector store connections
            self._cleanup_vector_stores()

            # Force garbage collection
            gc.collect()

            # Log active instances
            active_count = len(self.active_llm_instances)
            logger.info(f"LLM memory cleanup: {active_count} active instances")

            self.last_cleanup = time.time()

        except Exception as e:
            logger.error(f"Error during LLM memory cleanup: {e}")

    def _cleanup_llm_instances(self):
        """Clean up LLM instances that are no longer needed"""
        try:
            # Get list of current instances (weak references may be None)
            current_instances = [inst for inst in self.active_llm_instances if inst is not None]

            # Explicit cleanup for instances that support it
            for instance in current_instances:
                try:
                    # Check if instance has cleanup methods
                    if hasattr(instance, 'cleanup'):
                        instance.cleanup()
                    elif hasattr(instance, 'close'):
                        instance.close()
                    elif hasattr(instance, '__del__'):
                        # Let Python handle cleanup
                        pass
                except Exception as inst_error:
                    logger.debug(f"Error cleaning up LLM instance: {inst_error}")

            logger.debug(f"Cleaned up {len(current_instances)} LLM instances")

        except Exception as e:
            logger.error(f"Error during LLM instance cleanup: {e}")

    def _cleanup_vector_stores(self):
        """Clean up vector store connections"""
        try:
            from backend.modules.vector_store_manager import get_vector_store_manager
            vector_manager = get_vector_store_manager()

            # Clean up expired connections
            vector_manager._cleanup_expired_connections()

            logger.debug("Cleaned up vector store connections")

        except Exception as e:
            logger.debug(f"Error cleaning up vector stores: {e}")

    def register_llm_instance(self, llm_instance):
        """Register an LLM instance for tracking"""
        self.active_llm_instances.add(llm_instance)

        # Register cleanup callback if possible
        if hasattr(llm_instance, 'register_cleanup_callback'):
            llm_instance.register_cleanup_callback(self._instance_cleanup_callback)

    def _instance_cleanup_callback(self, instance):
        """Callback when an LLM instance is cleaned up"""
        logger.debug(f"LLM instance cleaned up: {type(instance).__name__}")

    def dispose_llm_instance(self, llm_instance):
        """Explicitly dispose of an LLM instance"""
        try:
            if hasattr(llm_instance, 'cleanup'):
                llm_instance.cleanup()
            elif hasattr(llm_instance, 'close'):
                llm_instance.close()

            # Remove from tracking
            self.active_llm_instances.discard(llm_instance)

            logger.debug(f"Disposed LLM instance: {type(llm_instance).__name__}")

        except Exception as e:
            logger.error(f"Error disposing LLM instance: {e}")

    def check_response_size(self, response_text: str) -> bool:
        """Check if response exceeds size limits"""
        if len(response_text) > self.max_response_chars:
            logger.warning(f"Response truncated: {len(response_text)} chars > {self.max_response_chars} limit")
            return False
        return True

    def truncate_response(self, response_text: str) -> str:
        """Truncate response to size limits"""
        if len(response_text) > self.max_response_chars:
            truncated = response_text[:self.max_response_chars]
            # Try to truncate at last complete sentence
            last_period = truncated.rfind('.')
            if last_period > self.max_response_chars * 0.8:  # If we can find a period in the last 20%
                truncated = truncated[:last_period + 1]
            return truncated + "\n\n[Response truncated due to length limits]"
        return response_text


# Singleton instance
llm_resource_manager = LLMResourceManager()
