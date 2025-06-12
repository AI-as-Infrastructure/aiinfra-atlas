"""
Provider-agnostic token counting utilities for Phoenix telemetry.

This module provides token counting functionality that works across different LLM providers
(OpenAI, Anthropic, Ollama, Bedrock, etc.) with appropriate fallbacks.
"""
import logging
from typing import Dict, Optional, Any, Union, Tuple
import re

logger = logging.getLogger(__name__)

# Token estimation constants (rough approximations)
AVG_CHARS_PER_TOKEN = 4  # Average characters per token across most tokenizers
AVG_WORDS_TO_TOKENS = 1.3  # Average word-to-token ratio


class TokenCounter:
    """Provider-agnostic token counting utility."""
    
    def __init__(self, provider: str = None):
        """
        Initialize token counter for specific provider.
        
        Args:
            provider: LLM provider name (openai, anthropic, ollama, etc.)
        """
        self.provider = (provider or "").upper()
        self._tiktoken_encoder = None
        
    def get_tiktoken_encoder(self):
        """Get tiktoken encoder for OpenAI-style estimation (lazy loading)."""
        if self._tiktoken_encoder is None:
            try:
                import tiktoken
                self._tiktoken_encoder = tiktoken.get_encoding("cl100k_base")  # GPT-4 encoding
                logger.debug("Loaded tiktoken encoder for token estimation")
            except ImportError:
                logger.warning("tiktoken not available - using character-based estimation")
                self._tiktoken_encoder = False
        return self._tiktoken_encoder if self._tiktoken_encoder is not False else None
    
    def extract_tokens_from_response(self, response: Any) -> Dict[str, int]:
        """
        Extract token counts from LLM response based on provider.
        
        Args:
            response: LLM response object (format varies by provider)
            
        Returns:
            Dict with prompt_tokens, completion_tokens, total_tokens (0 if not available)
        """
        tokens = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        
        try:
            if self.provider == "OPENAI":
                tokens.update(self._extract_openai_tokens(response))
            elif self.provider == "ANTHROPIC":
                tokens.update(self._extract_anthropic_tokens(response))
            elif self.provider == "OLLAMA":
                tokens.update(self._extract_ollama_tokens(response))
            else:
                # Try generic extraction for unknown providers
                tokens.update(self._extract_generic_tokens(response))
                
        except Exception as e:
            logger.warning(f"Failed to extract tokens from {self.provider} response: {e}")
            
        return tokens
    
    def _extract_openai_tokens(self, response: Any) -> Dict[str, int]:
        """Extract tokens from OpenAI response format."""
        tokens = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        
        # Handle streaming response with usage information
        if hasattr(response, 'usage') and response.usage:
            usage = response.usage
            tokens["prompt_tokens"] = getattr(usage, 'prompt_tokens', 0)
            tokens["completion_tokens"] = getattr(usage, 'completion_tokens', 0)
            tokens["total_tokens"] = getattr(usage, 'total_tokens', 0)
        
        # Handle dictionary format
        elif isinstance(response, dict):
            usage = response.get('usage', {})
            tokens["prompt_tokens"] = usage.get('prompt_tokens', 0)
            tokens["completion_tokens"] = usage.get('completion_tokens', 0)
            tokens["total_tokens"] = usage.get('total_tokens', 0)
            
        return tokens
    
    def _extract_anthropic_tokens(self, response: Any) -> Dict[str, int]:
        """Extract tokens from Anthropic response format."""
        tokens = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        
        # Anthropic uses different field names
        if hasattr(response, 'usage') and response.usage:
            usage = response.usage
            tokens["prompt_tokens"] = getattr(usage, 'input_tokens', 0)
            tokens["completion_tokens"] = getattr(usage, 'output_tokens', 0)
            tokens["total_tokens"] = tokens["prompt_tokens"] + tokens["completion_tokens"]
        
        elif isinstance(response, dict):
            usage = response.get('usage', {})
            tokens["prompt_tokens"] = usage.get('input_tokens', 0)
            tokens["completion_tokens"] = usage.get('output_tokens', 0)
            tokens["total_tokens"] = tokens["prompt_tokens"] + tokens["completion_tokens"]
            
        return tokens
    
    def _extract_ollama_tokens(self, response: Any) -> Dict[str, int]:
        """Extract tokens from Ollama response format."""
        tokens = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        
        # Ollama may provide token counts in different formats
        if hasattr(response, 'eval_count'):
            tokens["completion_tokens"] = getattr(response, 'eval_count', 0)
        if hasattr(response, 'prompt_eval_count'):
            tokens["prompt_tokens"] = getattr(response, 'prompt_eval_count', 0)
            
        elif isinstance(response, dict):
            tokens["prompt_tokens"] = response.get('prompt_eval_count', 0)
            tokens["completion_tokens"] = response.get('eval_count', 0)
            
        tokens["total_tokens"] = tokens["prompt_tokens"] + tokens["completion_tokens"]
        return tokens
    
    def _extract_generic_tokens(self, response: Any) -> Dict[str, int]:
        """Try to extract tokens from unknown provider format."""
        tokens = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        
        # Common field names to check
        token_fields = [
            ('prompt_tokens', ['prompt_tokens', 'input_tokens', 'prompt_eval_count']),
            ('completion_tokens', ['completion_tokens', 'output_tokens', 'eval_count']),
            ('total_tokens', ['total_tokens', 'total'])
        ]
        
        for token_type, field_names in token_fields:
            for field_name in field_names:
                # Check object attributes
                if hasattr(response, field_name):
                    tokens[token_type] = getattr(response, field_name, 0)
                    break
                # Check dictionary keys
                elif isinstance(response, dict) and field_name in response:
                    tokens[token_type] = response[field_name]
                    break
                # Check nested usage object
                elif hasattr(response, 'usage') and hasattr(response.usage, field_name):
                    tokens[token_type] = getattr(response.usage, field_name, 0)
                    break
                elif isinstance(response, dict) and 'usage' in response and field_name in response['usage']:
                    tokens[token_type] = response['usage'][field_name]
                    break
        
        # Calculate total if not provided
        if not tokens["total_tokens"] and (tokens["prompt_tokens"] or tokens["completion_tokens"]):
            tokens["total_tokens"] = tokens["prompt_tokens"] + tokens["completion_tokens"]
            
        return tokens
    
    def estimate_tokens(self, text: str, method: str = "tiktoken") -> int:
        """
        Estimate token count for text using various methods.
        
        Args:
            text: Text to count tokens for
            method: Estimation method ("tiktoken", "chars", "words")
            
        Returns:
            Estimated token count
        """
        if not text:
            return 0
            
        if method == "tiktoken":
            encoder = self.get_tiktoken_encoder()
            if encoder:
                try:
                    return len(encoder.encode(text))
                except Exception as e:
                    logger.warning(f"tiktoken encoding failed: {e}, falling back to character method")
                    
        if method == "chars" or method == "tiktoken":  # fallback from tiktoken
            return max(1, len(text) // AVG_CHARS_PER_TOKEN)
            
        elif method == "words":
            word_count = len(text.split())
            return max(1, int(word_count * AVG_WORDS_TO_TOKENS))
            
        else:
            logger.warning(f"Unknown estimation method '{method}', using character-based")
            return max(1, len(text) // AVG_CHARS_PER_TOKEN)
    
    def get_completion_tokens_from_streaming(self, full_response: str) -> int:
        """
        Estimate completion tokens from accumulated streaming response.
        
        Args:
            full_response: Complete response text from streaming
            
        Returns:
            Estimated completion token count
        """
        return self.estimate_tokens(full_response, method="tiktoken")
    
    def calculate_token_counts(self, 
                             prompt_text: str = None, 
                             completion_text: str = None,
                             response_obj: Any = None) -> Dict[str, int]:
        """
        Calculate token counts using best available method.
        
        Args:
            prompt_text: Prompt text for estimation
            completion_text: Completion text for estimation  
            response_obj: LLM response object for extraction
            
        Returns:
            Dict with prompt_tokens, completion_tokens, total_tokens
        """
        tokens = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        
        # First try to extract from response object
        if response_obj:
            extracted = self.extract_tokens_from_response(response_obj)
            if extracted["total_tokens"] > 0:  # Got actual counts
                return extracted
            else:
                tokens.update(extracted)  # May have partial counts
        
        # Estimate missing counts from text
        if prompt_text and tokens["prompt_tokens"] == 0:
            tokens["prompt_tokens"] = self.estimate_tokens(prompt_text)
            
        if completion_text and tokens["completion_tokens"] == 0:
            tokens["completion_tokens"] = self.estimate_tokens(completion_text)
            
        # Calculate total
        tokens["total_tokens"] = tokens["prompt_tokens"] + tokens["completion_tokens"]
        
        return tokens


def get_token_counter(provider: str = None) -> TokenCounter:
    """
    Get a token counter instance for the specified provider.
    
    Args:
        provider: LLM provider name
        
    Returns:
        TokenCounter instance
    """
    return TokenCounter(provider)


def add_token_counts_to_span(span: Any, 
                           prompt_text: str = None,
                           completion_text: str = None, 
                           response_obj: Any = None,
                           provider: str = None) -> None:
    """
    Add token count attributes to a telemetry span.
    
    Args:
        span: Telemetry span to add attributes to
        prompt_text: Prompt text for estimation
        completion_text: Completion text for estimation
        response_obj: LLM response object for extraction
        provider: LLM provider name
    """
    try:
        counter = get_token_counter(provider)
        tokens = counter.calculate_token_counts(prompt_text, completion_text, response_obj)
        
        # Add OpenInference standard token attributes
        from backend.telemetry.constants import SpanAttributes
        span.set_attribute(SpanAttributes.LLM_TOKEN_COUNT_PROMPT, tokens["prompt_tokens"])
        span.set_attribute(SpanAttributes.LLM_TOKEN_COUNT_COMPLETION, tokens["completion_tokens"])
        span.set_attribute(SpanAttributes.LLM_TOKEN_COUNT_TOTAL, tokens["total_tokens"])
        
        # Log for debugging
        logger.debug(f"Added token counts to span: {tokens} (provider: {provider})")
        
    except Exception as e:
        logger.warning(f"Failed to add token counts to span: {e}") 