#!/usr/bin/env python3
"""Prepare (download & convert) embedding model for vector store.

Ensures that a HuggingFace model is available in Sentence-Transformers
format.  If the target directory already contains `modules.json` the script
is a no-op.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def ensure_st_model(repo: str, output_dir: Path) -> None:
    output_dir = output_dir.expanduser().resolve()

    # If 'repo' itself is a local directory that already looks like an ST model
    # (i.e. contains modules.json) we can simply use it and skip wrapping.
    repo_path = Path(repo).expanduser()
    if repo_path.is_dir() and (repo_path / "modules.json").exists():
        print(f"✅ Using existing local Sentence-Transformer model: {repo_path}")
        # Mirror/soft-copy into output_dir so downstream code has uniform path
        if output_dir != repo_path:
            output_dir.mkdir(parents=True, exist_ok=True)
            for item in repo_path.iterdir():
                target = output_dir / item.name
                if not target.exists():
                    if item.is_file():
                        import shutil; shutil.copy(item, target)
                    else:
                        import shutil; shutil.copytree(item, target)
        return

    # If we've already prepared this repo previously, skip
    if (output_dir / "modules.json").exists():
        print(f"✅ ST model already present: {output_dir}")
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    # Simple one-liner: SentenceTransformer() will either load an existing
    # ST model or, if the repo is a plain HF encoder, wrap it with a
    # mean-pooling head automatically.
    from sentence_transformers import SentenceTransformer

    print("📥 Preparing", repo, "→", output_dir)
    st_model = SentenceTransformer(repo)
    st_model.save(str(output_dir))

    _ensure_gitattributes()
    return


def _ensure_gitattributes() -> None:
    """Add a models path to .gitattributes for Git LFS if not already present."""
    gitattributes = Path(".gitattributes")
    lfs_line = "models/** filter=lfs diff=lfs merge=lfs -text\n"
    try:
        if gitattributes.exists():
            existing = gitattributes.read_text()
            if "models/**" in existing:
                return  # already configured
        with gitattributes.open("a", encoding="utf-8") as f:
            f.write("\n" + lfs_line if gitattributes.exists() else lfs_line)
        print("🔧 Added models/** to .gitattributes for Git LFS tracking")
    except Exception as exc:
        print(f"[WARN] Could not update .gitattributes automatically: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, help="HuggingFace repo name")
    parser.add_argument("--output-dir", required=True, help="Destination directory for ST model")
    args = parser.parse_args()
    ensure_st_model(args.repo, Path(args.output_dir))


if __name__ == "__main__":
    main() 