# ---- BASE TARGET CLASS ----
# This file loads configuration from environment variables and .txt files.
# All config is determined by .env,and the .txt files matching the REDIS_DUMP basename or test target definition.

"""
Base configuration module for ATLAS test targets.

This module contains shared functionality and base classes used by all test targets,
reducing duplication and improving maintainability.
"""

import os
import inspect
import logging
import importlib
from typing import Dict, Any, Optional

# Import utilities but not model providers - they're now in backend.modules.llm
from langchain_community.vectorstores import Redis, Chroma
from langchain_core.runnables import RunnablePassthrough
from langchain_huggingface import HuggingFaceEmbeddings

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# DEBUG: Log the Chroma configuration at startup
logger.info(f"[DEBUG] CHROMA_PERSIST_DIRECTORY seen by backend: {os.getenv('CHROMA_PERSIST_DIRECTORY')}")
logger.info(f"[DEBUG] CHROMA_COLLECTION_NAME seen by backend: {os.getenv('CHROMA_COLLECTION_NAME')}")

# ---- UNIFIED TARGET CONFIGURATION ----
class TargetConfig:
    # ... existing code ...
    def get_exportable_config(self):
        """
        Returns a dictionary of configuration fields relevant for UI display, telemetry, and export.
        """
        export_fields = [
            "ATLAS_VERSION", "target_version", "target_id", "llm_provider", "llm_model",
            "vector_database", "chroma_collection", "composite_target", "embedding_model", "large_retrieval_size",
            "algorithm", "search_type", "search_k", "search_score_threshold", "chunk_size",
            "chunk_overlap", "citation_limit", "system_prompt"
        ]
        full_cfg = self.get_full_config()
        export_cfg = {k: full_cfg.get(k) for k in export_fields if k in full_cfg}
        # Optionally, add the system prompt if available elsewhere
        try:
            from backend.modules.system_prompts import system_prompt
            export_cfg["system_prompt"] = system_prompt
        except Exception:
            pass
        return export_cfg

    """
    Unified configuration manager for ATLAS targets.
    Loads all configuration (test target, Redis, LLM, search params) from .env and .txt files.
    """
    def __init__(self):
        # Load environment variables
        self.env = self._load_env_vars()
        self._debug_log_env()

        # Load Chroma config from .env and .txt
        self.chroma_config = self._load_redis_config()

        # Load test target config from .txt
        self.target_config = self._load_target_config()

        # Compose composite target id
        self.composite_target = f"{self.env['TEST_TARGET']}_{self.chroma_config['CHROMA_COLLECTION_NAME']}"

    def _load_env_vars(self):
        # Required environment variables
        env_vars = {
            'TEST_TARGET': os.getenv('TEST_TARGET'),
            'CHROMA_PERSIST_DIRECTORY': os.getenv('CHROMA_PERSIST_DIRECTORY'),
            'CHROMA_COLLECTION_NAME': os.getenv('CHROMA_COLLECTION_NAME', 'blert_1000'),
            'LLM_PROVIDER': os.getenv('LLM_PROVIDER', 'OLLAMA'),
            'LLM_MODEL': os.getenv('LLM_MODEL'),
            'ATLAS_VERSION': os.getenv('ATLAS_VERSION', '1.0.0')
        }
        for k, v in env_vars.items():
            if v is None:
                logger.warning(f"[TargetConfig] Environment variable {k} is not set.")
        return env_vars

    def _debug_log_env(self):
        logger.info(f"[TargetConfig] Loaded environment: {self.env}")

    def _load_redis_config(self):
        # Get Chroma configuration from environment variables
        chroma_collection = self.env.get('CHROMA_COLLECTION_NAME', 'blert_1000')
        chroma_persist_dir = self.env.get('CHROMA_PERSIST_DIRECTORY')
        
        if not chroma_persist_dir:
            logger.error("CHROMA_PERSIST_DIRECTORY environment variable is not set")
            raise ValueError("CHROMA_PERSIST_DIRECTORY environment variable is not set")
        
        # Look for a .txt configuration file with the same name as the collection
        config_file = os.path.join('backend/targets', f"{chroma_collection}.txt")
        
        # Default configuration values
        config_values = {
            "INDEX_NAME": chroma_collection,
            "ALGORITHM": "HNSW",  # Chroma's default algorithm
            "SEARCH_TYPE": "similarity",  # Always use similarity search for stable results
            "CHUNK_SIZE": "1000",
            "CHUNK_OVERLAP": "100",
            "EMBEDDING_MODEL": "Livingwithmachines/bert_1890_1900"  # Default embedding model
        }
        
        # Load configuration from file if it exists
        if os.path.isfile(config_file):
            logger.info(f"[TargetConfig] Found Chroma config file: {config_file}")
            try:
                with open(config_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = [x.strip() for x in line.split('=', 1)]
                            if key in config_values:
                                config_values[key] = value.strip('"').strip("'")
                                logger.info(f"[TargetConfig] Loaded Chroma config: {key}={config_values[key]}")
            except Exception as e:
                logger.error(f"[TargetConfig] Error reading Chroma config {config_file}: {e}")
        else:
            logger.warning(f"[TargetConfig] No Chroma config file found at {config_file}. Using defaults.")
        
        return {
            "CHROMA_PERSIST_DIRECTORY": chroma_persist_dir,
            "CHROMA_COLLECTION_NAME": chroma_collection,
            "VECTOR_DATABASE": chroma_collection,
            **config_values
        }

    def _load_target_config(self):
        test_target = self.env['TEST_TARGET']
        # Try to find a .txt file for the test target
        possible_files = [
            os.path.join('backend/targets', f"{test_target}.txt"),
            os.path.join('backend/targets', f"{test_target.lower()}.txt")
        ]
        config = {
            "SEARCH_TYPE": "similarity_score_threshold",
            "SEARCH_K": 15,
            "SEARCH_SCORE_THRESHOLD": 0.0,
            "CITATION_LIMIT": 10,
            "TARGET_VERSION": "1.0",
            "LARGE_RETRIEVAL_SIZE": 500,
            "LLM_PROVIDER": self.env.get('LLM_PROVIDER'),
            "LLM_MODEL": self.env.get('LLM_MODEL'),
        }
        found = False
        for file in possible_files:
            if os.path.isfile(file):
                logger.info(f"[TargetConfig] Found test target config: {file}")
                found = True
                try:
                    with open(file, 'r') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#') and '=' in line:
                                key, value = [x.strip() for x in line.split('=', 1)]
                                config[key] = value.strip('"').strip("'")
                                logger.info(f"[TargetConfig] Loaded target config: {key}={config[key]}")
                except Exception as e:
                    logger.error(f"[TargetConfig] Error reading target config {file}: {e}")
                break
        if not found:
            logger.warning(f"[TargetConfig] No test target config file found for {test_target}. Using defaults.")
        return config

    def get_full_config(self):
        """
        Return the unified configuration as a dictionary for API, telemetry, retriever, etc.
        """
        # Always use similarity search for stable corpus filtering
        search_type = "similarity"
        
        cfg = {
            # Target metadata
            "target_id": self.env['TEST_TARGET'],
            "composite_target": self.composite_target,
            "target_version": self.target_config.get("TARGET_VERSION", "1.0"),
            # Search configuration
            "search_type": search_type,  
            "search_k": int(self.target_config.get("SEARCH_K", 15)),
            "search_score_threshold": float(self.target_config.get("SEARCH_SCORE_THRESHOLD", 0.0)),
            "citation_limit": int(self.target_config.get("CITATION_LIMIT", 10)),
            # Vector store config
            "vector_database": self.chroma_config["VECTOR_DATABASE"],
            "chroma_collection": self.chroma_config["CHROMA_COLLECTION_NAME"],
            "chroma_persist_directory": self.chroma_config["CHROMA_PERSIST_DIRECTORY"],
            "index_name": self.chroma_config["INDEX_NAME"],
            "algorithm": self.chroma_config["ALGORITHM"],
            "chunk_size": self.chroma_config["CHUNK_SIZE"],
            "chunk_overlap": self.chroma_config["CHUNK_OVERLAP"],
            "embedding_model": self.chroma_config["EMBEDDING_MODEL"],
            "large_retrieval_size": int(self.target_config.get("LARGE_RETRIEVAL_SIZE", 500)),
            # LLM config
            "llm_provider": self.target_config.get("LLM_PROVIDER", self.env.get("LLM_PROVIDER")),
            "llm_model": self.target_config.get("LLM_MODEL", self.env.get("LLM_MODEL")),
        }
        logger.info(f"[TargetConfig] Final unified config: {cfg}")
        return cfg




