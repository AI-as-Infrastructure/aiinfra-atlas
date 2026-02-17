# Specification: Build Tooling

## ADDED Requirements

### Requirement: Makefile uv Integration
The Makefile SHALL use `uv` for all Python dependency installation operations.

#### Scenario: Backend installation
- **WHEN** running `make b` or equivalent backend setup target
- **THEN** the Makefile SHALL check if uv is installed
- **AND** use `uv pip install` instead of `pip install`
- **AND** provide installation instructions if uv is not available

#### Scenario: Lock file generation
- **WHEN** running `make l` (generate lock file)
- **THEN** the Makefile SHALL use `uv pip compile pyproject.toml -o requirements.lock`
- **AND** NOT use `pip-compile config/requirements.txt`
- **AND** the generated lock file SHALL be portable across machines

#### Scenario: Vector store creation
- **WHEN** running `make vs` (create vector store)
- **THEN** dependencies SHALL be installed using uv if available
- **AND** GPU detection SHALL work as before
- **AND** the appropriate PyTorch variant SHALL be selected

### Requirement: Startup Script GPU Detection
Backend startup scripts SHALL detect GPU capabilities and install the appropriate PyTorch variant automatically.

#### Scenario: CPU-only machine detection
- **WHEN** starting the backend on a CPU-only machine
- **THEN** the script SHALL detect no GPU is available
- **AND** install using `uv pip install -e ".[cpu]"`
- **AND** log that CPU mode is being used

#### Scenario: CUDA 11.8 compatible GPU detection
- **WHEN** starting the backend on a machine with GTX 10xx, RTX 20xx, or RTX 30xx GPU
- **THEN** the script SHALL detect CUDA 11.8 compatibility via nvidia-smi
- **AND** install using `uv pip install -e ".[cuda118]" --index-url https://download.pytorch.org/whl/cu118`
- **AND** log the detected GPU and CUDA version

#### Scenario: CUDA 12.1 compatible GPU detection
- **WHEN** starting the backend on a machine with RTX 40xx GPU
- **THEN** the script SHALL detect CUDA 12.1 compatibility
- **AND** install using `uv pip install -e ".[cuda121]"`
- **AND** log the detected GPU

#### Scenario: RTX 50 series GPU detection
- **WHEN** starting the backend on a machine with RTX 50 series GPU
- **THEN** the script SHALL detect compute capability 12.0+
- **AND** install using `uv pip install -e ".[cuda124-nightly]" --index-url https://download.pytorch.org/whl/nightly/cu124`
- **AND** log a warning that nightly builds are being used
- **AND** fall back to CPU if GPU operations fail

#### Scenario: GPU detection failure
- **WHEN** GPU detection fails or nvidia-smi is unavailable
- **THEN** the script SHALL fall back to CPU installation
- **AND** log the reason for fallback
- **AND** NOT fail the installation

### Requirement: Deployment Script Updates
All deployment scripts (dev, staging, production) SHALL use uv for dependency management.

#### Scenario: Development environment setup
- **WHEN** setting up a development environment
- **THEN** `deploy/dev/scripts/start_backend.sh` SHALL use uv
- **AND** install dependencies from pyproject.toml
- **AND** select appropriate PyTorch variant

#### Scenario: Staging environment setup
- **WHEN** deploying to staging environment
- **THEN** staging scripts SHALL use uv
- **AND** handle GPU detection identically to development

#### Scenario: Production deployment
- **WHEN** deploying to production
- **THEN** production scripts SHALL use uv
- **AND** verify uv is installed before proceeding
- **AND** provide clear error messages if uv is missing

### Requirement: Backward Compatibility and Migration
The migration SHALL provide clear paths for rollback and troubleshooting.

#### Scenario: Rollback to pip
- **WHEN** uv causes issues in production
- **THEN** a documented rollback procedure SHALL exist
- **AND** the system SHALL be able to revert to pip-based installation
- **AND** the rollback SHALL be completable in under 5 minutes

#### Scenario: Installation troubleshooting
- **WHEN** users encounter installation issues
- **THEN** clear error messages SHALL indicate the problem
- **AND** documentation SHALL provide solutions for common issues
- **AND** both uv and pip commands SHALL be documented

#### Scenario: Migration documentation
- **WHEN** developers need to understand the new system
- **THEN** migration documentation SHALL explain:
  - Why the change was made
  - How to install uv
  - How to select PyTorch variants
  - How optional dependencies work
  - How to regenerate the lock file
