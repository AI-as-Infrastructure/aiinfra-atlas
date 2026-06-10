"""
LLM creation and configuration utilities for ATLAS.

This module provides functions for creating and configuring Language Model instances.
For response generation with telemetry, see backend.modules.response.
"""

import logging
import os
from typing import List, Dict, Optional, Union

from langchain_core.documents.base import Document
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_community.chat_models import ChatOllama
from langchain_aws import ChatBedrock
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.prompts import PromptTemplate
from langchain_core.language_models.chat_models import BaseChatModel

from backend.modules.config import get_llm_config
from backend.modules.system_prompts import get_qa_prompt_template

logger = logging.getLogger(__name__)

def format_documents(documents: List[Document]) -> str:
    """
    Format documents as a string for inclusion in prompts.

    Args:
        documents: List of documents

    Returns:
        Formatted string representation of documents
    """
    formatted_docs = []
    for i, doc in enumerate(documents):
        # Extract metadata
        metadata = doc.metadata.copy() if hasattr(doc, 'metadata') else {}

        # Format metadata fields
        metadata_str = ", ".join(f"{k}: {v}" for k, v in metadata.items()
                               if k in ["date", "title", "source", "corpus", "page"])

        # Extract text content
        text = doc.page_content if hasattr(doc, 'page_content') else str(doc)

        # Format document
        formatted_docs.append(f"Document {i+1} [{metadata_str}]:\n{text}\n")

    return "\n".join(formatted_docs)

def format_chat_history(chat_history: List[Dict[str, str]]) -> List[Union[HumanMessage, AIMessage]]:
    """
    Format chat history as LangChain messages.

    Converts chat history from the application format to the format expected by LangChain.
    Works with all supported LLM providers (OpenAI, Anthropic, Ollama).

    Args:
        chat_history: List of chat history entries with 'role' and 'content' keys

    Returns:
        List of LangChain message objects
    """
    if not chat_history:
        return []

    messages = []
    for entry in chat_history:
        # Handle different formats of chat history
        if isinstance(entry, dict):
            role = entry.get("role", "")
            content = entry.get("content", "")

            # Map chat history roles to message types
            if role.lower() == "user" or role.lower() == "human":
                messages.append(HumanMessage(content=content))
            elif role.lower() == "assistant" or role.lower() == "ai":
                messages.append(AIMessage(content=content))
            elif role.lower() == "system":
                messages.append(SystemMessage(content=content))
        elif isinstance(entry, (HumanMessage, AIMessage, SystemMessage)):
            # If already a LangChain message, use it directly
            messages.append(entry)

    return messages

def create_llm(
    model_name: Optional[str] = None,
    provider: Optional[str] = None,
    temperature: float = 0.7,
    streaming: bool = True
) -> BaseChatModel:
    """
    Create an LLM instance for any supported provider.

    This function is the centralized implementation for creating LLM instances
    in the ATLAS system, supporting OpenAI, Anthropic, OpenRouter, Ollama, Bedrock, and Google providers.

    Args:
        model_name: Name of the model
        provider: LLM provider (openai, anthropic, openrouter, ollama, bedrock, google)
        temperature: Temperature for generation
        streaming: Whether to use streaming mode

    Returns:
        LLM instance of the appropriate type
    """
    # Get LLM configuration
    llm_config = get_llm_config()

    # Use provided values or fall back to config -- no silent defaults
    model = model_name or llm_config.get("model")
    provider = provider or llm_config.get("provider")

    if not provider:
        logger.error("LLM provider not configured. Set TEST_TARGET in .env to a valid target file, or set LLM_PROVIDER in the target file.")
        raise ValueError("LLM provider not configured. Contact administrator.")
    if not model:
        logger.error("LLM model not configured. Set TEST_TARGET in .env to a valid target file, or set LLM_MODEL in the target file.")
        raise ValueError("LLM model not configured. Contact administrator.")

    # Normalize provider name to uppercase
    provider = provider.upper()

    # Create LLM based on provider
    if provider == 'OLLAMA':
        ollama_endpoint = os.getenv("OLLAMA_ENDPOINT", "http://host.docker.internal:11434")
        logger.debug(f"Using Ollama endpoint: {ollama_endpoint}")
        return ChatOllama(
            model=model or "llama3.2",
            base_url=ollama_endpoint,
            temperature=temperature,
            streaming=streaming
        )
    elif provider == 'ANTHROPIC':
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        if not anthropic_api_key:
            logger.error("ANTHROPIC_API_KEY not found in environment - check environment variable loading")
            raise ValueError("LLM provider configuration error. Contact administrator.")

        logger.debug("Using Anthropic with API key")
        return ChatAnthropic(
            api_key=anthropic_api_key,
            model_name=model or "claude-3-5-sonnet-20240620",
            temperature=temperature,
            streaming=streaming
        )
    elif provider == 'OPENROUTER':
        openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        if not openrouter_api_key:
            logger.error("OPENROUTER_API_KEY not found in environment - check environment variable loading")
            raise ValueError("LLM provider configuration error. Contact administrator.")

        # OpenRouter is OpenAI-API-compatible; route through ChatOpenAI with its base URL.
        # Models use namespaced ids, e.g. "anthropic/claude-sonnet-4.6".
        logger.debug("Using OpenRouter with API key")
        return ChatOpenAI(
            api_key=openrouter_api_key,
            base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            model=model,
            temperature=temperature,
            streaming=streaming
        )
    elif provider == 'OPENAI':
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            logger.error("OPENAI_API_KEY not found in environment - check environment variable loading")
            raise ValueError("LLM provider configuration error. Contact administrator.")

        logger.debug("Using OpenAI with API key")
        return ChatOpenAI(
            api_key=openai_api_key,
            model=model or "gpt-4o",
            temperature=temperature,
            streaming=streaming
        )
    elif provider == 'BEDROCK':
        aws_region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

        logger.debug(f"Using AWS Bedrock in region {aws_region}")
        return ChatBedrock(
            model_id=model or "anthropic.claude-3-sonnet-20240229-v1:0",
            region_name=aws_region,
            model_kwargs={
                "temperature": temperature,
                "max_tokens": 4096
            },
            streaming=streaming
        )
    elif provider == 'GOOGLE':
        google_api_key = os.getenv("GOOGLE_API_KEY")
        if not google_api_key:
            logger.error("GOOGLE_API_KEY not found in environment - check environment variable loading")
            raise ValueError("LLM provider configuration error. Contact administrator.")

        logger.debug("Using Google Generative AI with API key")
        return ChatGoogleGenerativeAI(
            google_api_key=google_api_key,
            model=model or "gemini-1.5-pro",
            temperature=temperature
            # Note: streaming is enabled by default, no need to specify
        )
    else:
        logger.error(f"Unknown LLM provider '{provider}'. Supported: OLLAMA, ANTHROPIC, OPENROUTER, OPENAI, BEDROCK, GOOGLE.")
        raise ValueError("LLM provider configuration error. Contact administrator.")

def create_qa_prompt(
    system_prompt: Optional[str] = None,
    include_chat_history: bool = True
) -> PromptTemplate:
    """
    Create a prompt template for Q&A.

    Args:
        system_prompt: System prompt (overrides default if provided)
        include_chat_history: Whether to include chat history

    Returns:
        Prompt template
    """
    # If a custom system prompt is provided, create a template with it
    if system_prompt:
        # Create a template with the custom system prompt
        if include_chat_history:
            template = f"""
{system_prompt}

Context information is below.
{{context}}

Previous conversation:
{{chat_history}}

User question: {{question}}

Answer:"""

            return PromptTemplate(
                template=template,
                input_variables=["context", "chat_history", "question"]
            )
        else:
            template = f"""
{system_prompt}

Context information is below.
{{context}}

User question: {{question}}

Answer:"""

            return PromptTemplate(
                template=template,
                input_variables=["context", "question"]
            )
    else:
        # Use the standard template from system_prompts.py
        return get_qa_prompt_template(include_chat_history)
