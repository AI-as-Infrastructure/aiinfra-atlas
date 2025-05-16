# ATLAS Configuration Management

This directory contains the centralized configuration system for the ATLAS application. It manages both sensitive and non-sensitive configuration values across all environments and application components.

## Overview

The ATLAS configuration system follows these key principles:
- **Centralization**: All configuration files are stored in this directory
- **Separation of Concerns**: Sensitive and non-sensitive information are kept in separate files
- **Consistency**: The same configuration approach is used across all environments
- **Security**: Sensitive information is properly secured and not committed to version control

## Configuration Files

| File | Purpose | Contains Secrets? | Version Controlled? |
|------|---------|-------------------|---------------------|
| `.env` | Non-sensitive configuration | No | Yes (template only) |
| `.secrets` | Sensitive information (API keys, passwords) | Yes | No |
| `.env.template` | Template for `.env` file | No | Yes |
| `.secrets.template` | Template for `.secrets` file | No | Yes |
| `.vault_pass` | Ansible Vault password file | Yes | No |
| `requirements.txt` | Python dependencies | No | Yes |
| `requirements.lock` | Pinned Python dependencies | No | Yes |

## Secrets Management Process

### Development Environment

1. **Initial Setup**:
   - Copy `.env.template` to `.env` and fill in your environment-specific values
   - Copy `.secrets.template` to `.secrets` and fill in your sensitive information
   - Both files should be in the `config/` directory

2. **Environment Loading**:
   - `deploy/dev/dev.sh` loads variables from both files
   - Python applications use the `secrets_manager.py` module to access these variables
   - Frontend uses `setup_react_env.sh` to generate its environment file

3. **Frontend Integration**:
   - `setup_react_env.sh` extracts all `REACT_APP_*` variables from both `.env` and `.secrets`
   - These variables are written to `frontend/.env` for use by the React application
   - The React application uses the `envConfig.js` utility to access these variables

### Docker and Staging Environment

The Docker build process uses these configuration files to create a single image for staging:

1. Docker builds use the `.env` file for non-sensitive configuration
2. Sensitive information from `.secrets` is injected at runtime via environment variables
3. The Ansible staging playbook manages secrets deployment using encrypted vault files

### Production Environment

In production, secrets are managed through a dedicated Ansible role:

1. Secrets are stored securely in the Ansible vault, encrypted with the password in `.vault_pass`
2. The production playbook uses this vault password to decrypt secrets during deployment
3. The application service is configured to use these secrets at runtime

## Scripts

| Script | Purpose |
|--------|---------|
| `setup_react_env.sh` | Generates the frontend environment file from `.env` and `.secrets` |
| `secrets_manager.py` | Python module for accessing configuration values |

## Usage Examples

### Accessing Configuration in Python

```python
from secrets_manager import get_secret

# Access a non-sensitive configuration value
debug_mode = get_secret("DEBUG_MODE", default="False")

# Access a sensitive configuration value
api_key = get_secret("OPENAI_API_KEY")
```

### Accessing Configuration in React

```javascript
import envConfig from './utils/envConfig';

// Access a configuration value
const siteTitle = envConfig.appTitle;

// Access authentication configuration
const clientId = envConfig.auth.clientId;
```

## Security Considerations

1. **Never commit** `.env`, `.secrets`, or `.vault_pass` files to version control
2. Ensure proper file permissions are set on these files (e.g., `chmod 600`)
3. In production, use environment-specific secrets management with Ansible vault
4. Regularly rotate sensitive credentials and the vault password
5. The `.vault_pass` file should be distributed securely to team members who need deployment access

## Testing

To test the configuration system:

1. Backend: Run `python -m unittest discover tests`
2. Frontend: Run `./frontend/test_env_integration.sh`

## Troubleshooting

If you encounter issues with configuration:

1. Verify that both `.env` and `.secrets` files exist in the `config/` directory
2. Check that all required variables are defined
3. Ensure the correct Python version (3.10) is being used
4. Check file permissions on the configuration files
