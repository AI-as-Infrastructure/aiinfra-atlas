#!/bin/bash

# Vector store creation (CPU) using an isolated venv
set -euo pipefail

ENV_FILE="config/.env.development"

echo "[vs-cpu] 🔍 Pre-flight checks"
if [ ! -d "config" ]; then echo "[vs-cpu] ❌ Missing config directory"; exit 1; fi
if [ ! -f "$ENV_FILE" ]; then echo "[vs-cpu] ❌ Missing $ENV_FILE"; exit 1; fi
if [ ! -f "config/requirements.lock" ]; then echo "[vs-cpu] ❌ Missing config/requirements.lock. Run 'make l' first."; exit 1; fi
if [ ! -f "create/txt/create_hansard_store.py" ]; then echo "[vs-cpu] ❌ Missing create/txt/create_hansard_store.py"; exit 1; fi

VENV_DIR=".venv-vs-cpu"
if [ ! -d "$VENV_DIR" ]; then
  echo "[vs-cpu] 📦 Creating isolated venv at $VENV_DIR"
  python3 -m venv "$VENV_DIR"
fi

echo "[vs-cpu] 🔌 Activating venv"
source "$VENV_DIR/bin/activate"

echo "[vs-cpu] 🌱 Loading environment from $ENV_FILE"
set -a
source "$ENV_FILE"
set +a

echo "[vs-cpu] 📥 Installing dependencies (CPU)"
pip install --upgrade pip
# Install everything from the lockfile except the torch stack and triton (torch will pull the right one)
TMP_NO_TORCH=$(mktemp)
grep -v -E '^(torch|torchvision|torchaudio|triton)==.*' config/requirements.lock > "$TMP_NO_TORCH"
pip install -r "$TMP_NO_TORCH"
rm -f "$TMP_NO_TORCH"

# Ensure CPU-only torch stack
pip install -r create/cpu_requirements.txt

# Allow a preflight-only check without building the store
if [ "${VS_NO_BUILD:-}" = "1" ]; then
  echo "[vs-cpu] ✅ Preflight passed. Skipping build due to VS_NO_BUILD=1"
  exit 0
fi

echo "[vs-cpu] 📁 Using TXT builder (XML path disabled)"
rm -rf create/output && mkdir -p create/output
python create/txt/create_hansard_store.py
echo "[vs-cpu] ✅ Build completed. Artifacts available in create/output:"
echo "  • Vector store: create/output/chroma_db/"
echo "  • Manifest:     create/output/manifest.json"
echo "  • BM25 JSONL:   create/output/bm25_corpus.jsonl"
echo "[vs-cpu] 👉 Next steps — copy into backend/targets:"
echo "  1) cp -r create/output/chroma_db backend/targets/chroma_db"
echo "  2) cp create/output/manifest.json backend/targets/manifest.json"
echo "  3) cp create/output/bm25_corpus.jsonl backend/targets/bm25_corpus.jsonl"
echo "  4) Ensure CHROMA_PERSIST_DIRECTORY=backend/targets/chroma_db in config/.env.development"
echo "[vs-cpu] ✅ Done"
