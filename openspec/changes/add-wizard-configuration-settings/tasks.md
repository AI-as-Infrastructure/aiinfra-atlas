# Implementation Tasks

## Frontend Components

### Wizard Structure Updates
- [x] Update `frontend/src/views/CorpusWizard.vue` to add new configuration step
- [x] Shift step numbers for all subsequent steps (+1)
- [x] Update step navigation logic to handle new step

### New Configuration Component
- [x] Create `frontend/src/components/wizard/SystemConfiguration.vue`
- [x] Implement telemetry toggle with description
- [x] Implement inter-rater feedback toggle with description
- [x] Add form validation for configuration settings
- [x] Style component to match existing wizard aesthetic

### State Management
- [x] Add configuration state to wizard data model
- [x] Update wizard data validation to include configuration
- [x] Ensure configuration persists through wizard navigation

## Backend Implementation

### Configuration Management
- [x] Create `backend/modules/system_configuration.py` module
- [x] Implement configuration file reader/writer
- [x] Add configuration validation logic
- [x] Create configuration merge strategy (file + env vars)

### API Endpoints
- [x] Create `backend/routers/system.py` router module
- [x] Implement `POST /api/system/configuration` endpoint
- [x] Add request/response models with Pydantic
- [x] Add appropriate authentication checks
- [x] Implement configuration persistence logic

### Runtime Configuration
- [x] Update `backend/app.py` to read system_settings.json on startup
- [x] Modify telemetry initialization to respect runtime settings
- [x] Update inter-rater feedback checks to use runtime configuration
- [x] Ensure environment variables can still override file settings

### Configuration File
- [x] Create default `config/system_settings.json` template
- [x] Add system_settings.json to .gitignore
- [x] Document configuration file format

## Integration Points

### Telemetry Integration
- [x] Update `backend/telemetry/core.py` to check runtime configuration
- [x] Modify telemetry initialization logic
- [x] Add configuration change logging
- [x] Test telemetry enable/disable at runtime

### Inter-Rater Integration
- [x] Update inter-rater feedback endpoints to check runtime config
- [x] Modify feedback UI components to respect settings
- [x] Hide/show feedback buttons based on configuration
- [x] Update `backend/routers/core.py` health check response

## Testing

### Unit Tests
- [ ] Test SystemConfiguration.vue component
- [ ] Test configuration validation logic
- [ ] Test configuration file read/write operations
- [ ] Test configuration merge strategy

### Integration Tests
- [ ] Test configuration endpoint with valid data
- [ ] Test configuration endpoint with invalid data
- [ ] Test configuration persistence across restarts
- [ ] Test environment variable overrides

### E2E Tests
- [ ] Test complete wizard flow with configuration step
- [ ] Test configuration changes take effect immediately
- [ ] Test navigation back/forward through configuration step
- [ ] Test configuration validation in wizard

## Documentation

### User Documentation
- [ ] Update wizard documentation to include configuration step
- [ ] Document privacy implications of settings
- [ ] Add configuration FAQ section

### Developer Documentation
- [ ] Document configuration precedence (env > file > defaults)
- [ ] Update deployment guide with configuration options
- [ ] Document configuration API endpoint

## Deployment Considerations

### Migration
- [ ] Create migration script for existing deployments
- [ ] Set safe defaults for existing installations
- [ ] Test upgrade path from current version

### Security
- [ ] Implement file permission checks for config file
- [ ] Add rate limiting to configuration endpoint
- [ ] Implement audit logging for configuration changes
- [ ] Validate all input to prevent injection attacks

## Rollback Plan

### If Issues Occur
- [ ] Document rollback procedure
- [ ] Ensure environment variables continue to work as fallback
- [ ] Test rollback scenario
- [ ] Prepare hotfix branch if needed

## Completion Criteria

- [ ] All toggles functional in wizard
- [ ] Settings persist across sessions
- [ ] Telemetry respects configuration
- [ ] Inter-rater feedback respects configuration
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Code reviewed and approved