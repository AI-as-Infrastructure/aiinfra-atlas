# Implementation Tasks: Fix Reset Stale State and Error Logging

## 1. Reset VITE_SITE_TITLE During `make reset`

- [x] 1.1 Add step to `deploy/dev/scripts/reset_dev.sh` to reset `VITE_SITE_TITLE` in `config/.env.development` to `"ATLAS"`
- [ ] 1.2 Test: run `make reset` and verify `VITE_SITE_TITLE="ATLAS"` in `config/.env.development` (manual test)
- [ ] 1.3 Test: rebuild corpus with wizard, confirm new title is set, then `make reset` and confirm title reverts to default (manual test)

## 2. Remove Stale Manifest During `make reset`

- [x] 2.1 Add `backend/targets/manifest.json` removal to `deploy/dev/scripts/reset_dev.sh` Step 5 (targets cleanup)
- [ ] 2.2 Test: run `make reset` and verify `backend/targets/manifest.json` is removed (manual test)

## 3. Add exc_info to Streaming Error Log

- [x] 3.1 Change `response.py:138` from `logger.error(f"Error during streaming: {e}")` to `logger.error(f"Error during streaming: {e}", exc_info=True)`
- [x] 3.2 Verified: the telemetry-enabled path at `response.py:336` already includes `exc_info=True` — no change needed

## 4. Invalidate Manifest Cache After Corpus Build

- [x] 4.1 Add `invalidate_cache()` call at `corpus_wizard.py:1496-1499` after copying manifest to targets
- [x] 4.2 Add fallback: if `results['manifest_path']` is missing or stale, copy from `backend/corpus/manifest.json` instead
- [ ] 4.3 Test: build a new corpus and verify Vector Store Overview shows the new manifest data without server restart (manual test — requires running app)
