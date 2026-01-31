# Runtime Mode System - Environment File Handling

## Overview

The runtime mode management system properly handles different environment files (development, staging, production) while respecting the mode state (configure vs deploy).

## Key Improvements

### 1. Environment-Specific Updates

The system now only updates the **current** environment's .env file, determined by the `ENVIRONMENT` variable:
- If `ENVIRONMENT=development`, only `config/.env.development` is modified
- If `ENVIRONMENT=staging`, only `config/.env.staging` is modified
- If `ENVIRONMENT=production`, only `config/.env.production` is modified

### 2. Mode-Aware File Modifications

**Configure Mode:**
- Allows updating .env files for persistent configuration
- Updates both the file AND runtime environment variables
- Changes persist across server restarts

**Deploy Mode:**
- **NO** .env file modifications allowed
- Only updates runtime environment variables (in-memory)
- Changes are temporary and lost on server restart
- Ensures configuration consistency during testing

### 3. Updated Functions

The following functions have been updated to respect mode and environment:

#### `set_default_target()` (corpus_wizard.py:1780-1839)
- In configure mode: Updates current environment's .env file
- In deploy mode: Only updates runtime `os.environ["TEST_TARGET"]`

#### Target Configuration Generation (corpus_wizard.py:1260-1295)
- In configure mode: Updates TEST_TARGET in current .env file
- In deploy mode: Only updates runtime environment
- Always generates the target .txt file (needed for target management)

#### VITE_SITE_TITLE Update (corpus_wizard.py:1297-1339)
- In configure mode: Updates current .env file
- In deploy mode: Skip file updates (frontend title won't change)

#### RETRIEVER_MODULE Update (corpus_wizard.py:1397-1439)
- In configure mode: Updates current .env file
- In deploy mode: Only updates runtime environment

## Usage Examples

### Development Environment
```bash
# Start with development environment
export ENVIRONMENT=development
make b  # Starts backend

# In configure mode:
# - Changes update config/.env.development
# - Other .env files remain unchanged

# In deploy mode:
# - No files are modified
# - Runtime changes only
```

### Staging Environment
```bash
# Start with staging environment
export ENVIRONMENT=staging
make s  # Starts staging

# In configure mode:
# - Changes update config/.env.staging
# - Development and production files unchanged

# In deploy mode:
# - No files are modified
```

### Production Environment
```bash
# Start with production environment
export ENVIRONMENT=production
make p  # Starts production

# Usually starts directly in deploy mode
# Configuration changes require server restart
```

## Benefits

1. **Environment Isolation**: Each environment maintains its own configuration
2. **Deploy Mode Safety**: No accidental configuration changes during testing
3. **Runtime Flexibility**: Can temporarily switch targets in deploy mode without affecting persistent config
4. **Clear Separation**: Configure mode for setup, deploy mode for testing

## Mode Transitions

```
Server Start
    ↓
Configure Mode (default)
    ├── Build corpus
    ├── Add/modify targets
    ├── Updates current .env file
    └── Enter Deploy Mode → [One-way lock]
                              ↓
                          Deploy Mode
                              ├── Configuration locked
                              ├── No file modifications
                              └── Requires server restart to change
```

## Important Notes

1. The mode is **runtime state** - not stored in .env files
2. Deploy mode is **one-way** - requires server restart to unlock
3. Each environment can have different default targets and configurations
4. The system uses `ENVIRONMENT` variable to determine which .env file to use