# GPU Compatibility Guide

## Overview

ATLAS runs entirely on CPU and does not require a GPU. GPU acceleration is optional and primarily speeds up vector store creation.

## RTX 50-series GPU Fix

If you have an RTX 5090 or other RTX 50-series GPU and see CUDA compatibility warnings:

```bash
# Activate your virtual environment
source .venv/bin/activate

# Upgrade to CUDA 12.8 compatible PyTorch
pip uninstall torch torchvision torchaudio -y
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
```

**Verify it worked:**
```bash
python -c "import torch; print('CUDA available:', torch.cuda.is_available())"
```

## Pinning Requirements (Optional)

If you want to lock in the CUDA 12.8 versions to prevent future issues, update `config/requirements.txt`:

**Replace:**
```
torch==2.7.1
```

**With:**
```
torch==2.7.1+cu128
torchvision==0.22.1+cu128
torchaudio==2.7.1+cu128
```

**Note:** This pins the requirements to RTX 50-series compatible versions. Other users with older GPUs or CPU-only setups will need to manually install the generic versions.

## CPU-Only Operation

ATLAS works perfectly on CPU:
- All features supported
- Vector store creation works (just slower for large corpora)
- Daily operation (search, retrieval) runs efficiently

No special configuration needed - just run `make b` and you're set.
