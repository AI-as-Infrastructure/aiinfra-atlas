#!/bin/bash

# Vector store creation (GPU) using an isolated venv
set -euo pipefail

ENV_FILE="config/.env.development"

echo "[vs-gpu] 🔍 Pre-flight checks"
if [ ! -d "config" ]; then echo "[vs-gpu] ❌ Missing config directory"; exit 1; fi
if [ ! -f "$ENV_FILE" ]; then echo "[vs-gpu] ❌ Missing $ENV_FILE"; exit 1; fi
if [ ! -f "config/requirements.lock" ]; then echo "[vs-gpu] ❌ Missing config/requirements.lock. Run 'make l' first."; exit 1; fi
if [ ! -f "create/txt/create_hansard_store.py" ]; then echo "[vs-gpu] ❌ Missing create/txt/create_hansard_store.py"; exit 1; fi

VENV_DIR=".venv-vs-gpu"
if [ ! -d "$VENV_DIR" ]; then
  echo "[vs-gpu] 📦 Creating isolated venv at $VENV_DIR"
  python3 -m venv "$VENV_DIR"
fi

echo "[vs-gpu] 🔌 Activating venv"
source "$VENV_DIR/bin/activate"

echo "[vs-gpu] 🌱 Loading environment from $ENV_FILE"
set -a
source "$ENV_FILE"
set +a

echo "[vs-gpu] 📥 Installing dependencies (GPU)"
pip install --upgrade pip
# Install everything from the lockfile except the torch stack and triton (torch will pull the right one)
TMP_NO_TORCH=$(mktemp)
grep -v -E '^(torch|torchvision|torchaudio|triton)==.*' config/requirements.lock > "$TMP_NO_TORCH"
pip install -r "$TMP_NO_TORCH"
rm -f "$TMP_NO_TORCH"

# Install CUDA-enabled torch stack. Allow override via TORCH_CUDA_INDEX_URL, default to cu128.
PYTORCH_INDEX_DEFAULT="https://download.pytorch.org/whl/cu128"
PYTORCH_INDEX="${TORCH_CUDA_INDEX_URL:-$PYTORCH_INDEX_DEFAULT}"
pip install --index-url "$PYTORCH_INDEX" -r create/gpu_requirements.txt

# Quick CUDA preflight
python - <<'PY'
import sys, torch
print("[vs-gpu] 🔎 Torch:", torch.__version__)
print("[vs-gpu] 🔎 CUDA available:", torch.cuda.is_available())
if torch.cuda.is_available():
  print("[vs-gpu] 🔎 CUDA version:", torch.version.cuda)
  try:
    print("[vs-gpu] 🔎 Device:", torch.cuda.get_device_name(0))
  except Exception as e:
    print("[vs-gpu] ⚠️  Unable to read GPU device name:", e)
else:
  print("[vs-gpu] ❌ CUDA not available in this venv. If you have an RTX 50-series, use cu128 wheels.")
  sys.exit(1)
PY

# Allow a preflight-only check without building the store
if [ "${VS_NO_BUILD:-}" = "1" ]; then
  echo "[vs-gpu] ✅ Preflight passed. Skipping build due to VS_NO_BUILD=1"
  exit 0
fi

echo "[vs-gpu] 📁 Using TXT builder (XML path disabled)"
rm -rf create/output && mkdir -p create/output
python create/txt/create_hansard_store.py
echo "[vs-gpu] ✅ Build completed. Artifacts available in create/output:"
echo "  • Vector store: create/output/chroma_db/"
echo "  • Manifest:     create/output/manifest.json"
echo "  • BM25 JSONL:   create/output/bm25_corpus.jsonl"
echo "[vs-gpu] 👉 Next steps — copy into backend/targets:"
echo "  1) cp -r create/output/chroma_db backend/targets/chroma_db"
echo "  2) cp create/output/manifest.json backend/targets/manifest.json"
echo "  3) cp create/output/bm25_corpus.jsonl backend/targets/bm25_corpus.jsonl"
echo "  4) Ensure CHROMA_PERSIST_DIRECTORY=backend/targets/chroma_db in config/.env.development"
echo "[vs-gpu] ✅ Done"
