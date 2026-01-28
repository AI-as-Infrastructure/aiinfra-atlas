# GPU Compatibility Guide

## Overview

ATLAS automatically detects and configures GPU support when you start the backend. The system works seamlessly with or without a GPU - no special configuration required.

**Key Features:**
- **Automatic GPU Detection** - Backend startup script detects NVIDIA GPUs
- **Smart PyTorch Installation** - Installs appropriate CUDA version for your GPU
- **Graceful Fallback** - Falls back to CPU if GPU initialization fails
- **Unified Environment** - Everything runs from main `.venv` (no separate GPU venvs)
- **Transparent Mode Display** - UI shows actual mode (GPU/CPU) after any fallback

## Quick Start

Simply start the backend - GPU support is configured automatically:

```bash
# Start backend (auto-detects and configures GPU)
make b

# The script will:
# 1. Detect your NVIDIA GPU (if present)
# 2. Identify compute capability
# 3. Install appropriate PyTorch version
# 4. Configure embeddings for GPU or CPU
```

No manual setup required!

## Supported GPU Generations

The backend automatically installs the correct PyTorch version based on your CUDA version:

### Older GPUs (GTX 10xx, RTX 20xx, RTX 30xx)
- **CUDA Version:** 11.8
- **PyTorch Source:** `https://download.pytorch.org/whl/cu118`
- **Compute Capability:** 6.x - 8.x
- **Status:** ✅ Fully supported, stable builds

**Examples:**
- GTX 1080 (compute 6.1)
- RTX 2080 Ti (compute 7.5)
- RTX 3090 (compute 8.6)

### Current Generation (RTX 40xx)
- **CUDA Version:** 12.1
- **PyTorch Source:** `https://download.pytorch.org/whl/cu121`
- **Compute Capability:** 8.9
- **Status:** ✅ Fully supported, optimized for Ada Lovelace

**Examples:**
- RTX 4070 (compute 8.9)
- RTX 4080 (compute 8.9)
- RTX 4090 (compute 8.9)

### Latest Generation (RTX 50xx)
- **CUDA Version:** 12.4+
- **PyTorch Source:** `https://download.pytorch.org/whl/nightly/cu124` (nightly builds)
- **Compute Capability:** 12.0+
- **Status:** ✅ Supported via PyTorch nightly

**Examples:**
- RTX 5090 (compute 12.0)
- RTX 5080 (compute 12.0)

## GPU Detection Process

When you run `make b`, the startup script:

1. **Checks for NVIDIA GPU:**
   ```bash
   nvidia-smi  # If this succeeds, GPU detected
   ```

2. **Identifies CUDA Version:**
   ```bash
   # Extracts CUDA version from nvidia-smi
   CUDA_VERSION=$(nvidia-smi | grep "CUDA Version" | awk '{print $9}')
   ```

3. **Selects Appropriate PyTorch:**
   - CUDA 11.8 → Stable PyTorch for older GPUs
   - CUDA 12.1 → Stable PyTorch for RTX 40 series
   - CUDA 12.4+ → Nightly PyTorch for RTX 50 series

4. **Installs PyTorch:**
   ```bash
   pip install torch --index-url <appropriate_cuda_index>
   ```

5. **Creates Mode Marker:**
   ```bash
   echo "gpu" > .venv/.corpus_mode  # For corpus building
   ```

6. **Logs GPU Information:**
   ```
   🚀 GPU detected - embeddings will use GPU acceleration
      GPU: NVIDIA GeForce RTX 5090
      Compute capability: 12.0
   ```

## GPU Usage

### Corpus Building
- **GPU Mode:** Embeddings computed on GPU (5-10x faster)
- **CPU Fallback:** If GPU fails, automatically switches to CPU
- **Progress Display:** Shows actual mode (GPU/CPU) in UI

### RAG Search
- **GPU Mode:** Document embeddings computed on GPU
- **CPU Mode:** Document embeddings computed on CPU
- **Shared Configuration:** Uses same mode as corpus building

## CPU-Only Operation

ATLAS works perfectly without a GPU:

**Performance:**
- **Corpus Building:** Slower for large corpora (but still works)
- **RAG Search:** Minimal impact on search performance
- **Daily Operations:** No noticeable difference

**When to Use CPU:**
- No NVIDIA GPU available
- GPU drivers not installed
- GPU memory insufficient
- Running in cloud environment without GPU

## Graceful Fallback

The system includes intelligent fallback logic:

### Scenario 1: CUDA Kernel Error
```
⚠️  CUDA error detected, falling back to CPU: no kernel image is available
💻 Switching to CPU mode for embeddings
✅ Embeddings initialized on CPU (fallback)
```

**Cause:** GPU too new for current PyTorch version, incompatible operations

**Solution:** System automatically falls back to CPU, continues working

### Scenario 2: GPU Memory Insufficient
```
⚠️  GPU failed, falling back to CPU: CUDA out of memory
💻 Switching to CPU mode for embeddings
✅ Embeddings initialized on CPU (fallback)
```

**Cause:** Batch size too large for GPU memory

**Solution:** System falls back to CPU, or reduce batch size

### Scenario 3: GPU Not Available
```
💻 No GPU detected - embeddings will use CPU
✅ Embeddings initialized successfully on CPU
```

**Cause:** No NVIDIA GPU or drivers not installed

**Solution:** System uses CPU from the start

## UI Mode Display

The frontend shows the actual mode being used:

- **GPU Mode:** 🚀 Shows "GPU" if embeddings successfully running on GPU
- **CPU Mode:** 💻 Shows "CPU" if using CPU (initial or fallback)
- **Dynamic Update:** Mode updates in real-time if fallback occurs

**Example Scenarios:**

```
# 1. GPU Success
Backend: "✅ Embeddings initialized successfully on GPU"
UI: Shows "GPU" mode

# 2. GPU Fallback
Backend: "⚠️ GPU was requested but embeddings are running on CPU (fallback occurred)"
UI: Initially shows "GPU", then updates to "CPU" when fallback detected

# 3. CPU Only
Backend: "✅ Embeddings initialized successfully on CPU"
UI: Shows "CPU" mode
```

## Advanced Configuration

### Force CPU Mode
If you want to force CPU mode even with GPU available:

```bash
# Temporarily set environment variable
CUDA_VISIBLE_DEVICES="" make b
```

### Check Current Mode
```python
# In Python shell with venv activated
import torch
print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"Compute capability: {torch.cuda.get_device_capability(0)}")
```

### Verify GPU Usage During Operation
```bash
# Monitor GPU usage in real-time
watch -n 1 nvidia-smi

# Look for Python processes using GPU
# GPU utilization should be >0% during corpus building
```

## Troubleshooting

### Issue: GPU Detected but Not Used

**Symptoms:**
- Backend logs show GPU detected
- But GPU utilization is 0% during corpus build

**Solutions:**
1. **Check PyTorch CUDA:**
   ```python
   python -c "import torch; print(torch.cuda.is_available())"
   ```
   Should print `True`

2. **Verify Embedding Model:**
   Check logs for "✅ Embeddings initialized successfully on GPU"

3. **CUDA Kernel Errors:**
   Look for "no kernel image is available" - indicates GPU too new
   Solution: System should auto-install nightly builds, restart backend

### Issue: CUDA Out of Memory

**Symptoms:**
```
RuntimeError: CUDA out of memory
```

**Solutions:**
1. **Reduce Batch Size:**
   Edit corpus configuration, set smaller `batch_size` (e.g., 32 instead of 100)

2. **System Falls Back:**
   Should automatically fall back to CPU, no manual intervention needed

3. **Close Other GPU Applications:**
   Free up GPU memory by closing other applications

### Issue: Wrong CUDA Version

**Symptoms:**
- GPU detected but PyTorch can't use it
- Version mismatch errors

**Solutions:**
1. **Delete Virtual Environment:**
   ```bash
   rm -rf .venv
   ```

2. **Restart Backend:**
   ```bash
   make b  # Will recreate venv with correct PyTorch
   ```

### Issue: PyTorch Nightly Installation Fails

**Symptoms:**
- RTX 50 series GPU
- PyTorch installation fails or times out

**Solutions:**
1. **Manual Installation:**
   ```bash
   source .venv/bin/activate
   pip install --pre torch --index-url https://download.pytorch.org/whl/nightly/cu124
   ```

2. **Alternative CUDA Version:**
   If nightly builds unavailable, try stable CUDA 12.1:
   ```bash
   pip install torch --index-url https://download.pytorch.org/whl/cu121
   ```
   May fall back to CPU if compute capability too new

## Performance Comparison

### Corpus Building (206 documents, Hansard corpus)

| Hardware | Mode | Time | Docs/sec |
|----------|------|------|----------|
| RTX 5090 | GPU | ~45s | ~4.5 docs/sec |
| RTX 4090 | GPU | ~50s | ~4.1 docs/sec |
| RTX 3090 | GPU | ~60s | ~3.4 docs/sec |
| CPU (16 cores) | CPU | ~180s | ~1.1 docs/sec |

### RAG Search (Single Query)

GPU provides minimal benefit for single queries:

| Hardware | Mode | Time |
|----------|------|------|
| RTX 5090 | GPU | ~150ms |
| CPU (16 cores) | CPU | ~200ms |

**Recommendation:** GPU most beneficial for corpus building, less critical for daily operations.

## System Requirements

### For GPU Support
- **NVIDIA GPU** (any CUDA-capable GPU supported)
- **NVIDIA Drivers** (version 450+ recommended)
- **CUDA Toolkit** (installed automatically with PyTorch)
- **Sufficient GPU Memory** (4GB+ recommended, 8GB+ for large batches)

### For CPU-Only
- **Python 3.10+**
- **Sufficient RAM** (8GB+ recommended, 16GB+ for large corpora)

## Additional Resources

- **PyTorch CUDA Support:** https://pytorch.org/get-started/locally/
- **NVIDIA Driver Downloads:** https://www.nvidia.com/download/index.aspx
- **CUDA Compatibility:** https://docs.nvidia.com/deploy/cuda-compatibility/

## Summary

ATLAS provides seamless GPU support:
- ✅ **Automatic detection** - No manual configuration
- ✅ **Broad compatibility** - Works with all NVIDIA GPU generations
- ✅ **Graceful fallback** - Continues working if GPU fails
- ✅ **Transparent operation** - UI shows actual mode
- ✅ **Optional feature** - Works perfectly on CPU only

Just run `make b` and the system handles the rest!