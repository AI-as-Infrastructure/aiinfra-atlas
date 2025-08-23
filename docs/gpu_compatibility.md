# GPU Compatibility Guide

## Overview

ATLAS runs entirely on CPU and does not require a GPU. GPU acceleration is optional and primarily speeds up vector store creation. To keep the main app environment stable, vector store creation now uses isolated venvs:

- CPU build: `make vs-cpu`
- GPU build (CUDA 12.8 default): `make vs-gpu`

## RTX 50-series GPU Fix

### Defaults for RTX 5090 (CUDA 12.8)

vs-gpu is pre-configured for RTX 50‑series (including 5090) using CUDA 12.8 wheels by default. No extra flags needed.

```bash
# Build the vector store with CUDA 12.8 (default)
make vs-gpu

# Optional: override the CUDA wheel index if needed
TORCH_CUDA_INDEX_URL=https://download.pytorch.org/whl/cu128 make vs-gpu
```

**Verify it worked (inside the vs-gpu venv):**
```bash
. .venv-vs-gpu/bin/activate
python -c "import torch; print('CUDA available:', torch.cuda.is_available(), 'CUDA:', torch.version.cuda)"
```

## Pinning Requirements (Optional)

### Other GPUs (choose the right CUDA wheels)

Older NVIDIA GPUs may require different CUDA wheel indices. Common options:

- CUDA 12.1: https://download.pytorch.org/whl/cu121
- CUDA 12.2: https://download.pytorch.org/whl/cu122
- CUDA 12.4: https://download.pytorch.org/whl/cu124
- CUDA 12.6: https://download.pytorch.org/whl/cu126
- CUDA 12.8 (RTX 50‑series default): https://download.pytorch.org/whl/cu128

Use one for a single run:

```bash
TORCH_CUDA_INDEX_URL=https://download.pytorch.org/whl/cu126 make vs-gpu
```

To permanently pin for your machine only, edit `create/gpu_requirements.txt` instead of global requirements. This keeps the app’s main environment portable for all users.

## CPU-Only Operation

ATLAS works perfectly on CPU:
- All features supported
- Vector store creation works (just slower for large corpora)
- Daily operation (search, retrieval) runs efficiently

No special configuration needed - just run `make b` and you're set. For building vector stores without a GPU, use `make vs-cpu`.
