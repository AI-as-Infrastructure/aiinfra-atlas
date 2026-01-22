"""
Embedding model setup and preparation.

This module handles downloading and converting HuggingFace models
to Sentence-Transformer format for use with the vector store.
"""

import os
import logging
import shutil
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


def ensure_st_model(repo: str, output_dir: Path) -> Dict[str, Any]:
    """
    Ensure a HuggingFace model is available in Sentence-Transformers format.

    If the target directory already contains modules.json, the function
    is a no-op (model already prepared).

    Args:
        repo: HuggingFace repository name or local path
        output_dir: Destination directory for ST model

    Returns:
        Dictionary with preparation results
    """
    output_dir = output_dir.expanduser().resolve()
    result = {
        "success": False,
        "model_path": str(output_dir),
        "source": repo,
        "action": None,
        "message": None
    }

    try:
        # If 'repo' itself is a local directory that already looks like an ST model
        # (i.e. contains modules.json) we can simply use it and skip wrapping.
        repo_path = Path(repo).expanduser()
        if repo_path.is_dir() and (repo_path / "modules.json").exists():
            logger.info(f"Using existing local Sentence-Transformer model: {repo_path}")
            result["action"] = "local_copy"

            # Mirror/soft-copy into output_dir so downstream code has uniform path
            if output_dir != repo_path:
                output_dir.mkdir(parents=True, exist_ok=True)
                for item in repo_path.iterdir():
                    target = output_dir / item.name
                    if not target.exists():
                        if item.is_file():
                            shutil.copy(item, target)
                        else:
                            shutil.copytree(item, target)

            result["success"] = True
            result["message"] = f"Used existing local ST model from {repo_path}"
            return result

        # If we've already prepared this repo previously, skip
        if (output_dir / "modules.json").exists():
            logger.info(f"ST model already present: {output_dir}")
            result["success"] = True
            result["action"] = "already_exists"
            result["message"] = f"Model already prepared at {output_dir}"
            return result

        output_dir.mkdir(parents=True, exist_ok=True)

        # Import here to avoid dependency issues when not needed
        from sentence_transformers import SentenceTransformer

        logger.info(f"Preparing {repo} → {output_dir}")
        result["action"] = "download_convert"

        # SentenceTransformer() will either load an existing ST model or,
        # if the repo is a plain HF encoder, wrap it with a mean-pooling head
        st_model = SentenceTransformer(repo)
        st_model.save(str(output_dir))

        result["success"] = True
        result["message"] = f"Successfully prepared model from {repo}"
        logger.info(result["message"])

    except ImportError as e:
        result["message"] = "sentence-transformers not installed. Run: pip install sentence-transformers"
        logger.error(result["message"])
        raise

    except Exception as e:
        result["message"] = f"Failed to prepare model: {str(e)}"
        logger.error(result["message"])
        raise

    return result


def prepare_embedding_model(
    model_name: Optional[str] = None,
    models_dir: Optional[str] = None
) -> Dict[str, Any]:
    """
    Prepare embedding model using environment configuration.

    This is a higher-level wrapper that loads configuration from
    environment variables if not provided.

    Args:
        model_name: HuggingFace model name (default: from EMBEDDING_MODEL env var)
        models_dir: Directory to store models (default: ./models)

    Returns:
        Dictionary with preparation results
    """
    # Load from environment if not provided
    if model_name is None:
        model_name = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-mpnet-base-v2")

    if models_dir is None:
        models_dir = os.getenv("MODELS_DIR", "./models")

    models_path = Path(models_dir)
    model_path = models_path / model_name.replace("/", "_")

    logger.info(f"Preparing embedding model: {model_name}")
    logger.info(f"Model directory: {model_path}")

    return ensure_st_model(model_name, model_path)


def validate_embedding_model(model_id: str) -> Dict[str, Any]:
    """
    Validate that a HuggingFace model exists and is compatible.

    Args:
        model_id: HuggingFace model ID to validate

    Returns:
        Dictionary with validation results
    """
    import requests

    validation = {
        "valid": False,
        "exists": False,
        "is_sentence_transformer": False,
        "model_info": {},
        "error": None,
        "warning": None
    }

    # Clean model ID
    model_id = model_id.strip()

    # Check if model exists on HuggingFace
    try:
        response = requests.head(
            f"https://huggingface.co/{model_id}/resolve/main/config.json",
            timeout=5
        )

        if response.status_code == 404:
            validation["error"] = f"Model '{model_id}' not found on HuggingFace"
            return validation

        validation["exists"] = True

        # Get model information
        response = requests.get(
            f"https://huggingface.co/api/models/{model_id}",
            timeout=5
        )

        if response.status_code == 200:
            model_info = response.json()
            validation["model_info"] = {
                "id": model_id,
                "pipeline_tag": model_info.get("pipeline_tag", "unknown"),
                "downloads": model_info.get("downloads", 0),
                "likes": model_info.get("likes", 0),
                "library_name": model_info.get("library_name", ""),
                "tags": model_info.get("tags", [])
            }

            # Check for sentence-transformers compatibility
            libraries = model_info.get("library_name", "")
            tags = model_info.get("tags", [])

            validation["is_sentence_transformer"] = (
                "sentence-transformers" in libraries or
                "sentence-transformers" in tags or
                "sentence-similarity" in tags
            )

            if not validation["is_sentence_transformer"]:
                validation["warning"] = (
                    "This model may not be optimized for embeddings. "
                    "Consider using a sentence-transformers model."
                )

        validation["valid"] = True

    except requests.Timeout:
        validation["error"] = "Timeout while connecting to HuggingFace"
    except requests.RequestException as e:
        validation["error"] = f"Error connecting to HuggingFace: {str(e)}"
    except Exception as e:
        validation["error"] = f"Unexpected error: {str(e)}"

    return validation


def get_model_characteristics(model_path: str) -> Dict[str, Any]:
    """
    Get characteristics of a prepared embedding model.

    Args:
        model_path: Path to the prepared model

    Returns:
        Dictionary with model characteristics
    """
    from sentence_transformers import SentenceTransformer

    characteristics = {
        "embedding_dim": None,
        "max_sequence_length": None,
        "model_size_mb": None,
        "pooling_mode": None
    }

    try:
        model_path = Path(model_path)

        # Calculate model size
        if model_path.exists():
            total_size = sum(
                f.stat().st_size for f in model_path.rglob("*") if f.is_file()
            )
            characteristics["model_size_mb"] = round(total_size / (1024 * 1024), 1)

        # Load model to get characteristics
        model = SentenceTransformer(str(model_path))

        # Get embedding dimension
        test_embedding = model.encode(["test"], show_progress_bar=False)
        characteristics["embedding_dim"] = test_embedding.shape[1]

        # Get max sequence length
        characteristics["max_sequence_length"] = model.max_seq_length

        # Get pooling mode if available
        if hasattr(model, '_modules'):
            for module_name, module in model._modules.items():
                if 'pooling' in module_name.lower():
                    if hasattr(module, 'pooling_mode_mean_tokens'):
                        modes = []
                        if module.pooling_mode_mean_tokens:
                            modes.append("mean")
                        if module.pooling_mode_max_tokens:
                            modes.append("max")
                        if module.pooling_mode_cls_token:
                            modes.append("cls")
                        characteristics["pooling_mode"] = "+".join(modes) if modes else "unknown"

    except Exception as e:
        logger.warning(f"Could not get model characteristics: {e}")

    return characteristics


def cleanup_model_cache(models_dir: str = "./models", keep_models: Optional[list] = None):
    """
    Clean up unused models from the cache directory.

    Args:
        models_dir: Directory containing cached models
        keep_models: List of model names to keep (default: keep all)
    """
    models_path = Path(models_dir)

    if not models_path.exists():
        return

    if keep_models is None:
        keep_models = []

    # Convert model names to directory names
    keep_dirs = {model.replace("/", "_") for model in keep_models}

    removed = []
    for model_dir in models_path.iterdir():
        if model_dir.is_dir() and model_dir.name not in keep_dirs:
            try:
                shutil.rmtree(model_dir)
                removed.append(model_dir.name)
                logger.info(f"Removed cached model: {model_dir.name}")
            except Exception as e:
                logger.warning(f"Could not remove {model_dir.name}: {e}")

    if removed:
        logger.info(f"Cleaned up {len(removed)} unused models")
    else:
        logger.info("No unused models to clean up")