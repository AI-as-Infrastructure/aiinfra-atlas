# Specification: Dependency Management

## ADDED Requirements

### Requirement: pyproject.toml Standard
The project SHALL use `pyproject.toml` as the single source of truth for project metadata and dependencies, following PEP 518 and PEP 621 standards.

#### Scenario: Project metadata defined
- **WHEN** examining the project root
- **THEN** a `pyproject.toml` file SHALL exist containing:
  - `[build-system]` section with setuptools backend
  - `[project]` section with name, version, description, authors, license
  - `requires-python = ">=3.10"` constraint
  - All non-PyTorch dependencies listed in `[project.dependencies]`

#### Scenario: Reading project information
- **WHEN** a developer or tool needs project information
- **THEN** they SHALL consult `pyproject.toml` rather than setup.py or requirements files

### Requirement: Optional PyTorch Dependencies
The project SHALL define PyTorch variants as optional dependencies to support different GPU generations and CPU-only installations.

#### Scenario: CPU-only installation
- **WHEN** installing on a CPU-only machine
- **THEN** PyTorch CPU variant SHALL be installable via `uv pip install -e ".[cpu]"`
- **AND** no CUDA libraries SHALL be required

#### Scenario: CUDA 11.8 installation (GTX 10xx, RTX 20xx/30xx)
- **WHEN** installing on a machine with CUDA 11.8 compatible GPU
- **THEN** PyTorch CUDA 11.8 variant SHALL be installable via `uv pip install -e ".[cuda118]" --index-url https://download.pytorch.org/whl/cu118`
- **AND** the installation SHALL support compute capabilities 6.x - 8.x

#### Scenario: CUDA 12.1 installation (RTX 40xx)
- **WHEN** installing on a machine with CUDA 12.1 compatible GPU
- **THEN** PyTorch CUDA 12.1 variant SHALL be installable via `uv pip install -e ".[cuda121]"`
- **AND** the installation SHALL support compute capability 8.9

#### Scenario: CUDA 12.4+ nightly installation (RTX 50xx)
- **WHEN** installing on a machine with RTX 50 series GPU
- **THEN** PyTorch CUDA 12.4+ nightly variant SHALL be installable via `uv pip install -e ".[cuda124-nightly]" --index-url https://download.pytorch.org/whl/nightly/cu124`
- **AND** the system SHALL gracefully fall back to CPU if compute capability 12.0 is not yet supported

### Requirement: uv Package Manager
The project SHALL use `uv` as the primary package installer for speed and reliability.

#### Scenario: Installing dependencies
- **WHEN** setting up the development environment
- **THEN** `uv pip install` commands SHALL be used instead of `pip install`
- **AND** installation SHALL be 10-100x faster than pip

#### Scenario: uv not available
- **WHEN** uv is not installed on the system
- **THEN** installation scripts SHALL detect this condition
- **AND** provide clear instructions for installing uv
- **AND** optionally fall back to pip with a warning message

#### Scenario: Lock file generation
- **WHEN** generating a dependency lock file
- **THEN** `uv pip compile` SHALL be used instead of `pip-compile`
- **AND** the resulting lock file SHALL be portable across CPU and GPU machines

### Requirement: Cross-Machine Reproducibility
Dependency installation SHALL work consistently across different machine types (CPU vs various GPU generations).

#### Scenario: Lock file on different machines
- **WHEN** a lock file is generated on a CPU machine
- **THEN** it SHALL be usable on GPU machines with appropriate optional dependencies
- **AND** vice versa (GPU-generated lock works on CPU)

#### Scenario: PyTorch variant selection
- **WHEN** installing on a machine with specific hardware
- **THEN** the appropriate PyTorch variant SHALL be selected at install time
- **AND** NOT at lock file generation time
- **AND** the lock file SHALL remain machine-agnostic

#### Scenario: No manual PyTorch reinstallation
- **WHEN** dependencies are installed with the correct optional dependency
- **THEN** PyTorch SHALL work without requiring uninstall/reinstall
- **AND** the startup script SHALL only need to select the correct optional dependency
