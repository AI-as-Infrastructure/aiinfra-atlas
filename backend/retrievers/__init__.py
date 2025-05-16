"""
ATLAS Retrievers Package

This package contains different retriever implementations that can be used with ATLAS.
"""

import os
import importlib
import logging
import traceback
from typing import Dict, Any, Optional, Type

from .base_retriever import BaseRetriever

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_retriever(retriever_name: str = None, config: Dict[str, Any] = None) -> Optional[BaseRetriever]:
    """Load and instantiate a retriever by name.
    
    If no retriever_name is provided, it checks the RETRIEVER_MODULE environment variable.
    If that is not set, it defaults to 'hansard_retriever'.
    
    Args:
        retriever_name: The name of the retriever to load (without .py extension)
        config: Configuration dictionary to pass to the retriever
    
    Returns:
        An instantiated retriever object or None if loading fails
    """
    if retriever_name is None:
        # Check environment variable for retriever module
        retriever_name = os.environ.get('RETRIEVER_MODULE', 'hansard_retriever')
        
        # Handle module path format (modules.my_retriever -> my_retriever)
        if '.' in retriever_name:
            retriever_name = retriever_name.split('.')[-1]
    
    logger.info(f"Loading retriever: {retriever_name}")
    
    # Removed vestigial SelfQueryRetriever config injection block. Only dynamic import and instantiation logic remains.
    try:
        # Import the retriever module
        module_path = f"backend.retrievers.{retriever_name}"
        logger.info(f"Importing module: {module_path}")
        
        try:
            retriever_module = importlib.import_module(module_path)
            logger.info(f"Successfully imported module: {module_path}")
        except ImportError as e:
            logger.error(f"Failed to import retriever module '{module_path}': {e}")
            logger.error(traceback.format_exc())
            raise ValueError(f"Retriever module '{module_path}' could not be imported: {e}")
        
        # Find the retriever class in the module (should be the only class that extends BaseRetriever)
        retriever_class = None
        for attr_name in dir(retriever_module):
            attr = getattr(retriever_module, attr_name)
            try:
                if (isinstance(attr, type) and 
                    issubclass(attr, BaseRetriever) and 
                    attr is not BaseRetriever):
                    retriever_class = attr
                    logger.info(f"Found retriever class: {attr_name}")
                    break
            except TypeError:
                # This happens when checking issubclass on non-class objects
                continue
        
        if retriever_class is None:
            logger.error(f"No BaseRetriever implementation found in {module_path}")
            logger.error(f"Available attributes: {[a for a in dir(retriever_module) if not a.startswith('__')]}")
            raise ValueError(f"No BaseRetriever implementation found in {module_path}")
        
        # Create an instance with the provided config
        if config is None:
            config = {}
        
        logger.info(f"Instantiating retriever class: {retriever_class.__name__}")
        try:
            retriever_instance = retriever_class(config)
            logger.info(f"Successfully instantiated retriever: {retriever_class.__name__}")
            return retriever_instance
        except Exception as e:
            logger.error(f"Failed to instantiate retriever '{retriever_class.__name__}': {e}")
            logger.error(traceback.format_exc())
            raise ValueError(f"Retriever instantiation failed: {e}")
    
    except Exception as e:
        logger.error(f"Error loading retriever '{retriever_name}': {e}")
        logger.error(traceback.format_exc())
        return None

def get_available_retrievers():
    """Get a list of all available retriever implementations.
    
    Returns:
        A list of retriever names
    """
    return BaseRetriever.get_available_retrievers() 