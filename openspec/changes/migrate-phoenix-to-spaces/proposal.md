# Change: Migrate Phoenix from Legacy to Spaces Architecture

## Why
Phoenix's legacy endpoint structure has been deprecated by Arize. Projects currently default to `https://app.phoenix.arize.com/legacy/projects` instead of the new spaces-based structure `https://app.phoenix.arize.com/s/{space-id}/projects`. This affects both core telemetry (OTEL traces) and backup functionality. The timeline for legacy support is uncertain, creating maintenance risk for ATLAS infrastructure.

The new spaces architecture provides organizational benefits: each space represents a research project boundary with independent isolation and access control. The AIINFRA project will use the `aiinfra` space, containing all ATLAS variants (Hansard, Darwin, and future variants). This allows future organizational projects to have their own isolated spaces.

**GitHub Issue**: #58

## What Changes
- **PRIMARY**: Update core telemetry to use space-based `PHOENIX_COLLECTOR_ENDPOINT`
  - Change from `https://app.phoenix.arize.com` to `https://app.phoenix.arize.com/s/aiinfra`
  - Set `PHOENIX_SPACE_ID=aiinfra` for AIINFRA project space
  - Update OTEL trace export to use space-based URLs
  - All ATLAS variants (Hansard, Darwin) will use same `aiinfra` space with different project names
- **SECONDARY**: Update backup script to use space-based URLs
  - Change `PHOENIX_BASE_URL` default from `/legacy` to `/s/aiinfra`
  - Align backup configuration with core telemetry configuration
- Update all environment files (.env.template, .env.development, .env.staging, .env.production)
- Update all documentation with space architecture
- **Non-breaking**: Explicit URL overrides still work during transition

## Impact
- **Affected specs**: Phoenix integration (new capability spec)
- **Affected code**:
  - `config/.env.template:191` - Update `PHOENIX_COLLECTOR_ENDPOINT` default
  - `backend/telemetry/core.py:134` - Uses `PHOENIX_COLLECTOR_ENDPOINT` + `/v1/traces`
  - `backend/services/phoenix_client.py:362,412,589,656` - Uses `PHOENIX_COLLECTOR_ENDPOINT`
  - `backend/telemetry/feedback.py:224` - Uses `PHOENIX_COLLECTOR_ENDPOINT`
  - `utils/scripts/phoenix_backup_prod.py:125,128` - Update `PHOENIX_BASE_URL` default
- **Affected documentation**:
  - `docs/configuration.md:152` - Phoenix configuration examples
  - `docs/backups.md:46` - Backup configuration
  - `docs/production.md:118` - Production setup
- **Breaking change**: All environments must update to use `aiinfra` space
- **Migration required**: All environments (dev, staging, production) need configuration updates
- **ATLAS Darwin fork**: Must also update to use same `aiinfra` space

## Organizational Structure
```
Organization
└── Space: aiinfra (AIINFRA research project)
    └── Projects:
        ├── ATLAS-Hansard-Dev
        ├── ATLAS-Hansard-Staging
        ├── ATLAS-Hansard-Prod
        ├── ATLAS-Darwin-Dev
        └── ATLAS-Darwin-Prod
```

Future organizational research projects will create their own isolated spaces.

## Migration Path
1. **Space ID**: Use `aiinfra` for all AIINFRA project environments
2. **Update configuration**: Set `PHOENIX_SPACE_ID=aiinfra` and `PHOENIX_COLLECTOR_ENDPOINT="https://app.phoenix.arize.com/s/aiinfra"` in all `.env` files
3. **Test connectivity**: Verify telemetry and backups work with new configuration
4. **Deploy sequentially**: Development → Staging → Production
5. **Update Darwin fork**: Apply same configuration to ATLAS Darwin codebase
