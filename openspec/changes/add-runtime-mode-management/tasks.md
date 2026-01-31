# Implementation Tasks

## Phase 1: Backend Mode Management
- [ ] Create `backend/modules/mode_manager.py` with SystemMode enum and ModeManager singleton
- [ ] Implement mode state persistence in memory (resets on server restart)
- [ ] Add `has_complete_configuration()` method checking for corpus and targets
- [ ] Create `backend/routers/mode.py` with `/api/mode/status`, `/api/mode/deploy`, `/api/mode/configure` endpoints
- [ ] Add mode-based access control decorators for protected endpoints
- [ ] Update `backend/routers/core.py` to respect mode for configuration endpoints

## Phase 2: Configuration Centralization
- [ ] Design `atlas_config.json` schema for centralized configuration
- [ ] Create configuration loader that reads from `atlas_config.json` instead of multiple sources
- [ ] Update `backend/modules/config.py` to use centralized configuration
- [ ] Remove dependency on TEST_TARGET environment variable
- [ ] Create migration script for existing configurations to new format
- [ ] Update corpus wizard to write to `atlas_config.json`

## Phase 3: Mode Selection UI
- [ ] Create `ModeSelector.vue` component for initial mode selection
- [ ] Implement mode status checking on application startup
- [ ] Add confirmation dialogs for deploy mode transition with warnings
- [ ] Style mode selection cards with clear visual distinction
- [ ] Add mode indicator in application header/navbar
- [ ] Implement "locked" state UI for deploy mode

## Phase 4: Wizard Integration
- [ ] Update `CorpusWizard.vue` final step with mode transition options
- [ ] Add "Continue Configuring" vs "Switch to Deploy" choice
- [ ] Implement configuration summary display before mode transition
- [ ] Remove manual target file creation options from UI
- [ ] Update wizard to save all settings to `atlas_config.json`
- [ ] Add validation ensuring at least one target before deploy mode

## Phase 5: Configuration Manager
- [ ] Create `ConfigManager.vue` for post-setup configuration management
- [ ] Implement target list with default selection and management
- [ ] Add "Add Test Target" functionality for existing corpus
- [ ] Create corpus rebuild option in configuration mode
- [ ] Add configuration export/import functionality
- [ ] Implement delete target with confirmation

## Phase 6: Navigation Guards
- [ ] Add route metadata for `requiresConfigure` and `requiresDeploy` flags
- [ ] Implement router beforeEach guard checking current mode
- [ ] Redirect configuration routes to chat when in deploy mode
- [ ] Redirect runtime routes to setup when configuration incomplete
- [ ] Add error messages for blocked navigation attempts
- [ ] Update all route definitions with appropriate metadata

## Phase 7: Environment Cleanup
- [ ] Remove TEST_TARGET from all .env template files
- [ ] Remove EMBEDDING_MODEL, SEARCH_K, and other config from .env
- [ ] Update deployment scripts to not require these variables
- [ ] Clean up backend code that reads these from environment
- [ ] Update documentation to reflect new minimal .env
- [ ] Create .env migration guide for existing installations

## Phase 8: Testing & Documentation
- [ ] Write unit tests for ModeManager class
- [ ] Create integration tests for mode transitions
- [ ] Test one-way deploy lock behavior
- [ ] Test configuration migration from old format
- [ ] Update user documentation with new setup flow
- [ ] Create administrator guide for mode management
- [ ] Add troubleshooting guide for mode-related issues
- [ ] Update API documentation with new endpoints

## Phase 9: Cleanup
- [ ] Remove deprecated manual configuration code
- [ ] Delete old target file parsing logic
- [ ] Remove unused environment variable readers
- [ ] Archive old configuration documentation
- [ ] Update CI/CD pipelines for new configuration approach
- [ ] Remove references to manual target creation in codebase

## Acceptance Criteria
- [ ] Users can select mode after authentication without editing files
- [ ] Configuration mode allows full wizard access and changes
- [ ] Deploy mode locks all configuration until server restart
- [ ] All configuration stored in single `atlas_config.json` file
- [ ] Environment files only contain infrastructure settings
- [ ] Clear warnings shown before entering deploy mode
- [ ] Existing configurations successfully migrated
- [ ] No manual file editing required for any configuration