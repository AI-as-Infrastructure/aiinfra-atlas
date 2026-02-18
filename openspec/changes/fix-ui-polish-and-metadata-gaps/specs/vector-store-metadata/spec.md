## ADDED Requirements

### Requirement: Build Environment Metadata
The vector store manifest SHALL include a `build` section capturing the hardware, software, and environment context at build time to support research transparency and reproducibility per FAIR data principles.

The manifest version SHALL be bumped to `1.4` when the `build` section is present.

The build section SHALL include at minimum: compute mode (GPU/CPU), build duration, Python version, PyTorch version, CUDA version (if applicable), platform, machine architecture, GPU details (if used), CPU core count, system RAM, and builder version.

#### Scenario: New vector store build produces v1.4 manifest with build metadata
- **WHEN** the corpus builder generates a manifest during vector store creation
- **THEN** the manifest SHALL contain a `build` section with environment data collected from `SystemRequirementsChecker.get_system_info()`
- **AND** the manifest `version` field SHALL be `1.4`

#### Scenario: Build environment displayed in Vector Store Overview
- **WHEN** a user views the Vector Store Overview modal
- **THEN** the build environment section SHALL be displayed showing compute mode, platform, GPU/CPU details, and software versions

#### Scenario: v1.3 manifests not supported
- **WHEN** a v1.3 manifest (without `build` section) is loaded
- **THEN** the build environment section SHALL NOT be displayed
- **AND** no backward compatibility handling is required — users MUST rebuild their vector store to produce a v1.4 manifest
