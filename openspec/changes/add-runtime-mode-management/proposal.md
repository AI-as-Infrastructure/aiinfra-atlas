# Add Runtime Mode Management System

## Summary
Implement a runtime mode management system that separates configuration and deployment modes, replacing manual configuration file editing with a wizard-driven approach and providing clear operational boundaries for the test harness.

## Problem
Currently, ATLAS configuration requires manual editing of environment files and target configurations, making it difficult for non-technical users to set up and manage test configurations. The system lacks clear operational modes, allowing configuration changes at any time which can compromise test consistency. Additionally, the separation between expensive corpus building and cheap target configuration is not clearly expressed in the user interface.

## Solution
Introduce a runtime mode management system with two distinct operational modes:

1. **Configuration Mode**: Allows corpus building and target configuration through wizards
2. **Deploy Mode**: Locks configuration for consistent testing (one-way until server restart)

Key features:
- Runtime mode selection after authentication (no .env editing required)
- Wizard-driven configuration replacing manual file creation
- Clear separation between corpus building (expensive) and target configuration (cheap)
- One-way transition to deploy mode with explicit warnings
- Minimal environment variables (only infrastructure settings)
- Centralized configuration in `atlas_config.json`

## Capabilities
- `runtime-mode-management`: Core mode manager with state persistence
- `mode-selection-ui`: Initial mode selection interface after authentication
- `wizard-mode-integration`: Wizard completion with mode transition options
- `config-manager-ui`: Post-setup configuration management interface
- `deploy-mode-lock`: One-way deploy mode with restart requirement
- `centralized-config`: Single configuration file replacing scattered settings
- `navigation-guards`: Route protection based on current mode

## Dependencies
- Existing corpus wizard functionality
- Current authentication system
- Backend configuration module
- Existing test target system

## Risks & Mitigations
- **Risk**: Users accidentally entering deploy mode too early
  - **Mitigation**: Clear warnings and confirmation dialogs explaining the lock
- **Risk**: Users frustrated by restart requirement
  - **Mitigation**: Clear documentation and UI messaging about mode behavior
- **Risk**: Loss of manual configuration flexibility
  - **Mitigation**: Comprehensive wizard covering all configuration needs
- **Risk**: Migration complexity for existing setups
  - **Mitigation**: Automated migration script for existing configurations

## Technical Design

### Mode Manager (Backend)
```python
# backend/modules/mode_manager.py
class SystemMode(Enum):
    CONFIGURE = "configure"
    DEPLOY = "deploy"

class ModeManager:
    """Singleton managing runtime mode state"""
    - get_mode() -> SystemMode
    - set_mode(mode: SystemMode) -> dict
    - has_complete_configuration() -> bool
```

### Configuration Structure
```json
// backend/config/atlas_config.json
{
  "version": "2.0",
  "corpus": {...},
  "targets": {
    "default": "k20_claude",
    "configurations": {...}
  }
}
```

### UI Flow
1. Auth → Mode Selection
2. Configure Mode → Wizard or Config Manager
3. Deploy Mode → Chat Interface (locked)

### Environment Variables (Reduced)
```bash
# Only infrastructure settings remain
ENVIRONMENT=development
REDIS_URL=redis://localhost:6379
PHOENIX_API_KEY=xxx
# All target/corpus settings removed
```

## Validation
- Unit tests for mode manager state transitions
- Integration tests for mode-based navigation
- UI tests for mode selection and transitions
- Configuration migration tests
- Deploy mode lock verification

## Implementation Order
1. Create mode manager module
2. Implement mode selection UI
3. Update wizard with mode transitions
4. Create config manager interface
5. Add navigation guards
6. Implement configuration migration
7. Update documentation
8. Remove deprecated manual configuration