# Documentation Overhaul

Documentation must accurately reflect the wizard-driven architecture and guide users through the current system.

## ADDED Requirements

### Requirement: Wizard-first quick start in README
The README quick start guide MUST lead users through: clone -> install dependencies -> start servers -> open browser -> System Mode page -> corpus wizard.

#### Scenario: New user follows README
- **Given** a user clones the repository
- **When** they follow the Quick Start instructions
- **Then** they are guided to the System Mode page and corpus wizard, not Git LFS or manual commands

### Requirement: corpus_active.json documented as central config
Documentation MUST explain that corpus_active.json (created by deploy mode from manifest data) is the central runtime configuration, replacing environment variables for corpus settings.

#### Scenario: Developer looks up how configuration works
- **Given** a developer reads configuration.md
- **When** they look for how corpus settings are configured
- **Then** they find corpus_active.json documented as the primary source, with .env files documented only for non-corpus settings (API keys, Redis, telemetry)

### Requirement: Configure/deploy mode workflow documented
Documentation MUST explain the System Mode page, the one-way configure-to-deploy transition, and the role of ModeSelector.vue as the application entry point.

#### Scenario: User wants to understand the mode system
- **Given** a user reads the runtime mode documentation
- **When** they look for how modes work
- **Then** they find: System Mode page as entry point, configure mode for wizard/settings, deploy mode locks configuration, server restart required to reconfigure

### Requirement: backend/corpus/ directory structure documented
Documentation MUST explain that backend/corpus/ contains all wizard-generated build artifacts: manifest.json, corpus_active.json, adapter .py, chroma_db/, bm25_corpus.jsonl, corpus_config.yaml.

#### Scenario: Developer investigates the corpus directory
- **Given** a developer reads the architecture documentation
- **When** they look for where corpus files are stored
- **Then** they find backend/corpus/ documented as the active corpus directory, distinct from backend/targets/

### Requirement: CLAUDE.md reflects current architecture
The AI assistant instructions MUST include corpus wizard workflow, corpus_active.json, configure/deploy modes, backend/corpus/ structure, and ModeSelector.vue as landing page.

#### Scenario: AI assistant reads CLAUDE.md for context
- **Given** an AI assistant loads CLAUDE.md
- **When** it reads the architecture and setup sections
- **Then** it understands the wizard-driven workflow without references to Git LFS vector stores

## MODIFIED Requirements

### Requirement: README removes Git LFS vector store references
All references to pulling a default vector store via Git LFS, mean pooling fallback, and manual `make vs` commands MUST be removed or replaced with wizard instructions.

#### Scenario: User reads README setup instructions
- **Given** a user reads the README
- **When** they look for vector store setup
- **Then** they find wizard instructions, not Git LFS pull commands

### Requirement: development.md uses wizard as primary setup path
The development guide MUST describe: install prerequisites, start backend/frontend, navigate to System Mode page, run corpus wizard to build first corpus, deploy, test.

#### Scenario: New developer sets up the project
- **Given** a developer follows development.md
- **When** they complete all setup steps
- **Then** they have a working corpus built via the wizard, not via Git LFS or manual scripts

### Requirement: configuration.md separates wizard-managed from env-managed config
Configuration documentation MUST clearly distinguish: (a) corpus settings managed by the wizard and stored in manifest.json/corpus_active.json, (b) infrastructure settings in .env files (API keys, Redis, telemetry, auth).

#### Scenario: Developer changes a corpus setting
- **Given** a developer reads configuration.md
- **When** they want to change embedding model or chunk size
- **Then** they are directed to rebuild via the wizard, not edit environment variables

#### Scenario: Developer changes an API key
- **Given** a developer reads configuration.md
- **When** they want to change an LLM provider API key
- **Then** they are directed to the .env file, not corpus_active.json

### Requirement: create_store.md positions wizard as primary method
The vector store creation guide MUST present the corpus wizard as the standard method, with manual creation documented as an advanced alternative for edge cases.

#### Scenario: User wants to create a vector store
- **Given** a user reads create_store.md
- **When** they look for how to create a vector store
- **Then** the wizard is presented first, with manual CLI creation as a secondary "Advanced" section

### Requirement: manifest.md updated to v1.4 schema and correct paths
Manifest documentation MUST reference backend/corpus/manifest.json as the canonical location and document the v1.4 schema including build environment, inter-rater config, and filters.

#### Scenario: Developer reads manifest schema
- **Given** a developer reads manifest.md
- **When** they check the manifest location and schema
- **Then** they find backend/corpus/manifest.json with v1.4 fields including build section

### Requirement: test_targets.md explains wizard-generated targets
Test target documentation MUST explain that the wizard generates target .txt files in backend/targets/, with manual creation documented as an advanced option.

#### Scenario: User wants to add a test target
- **Given** a user reads test_targets.md
- **When** they look for how to create a target
- **Then** they are guided to the wizard first, with manual .txt file creation as advanced

### Requirement: key_modules.md includes wizard modules
The backend architecture documentation MUST include corpus_wizard.py, corpus_builder.py, corpus_analyzer.py, manifest_loader.py, mode_manager.py, and the backend/corpus/ directory structure.

#### Scenario: Developer explores backend architecture
- **Given** a developer reads key_modules.md
- **When** they look for the module list
- **Then** they find wizard-related modules documented alongside retrieval and LLM modules

### Requirement: production.md includes wizard setup in deployment workflow
Production documentation MUST include: run wizard to build corpus, verify configuration, enter deploy mode, then proceed with server deployment.

#### Scenario: Admin deploys ATLAS to production
- **Given** an admin follows production.md
- **When** they complete the deployment checklist
- **Then** the checklist includes corpus wizard setup and deploy mode activation

### Requirement: All file paths updated from backend/targets/ to backend/corpus/
Any documentation referencing backend/targets/manifest.json, backend/targets/chroma_db/, or backend/targets/ as the primary corpus location MUST be updated to backend/corpus/.

#### Scenario: Developer searches docs for manifest path
- **Given** a developer searches documentation for manifest.json
- **When** they find path references
- **Then** the primary path is backend/corpus/manifest.json, with backend/targets/ mentioned only for legacy context or target .txt files

### Requirement: Minor docs updated with wizard prerequisites and correct paths
RAG_search.md, authentication.md, staging.md, telemetry.md, health_monitoring.md, load_testing.md, gpu_compatibility.md, testing.md, backups.md, and analysis.md MUST have path corrections and wizard prerequisite notes where relevant.

#### Scenario: User reads a secondary doc that references corpus paths
- **Given** a user reads any documentation file
- **When** they encounter corpus-related paths or configuration
- **Then** paths point to backend/corpus/ and configuration references corpus_active.json or the wizard

## REMOVED Requirements

### Requirement: Remove corpus_wizard_integration.md
The historical integration fixes document should be archived; any still-relevant content merged into docs/corpus_wizard.md.

#### Scenario: Developer looks for wizard integration docs
- **Given** a developer searches for wizard integration information
- **When** they look in docs/
- **Then** they find current information in corpus_wizard.md, not a historical fixes document

### Requirement: Remove all Git LFS vector store distribution references
All documentation describing the pre-built Hansard vector store, Git LFS pull commands, mean pooling fallback, and `make vs` commands for initial setup must be removed.

#### Scenario: User searches for Git LFS instructions
- **Given** a user searches documentation for "git lfs" or "default vector store"
- **When** they look for setup instructions
- **Then** they find no references to pulling a pre-built vector store
