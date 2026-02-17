# Implementation Tasks: Migrate to uv with pyproject.toml

**Change ID:** `migrate-to-uv-pyproject`
**Status:** Proposed

## Task Breakdown

### Phase 1: Setup and Preparation

#### Task 1.1: Install and verify uv
- [ ] Install uv locally: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- [ ] Verify installation: `uv --version`
- [ ] Test basic commands: `uv pip list`, `uv pip freeze`

#### Task 1.2: Analyze current dependencies
- [ ] Review `config/requirements.txt` for all dependencies
- [ ] Identify PyTorch-specific dependencies that need variants
- [ ] Document any dependencies with special installation requirements
- [ ] Check for any pip-only features that might not work with uv

### Phase 2: Create pyproject.toml

#### Task 2.1: Create base pyproject.toml structure
- [ ] Create `pyproject.toml` in project root
- [ ] Add `[build-system]` section for setuptools backend
- [ ] Add `[project]` section with metadata:
  - name: "atlas-rag"
  - version: Read from existing source or set initial version
  - description: From ReadMe.md
  - requires-python: ">=3.10"
  - authors: Project authors
  - license: From LICENSE.md

#### Task 2.2: Convert base dependencies
- [ ] Copy all non-PyTorch dependencies from `config/requirements.txt`
- [ ] Format as list in `[project.dependencies]`
- [ ] Verify version specifiers are compatible with PEP 440
- [ ] Test that dependency list is complete

#### Task 2.3: Define optional PyTorch dependencies
- [ ] Create `[project.optional-dependencies]` section
- [ ] Define `cpu` extra: torch>=2.8.0 (no special index needed for CPU)
- [ ] Define `cuda118` extra for GTX 10xx/RTX 20xx/30xx
- [ ] Define `cuda121` extra for RTX 40xx series
- [ ] Define `cuda124-nightly` extra for RTX 50xx series
- [ ] Add comment explaining each variant and compatible hardware

### Phase 3: Update Installation Scripts

#### Task 3.1: Update start_backend.sh
- [ ] Read current `deploy/dev/scripts/start_backend.sh`
- [ ] Replace pip-based installation with uv commands
- [ ] Update GPU detection logic to select appropriate PyTorch variant:
  - Detect CUDA version with nvidia-smi
  - Map to appropriate optional dependency (cpu/cuda118/cuda121/cuda124-nightly)
  - Install with: `uv pip install -e ".[<variant>]" --index-url <pytorch-url>`
- [ ] Add fallback to CPU if GPU detection fails
- [ ] Test on CPU-only machine
- [ ] Test on GPU machines (CUDA 11.8, 12.1, 12.4+ if available)

#### Task 3.2: Update Makefile targets
- [ ] Read current `Makefile`
- [ ] Update `install-backend` or equivalent target:
  - Check if uv is installed
  - Provide installation instructions if not
  - Use `uv pip install` instead of `pip install`
- [ ] Update `l` target (generate lock file):
  - Replace `pip-compile` with `uv pip compile`
  - Generate `requirements.lock` from `pyproject.toml`
  - Test that lock file is portable across machines
- [ ] Add optional fallback to pip if uv unavailable (with warning)
- [ ] Update any other targets that install dependencies

#### Task 3.3: Update staging/production scripts
- [ ] Update `deploy/staging/scripts/start_backend.sh` (if different from dev)
- [ ] Update production deployment scripts in `deploy/production/`
- [ ] Ensure all scripts check for uv availability
- [ ] Add uv installation to deployment prerequisites

### Phase 4: Documentation Updates

#### Task 4.1: Update main documentation
- [ ] Update `ReadMe.md`:
  - Add uv as prerequisite
  - Update installation instructions
  - Add quick start section with uv commands
  - Update "Command Reference" section
- [ ] Update `docs/development.md`:
  - Add uv installation instructions
  - Document new dependency management workflow
  - Explain optional dependencies for PyTorch variants
  - Add troubleshooting section for uv issues

#### Task 4.2: Update GPU documentation
- [ ] Update `docs/gpu_compatibility.md`:
  - Add section on PyTorch variant selection
  - Document how optional dependencies work
  - Add examples: `uv pip install -e ".[cuda118]"`
  - Update installation workflow

#### Task 4.3: Create migration guide
- [ ] Create `docs/migration/uv-migration.md`:
  - Document why migration was needed
  - Explain pyproject.toml structure
  - Provide before/after comparison
  - Document rollback procedure if needed
  - Add FAQ for common issues

#### Task 4.4: Update contributor documentation
- [ ] Update any contributor guides with new workflow
- [ ] Document how to add new dependencies
- [ ] Document how to regenerate lock file
- [ ] Update CI/CD documentation (if applicable)

### Phase 5: Testing and Validation

#### Task 5.1: Test CPU installation
- [ ] Clean environment: Delete venv
- [ ] Fresh install: `uv pip install -e ".[cpu]"`
- [ ] Verify all dependencies installed correctly
- [ ] Test backend starts: `make b`
- [ ] Test corpus build works: Create small test corpus
- [ ] Measure installation time vs old pip-based approach

#### Task 5.2: Test GPU installations
- [ ] Test CUDA 11.8 variant (if hardware available):
  - Clean environment
  - Install: `uv pip install -e ".[cuda118]" --index-url https://download.pytorch.org/whl/cu118`
  - Verify GPU detected and used
  - Test corpus build with GPU
- [ ] Test CUDA 12.1 variant (if hardware available):
  - Clean environment
  - Install: `uv pip install -e ".[cuda121]"`
  - Verify GPU detected and used
- [ ] Test CUDA 12.4+ nightly variant (if RTX 50 available):
  - Clean environment
  - Install: `uv pip install -e ".[cuda124-nightly]" --index-url https://download.pytorch.org/whl/nightly/cu124`
  - Verify detection and fallback if needed

#### Task 5.3: Test lock file portability
- [ ] Generate lock file on CPU machine
- [ ] Test lock file works on GPU machine
- [ ] Verify PyTorch variants can be installed from same lock
- [ ] Document any limitations or required flags

#### Task 5.4: Test Makefile targets
- [ ] Test `make b` - Backend starts correctly
- [ ] Test `make f` - Frontend works (no changes, but verify)
- [ ] Test `make l` - Lock file generation works
- [ ] Test `make vs` - Vector store creation works
- [ ] Test `make c` - Python environment check works
- [ ] Test any other affected targets

### Phase 6: Cleanup and Finalization

#### Task 6.1: Update configuration files
- [ ] Update `.gitignore` if needed for uv artifacts
- [ ] Consider deprecating `config/requirements.lock` or update generation
- [ ] Update any CI/CD config files (GitHub Actions, etc.)

#### Task 6.2: Performance benchmarking
- [ ] Measure installation time: uv vs pip
- [ ] Document speed improvements
- [ ] Measure corpus build time (should be same)
- [ ] Update documentation with benchmarks

#### Task 6.3: Final validation
- [ ] Run through complete setup on fresh machine
- [ ] Verify all documentation is accurate
- [ ] Check all Makefile commands work
- [ ] Verify rollback procedure works

#### Task 6.4: Create summary and changelog
- [ ] Document all changes in CHANGELOG (if exists)
- [ ] Create migration announcement for users
- [ ] Update version number if applicable
- [ ] Tag release after successful deployment

## Task Dependencies

```
Phase 1 (Setup)
    ↓
Phase 2 (pyproject.toml) → Must complete before Phase 3
    ↓
Phase 3 (Scripts) → Must complete before Phase 5
    ↓
Phase 4 (Documentation) → Can run parallel with Phase 3
    ↓
Phase 5 (Testing) → Must complete before Phase 6
    ↓
Phase 6 (Finalization)
```

## Rollback Plan

If migration fails or causes issues:

1. **Immediate Rollback**:
   - Revert all script changes
   - Delete `pyproject.toml`
   - Use original `config/requirements.txt` and `requirements.lock`
   - Reinstall with pip: `pip install -r config/requirements.lock`

2. **Keep Changes But Revert to pip**:
   - Keep `pyproject.toml` for metadata
   - Modify scripts to use pip instead of uv
   - Keep optional dependencies structure but install with pip

3. **Partial Migration**:
   - Keep uv for development environments only
   - Use pip for production until confident
   - Gradually roll out to staging then production

## Success Metrics

After completing all tasks, verify:

- ✅ Fresh installation with uv works on CPU machine
- ✅ Fresh installation with uv works on GPU machine (all variants tested)
- ✅ Installation is measurably faster (document speedup)
- ✅ All Makefile targets work without modification
- ✅ Backend starts successfully on dev environment
- ✅ Vector store creation works with GPU/CPU
- ✅ Documentation is complete and accurate
- ✅ At least one full test deployment to staging environment successful

## Estimated Time

- Phase 1: 30 minutes
- Phase 2: 1-2 hours
- Phase 3: 2-3 hours
- Phase 4: 2-3 hours
- Phase 5: 3-4 hours (depends on hardware availability)
- Phase 6: 1-2 hours

**Total: 10-15 hours** (spread across multiple days for testing)
