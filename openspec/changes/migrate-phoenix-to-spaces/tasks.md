# Implementation Tasks: Migrate Phoenix to Spaces

## Configuration Changes

- [x] Add `PHOENIX_SPACE_ID=aiinfra` to `config/.env.template` with clear documentation comment
- [x] Update `PHOENIX_COLLECTOR_ENDPOINT` to `https://app.phoenix.arize.com/s/aiinfra` in `config/.env.template`
- [x] Update `config/.env.development` with `PHOENIX_SPACE_ID=aiinfra` and space-based endpoint
- [x] Update `config/.env.staging` with `PHOENIX_SPACE_ID=aiinfra` and space-based endpoint
- [x] Update `config/.env.production` with `PHOENIX_SPACE_ID=aiinfra` and space-based endpoint
- [x] Document that `aiinfra` is the AIINFRA project space containing all ATLAS variants

## API Key Permissions (CRITICAL)

- [ ] **Verify API key has write access to `aiinfra` space in Phoenix Cloud**
  - [ ] Log into Phoenix Cloud Settings for `aiinfra` space
  - [ ] Check API Keys section - ensure current key has access OR create new space-specific key
  - [ ] Test: Submit query with telemetry and verify traces appear in `https://app.phoenix.arize.com/s/aiinfra/projects`
  - [ ] If using new key, update all environment files with new key value

## Core Telemetry Updates (PRIMARY)

- [x] Verify `backend/telemetry/core.py:134` correctly constructs trace endpoint from space-based URL
  - Currently: `f"{phoenix_endpoint}/v1/traces"`
  - Should work with: `https://app.phoenix.arize.com/s/{space-id}/v1/traces`
- [x] Add validation to check `PHOENIX_SPACE_ID` is configured when using default endpoint
- [ ] Test OTEL trace export with space-based endpoint in development

## Phoenix Client Updates

- [x] Review `backend/services/phoenix_client.py` usage of `PHOENIX_COLLECTOR_ENDPOINT`
  - Line 362: `_check_span_has_user_feedback` API call
  - Line 412: `_get_span_feedback_annotations` API call
  - Line 589: `check_user_already_rated` API call
  - Line 656: `get_inter_rater_count` API call
- [x] Verify all Phoenix API calls work with space-based URLs
- [x] Test inter-rater functionality with space configuration

## Feedback System Updates

- [x] Review `backend/telemetry/feedback.py:224` usage of `PHOENIX_COLLECTOR_ENDPOINT`
- [x] Test feedback annotation submission to space-based endpoint

## Backup Script Updates (SECONDARY)

- [x] Update `utils/scripts/phoenix_backup_prod.py`:
  - [x] Add `PHOENIX_SPACE_ID` environment variable support with default `aiinfra`
  - [x] Change default `PHOENIX_BASE_URL` from `/legacy` to `/s/aiinfra`
  - [x] Update line 125-128 logic to construct `https://app.phoenix.arize.com/s/aiinfra`
  - [x] Enforce explicit configuration when `PHOENIX_SPACE_ID` is missing (no fallback)
- [x] Update script docstring (lines 8, 13) with new default URL: `https://app.phoenix.arize.com/s/aiinfra`
- [x] Add validation error if space ID cannot be determined

## Documentation Updates

- [x] Update `docs/configuration.md`:
  - [x] Add `PHOENIX_SPACE_ID=aiinfra` configuration section explaining AIINFRA project space
  - [x] Update `PHOENIX_COLLECTOR_ENDPOINT` examples to `https://app.phoenix.arize.com/s/aiinfra` (line 152)
  - [x] Explain organizational structure: space = research project boundary
  - [x] Document that all ATLAS variants (Hansard, Darwin) use same `aiinfra` space
  - [x] Update troubleshooting section for space-related issues
- [x] Update `docs/backups.md`:
  - [x] Update backup configuration section with `aiinfra` space (line 46)
  - [x] Add example showing `PHOENIX_SPACE_ID=aiinfra`
  - [x] Update troubleshooting for backup connectivity with space URLs
- [x] Update `docs/production.md`:
  - [x] Update Phoenix configuration section to use `aiinfra` space (line 118)
  - [x] Add `PHOENIX_SPACE_ID=aiinfra` to production setup checklist
  - [x] Document production space configuration
- [x] Migration guide covered in existing documentation:
  - [x] Space architecture explained in `docs/configuration.md` Phoenix Spaces section
  - [x] All ATLAS variants sharing the space documented
  - [x] Configuration updates documented per-environment in `.env.template`
  - [x] Verification steps in `docs/production.md` checklist
  - [x] Troubleshooting in `docs/configuration.md` and `docs/backups.md`

## Testing

- [ ] Test core telemetry with space-based endpoint:
  - [ ] Verify traces appear in correct Phoenix space
  - [ ] Test trace export and span creation
  - [ ] Verify parent-child span relationships maintained
- [x] Test Phoenix Client operations:
  - [x] Query spans with feedback
  - [x] Fetch annotations
  - [x] Check inter-rater counting
- [x] Test feedback system:
  - [x] Submit user feedback
  - [x] Verify feedback annotations in Phoenix space
  - [x] Test inter-rater feedback submission
- [ ] Test backup script:
  - [ ] Run backup with space configuration
  - [ ] Verify exported data matches Phoenix UI
  - [ ] Check annotations are properly merged
- [x] Test with missing `PHOENIX_SPACE_ID`:
  - [x] Verify clear error handling
  - [x] Verify strict no-fallback behavior
- [x] Test backward compatibility:
  - [x] Verify explicit URL overrides still work
  - [x] Test migration transition period

## Deployment

- [x] Update development environment:
  - [x] Set `PHOENIX_SPACE_ID=aiinfra` in `.env.development`
  - [x] Set `PHOENIX_COLLECTOR_ENDPOINT="https://app.phoenix.arize.com/s/aiinfra"`
  - [ ] Test all Phoenix functionality
  - [ ] Verify telemetry appears in aiinfra space in Phoenix UI
- [x] Update staging environment:
  - [x] Set `PHOENIX_SPACE_ID=aiinfra` in `.env.staging`
  - [x] Set `PHOENIX_COLLECTOR_ENDPOINT="https://app.phoenix.arize.com/s/aiinfra"`
  - [ ] Deploy and test
  - [ ] Verify traces appear in aiinfra space
  - [ ] Monitor for errors
- [ ] Prepare production deployment:
  - [ ] Confirm aiinfra space access for production
  - [ ] Create deployment runbook
  - [ ] Plan rollback procedure
- [x] Update production environment configuration:
  - [x] Set `PHOENIX_SPACE_ID=aiinfra` in `.env.production`
  - [x] Set `PHOENIX_COLLECTOR_ENDPOINT="https://app.phoenix.arize.com/s/aiinfra"`
  - [ ] Restart services
  - [ ] Monitor telemetry flow to aiinfra space
  - [ ] Verify backup script connects to aiinfra space

## Post-Migration

- [ ] Monitor Phoenix connectivity across all environments (24 hours)
- [ ] Verify all traces appear in `aiinfra` space (not legacy)
- [ ] Confirm all ATLAS projects visible: Hansard-Dev, Hansard-Staging, Hansard-Prod
- [ ] Confirm backups retrieve data from `aiinfra` space successfully
- [ ] Document aiinfra space for ATLAS Darwin team to use same configuration
- [ ] Update GitHub issue #58 with completion status
- [ ] Archive this OpenSpec change after successful deployment
