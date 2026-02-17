# Proposal: Migrate to uv with pyproject.toml

**Change ID:** `migrate-to-uv-pyproject`
**Status:** Proposed
**Created:** 2026-01-28

## Why

The current dependency management system using pip with requirements.lock creates significant cross-machine reproducibility issues, particularly for PyTorch GPU/CPU variants, resulting in manual workarounds and slower installation times.

## What Changes

- Replace `requirements.txt` with `pyproject.toml` following PEP 518/621 standards
- Introduce `uv` package manager for 10-100x faster dependency installation
- Define PyTorch variants as optional dependencies (`[cpu]`, `[cuda118]`, `[cuda121]`, `[cuda124-nightly]`)
- Update all installation scripts to use uv with automatic GPU detection
- Create machine-agnostic lock files that work across CPU and GPU systems
- **BREAKING**: Users will need to install `uv` before running setup (fallback to pip provided)

## Impact

- Affected specs: dependency-management, build-tooling (new capabilities)
- Affected code: Makefile, start_backend.sh, all deployment scripts, documentation
- User impact: Requires uv installation but provides significant speed improvements

## Problem Statement

Current dependency management uses `pip` with `requirements.txt` and `requirements.lock` (via `pip-compile`). This creates cross-machine reproducibility issues for PyTorch installation:

1. **GPU Variant Conflict**: `requirements.lock` pins `torch==2.8.0+cpu` which conflicts with GPU-specific PyTorch versions
2. **Manual Override Required**: `start_backend.sh` must uninstall and reinstall PyTorch based on GPU detection
3. **Not Reproducible**: Lock file generated on one machine type (CPU/GPU) doesn't work cleanly on others
4. **Slow Installation**: `pip` is significantly slower than modern alternatives (10-100x)
5. **Complex Dependency Resolution**: pip-compile doesn't handle optional dependencies elegantly

### Current Workflow

```bash
# 1. Install all deps including wrong PyTorch
pip install -r config/requirements.lock

# 2. Detect GPU and reinstall correct PyTorch
if nvidia-smi; then
    pip uninstall torch -y
    pip install torch --index-url <cuda-specific-url>
fi
```

## Proposed Solution

Migrate to `uv` package manager with `pyproject.toml` using optional dependencies for GPU variants.

### Benefits

1. **10-100x Faster**: uv is significantly faster than pip for installs and resolution
2. **Native Optional Dependencies**: Clean PyTorch variant management
3. **Cross-Machine Reproducible**: Single lock file works across CPU/GPU machines
4. **Modern Standard**: `pyproject.toml` is Python's standard (PEP 518, 621)
5. **Better Resolution**: uv has superior dependency resolution
6. **Future-Proof**: Foundation for potential migration to monorepo tools

### New Workflow

```bash
# CPU machine
uv pip install -e ".[cpu]"

# GPU machine with CUDA 11.8
uv pip install -e ".[cuda118]"

# GPU machine with CUDA 12.1
uv pip install -e ".[cuda121]"

# GPU machine with CUDA 12.4+ (RTX 50 series)
uv pip install -e ".[cuda124-nightly]"
```

## Scope

### In Scope

- Convert `requirements.txt` to `pyproject.toml` with `[project]` table
- Define optional dependencies for PyTorch variants (`[cpu]`, `[cuda118]`, `[cuda121]`, `[cuda124-nightly]`)
- Update `Makefile` targets to use `uv` instead of `pip`
- Update `deploy/dev/scripts/start_backend.sh` to detect GPU and install appropriate variant
- Update documentation (`ReadMe.md`, `docs/development.md`, `docs/gpu_compatibility.md`)
- Generate new lock file with `uv pip compile`
- Test installation on CPU and GPU machines

### Out of Scope

- Migrating to Poetry or other higher-level tools
- Workspace/monorepo setup (future enhancement)
- Changing Python version requirements
- Modifying any application code (only dependency management)
- Automated GPU detection in pyproject.toml (handled by startup script)

## Design Decisions

### Why uv?

1. **Speed**: 10-100x faster than pip (critical for development velocity)
2. **Compatibility**: Drop-in replacement for pip commands
3. **Minimal Disruption**: Works with existing venv workflow
4. **Active Development**: Well-maintained by Astral (ruff creators)
5. **No Lock-In**: Can migrate back to pip if needed

### Why pyproject.toml?

1. **PEP Standard**: Modern Python packaging standard
2. **Optional Dependencies**: Native support for variants
3. **Single Source**: All project metadata in one file
4. **Tool Ecosystem**: Better tooling support

### PyTorch Variant Strategy

Define as optional dependencies:

```toml
[project.optional-dependencies]
# CPU-only (smallest, portable)
cpu = [
    "torch>=2.8.0",
]

# CUDA 11.8 (GTX 10xx, RTX 20xx/30xx)
cuda118 = [
    "torch>=2.8.0",
]

# CUDA 12.1 (RTX 40xx)
cuda121 = [
    "torch>=2.8.0",
]

# CUDA 12.4+ nightly (RTX 50xx)
cuda124-nightly = [
    "torch>=2.7.0.dev",
]
```

**Note**: Actual PyTorch URLs will be handled by `uv pip install` with `--index-url` or `--extra-index-url` flags, detected dynamically by startup script.

## Risks & Mitigation

### Risk 1: uv Not Installed

**Mitigation**:
- Makefile checks for uv and provides installation instructions
- Fallback to pip if uv unavailable (with warning)
- Document uv installation in setup guides

### Risk 2: Breaking Changes in uv

**Mitigation**:
- Pin uv version in documentation
- Test on clean environments before deployment
- Keep pip fallback option

### Risk 3: Team Unfamiliarity

**Mitigation**:
- Document all common commands with uv equivalents
- uv commands are nearly identical to pip
- Provide troubleshooting guide

### Risk 4: CI/CD Integration

**Mitigation**:
- Update CI/CD to install uv
- Test in staging before production
- Document rollback procedure

## Implementation Plan

See `tasks.md` for detailed implementation steps.

## Success Criteria

1. ✅ `pyproject.toml` replaces `requirements.txt` and defines all dependencies
2. ✅ `uv` successfully installs dependencies on CPU-only machines
3. ✅ `uv` successfully installs dependencies on GPU machines (CUDA 11.8, 12.1, 12.4+)
4. ✅ Installation is measurably faster than current pip-based approach
5. ✅ All existing Makefile targets work with minimal changes
6. ✅ Documentation updated to reflect new workflow
7. ✅ Backend starts successfully after migration on dev/staging/production

## Related Changes

- Related to GPU compatibility improvements (automatic PyTorch detection)
- Foundation for potential future monorepo migration
- Aligns with Python packaging best practices (PEP 621)

## References

- [uv Documentation](https://github.com/astral-sh/uv)
- [PEP 621 - Storing project metadata in pyproject.toml](https://peps.python.org/pep-0621/)
- [PEP 518 - pyproject.toml specification](https://peps.python.org/pep-0518/)
- [PyTorch Installation Guide](https://pytorch.org/get-started/locally/)
