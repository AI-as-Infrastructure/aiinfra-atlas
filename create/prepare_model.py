#!/usr/bin/env python3
"""Prepare embedding model for ATLAS.

This script downloads and prepares the embedding model for use with ATLAS.
It handles:
1. Downloading the base model
2. Converting to Sentence-Transformer format
3. Setting up the pooling strategy
4. Saving to the models directory

Usage:
    python create/prepare_model.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Ensure project root on path *before* any local package imports
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from create.prepare_embedding_model import ensure_st_model

def main():
    # Load environment variables
    env_candidates = [
        repo_root / "config" / ".env.development",
        repo_root / "config" / ".env.staging",
        repo_root / "config" / ".env.production",
    ]

    for _env in env_candidates:
        if _env.exists():
            print(f"Loading environment variables from: {_env}")
            load_dotenv(dotenv_path=_env, override=False)
            break
    else:
        print("[WARN] No .env.* file found under config/. Proceeding with current environment.")

    # Get model configuration
    embedding_model = os.getenv('EMBEDDING_MODEL', 'Livingwithmachines/bert_1890_1900')
    pooling = os.getenv('POOLING', 'mean').lower()
    
    print(f"Preparing embedding model: {embedding_model}")
    print(f"Using pooling strategy: {pooling}")

    # Create models directory if it doesn't exist
    models_dir = repo_root / "models"
    models_dir.mkdir(exist_ok=True)

    # Prepare the model
    model_output_dir = models_dir / f"{embedding_model.split('/')[-1]}_st"
    ensure_st_model(embedding_model, model_output_dir)

    print(f"\n✅ Model prepared successfully at: {model_output_dir}")
    print("\nNext steps:")
    print("1. The model is now ready for use with ATLAS")
    print("2. You can now clone the vector store without needing to recreate the model")
    print("3. The model will be used automatically by the retriever")

if __name__ == "__main__":
    main() 