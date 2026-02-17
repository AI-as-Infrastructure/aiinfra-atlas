# Makefile Specification

## REMOVED Requirements

### Requirement: Model Preparation Target
The Makefile SHALL NO LONGER include a `pm` (prepare model) target.

**Reason**: The Corpus Wizard now handles model preparation automatically during the build process.

**Migration**: Use the Corpus Wizard to prepare embedding models as part of corpus creation.

#### Scenario: pm target removed
- **WHEN** running `make pm`
- **THEN** the command SHALL fail with "No rule to make target"

### Requirement: Hansard Analysis Target
The Makefile SHALL NO LONGER include a `hansard-analysis` target.

**Reason**: This is too specific to a particular dataset. Users can run the analysis script directly via Python.

**Migration**: Run `python analysis/analyze_hansard_spans.py` directly if needed.

#### Scenario: hansard-analysis target removed
- **WHEN** running `make hansard-analysis`
- **THEN** the command SHALL fail with "No rule to make target"

### Requirement: Verbose Health Check Targets
The Makefile SHALL NO LONGER include `health-verbose`, `health-json`, or `health-critical` targets.

**Reason**: These are redundant. The base `health` target can accept flags for different output modes.

**Migration**: Use `make health` with appropriate flags or run the health check script directly.

#### Scenario: health variant targets removed
- **WHEN** running `make health-verbose`, `make health-json`, or `make health-critical`
- **THEN** the commands SHALL fail with "No rule to make target"

### Requirement: Corpus Management Targets
The Makefile SHALL NO LONGER include `corpus-backup`, `corpus-restore`, or `corpus-list` targets.

**Reason**: The Corpus Wizard UI now handles all corpus management operations including backup and restore.

**Migration**: Use the Corpus Wizard UI to manage corpora.

#### Scenario: corpus management targets removed
- **WHEN** running `make corpus-backup`, `make corpus-restore`, or `make corpus-list`
- **THEN** the commands SHALL fail with "No rule to make target"

### Requirement: Clean Tests Target
The Makefile SHALL NO LONGER include a `clean-tests` target.

**Reason**: Test cleanup is covered by the `d` (clean dev) target.

**Migration**: Use `make d` to clean development environment including test artifacts.

#### Scenario: clean-tests target removed
- **WHEN** running `make clean-tests`
- **THEN** the command SHALL fail with "No rule to make target"

### Requirement: Detailed Help Files
The Makefile SHALL NO LONGER include `deploy/help.mk` or `utils/help.mk` files.

**Reason**: Overly detailed help targets are unnecessary. The basic `make help` output is sufficient.

**Migration**: Use `make help` for target documentation.

#### Scenario: help files removed
- **WHEN** checking for `deploy/help.mk` or `utils/help.mk`
- **THEN** these files SHALL NOT exist

### Requirement: Production Backup Target
The Makefile SHALL NO LONGER include a `backup-prod` target.

**Reason**: Production backup operations should be documented in ops guides rather than exposed as make targets.

**Migration**: Refer to ops documentation for production backup procedures.

#### Scenario: backup-prod target removed
- **WHEN** running `make backup-prod`
- **THEN** the command SHALL fail with "No rule to make target"

## MODIFIED Requirements

### Requirement: Essential Makefile Targets
The Makefile SHALL retain only essential targets for development, deployment, and utilities.

#### Scenario: Essential targets remain functional
- **WHEN** running essential make targets
- **THEN** the following SHALL work: `b`, `f`, `d`, `reset`, `stop-wizard`, `p`, `dp`, `sp`, `s`, `ds`, `l`, `c`, `venv`, `health`, `help`

#### Scenario: Help target works without help.mk
- **WHEN** running `make help`
- **THEN** it SHALL display available targets without errors
- **AND** it SHALL NOT require `deploy/help.mk` or `utils/help.mk`
