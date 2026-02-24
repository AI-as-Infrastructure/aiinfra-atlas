# Fix Reset Stale State and Error Logging

## Summary

Fix four issues discovered during testing of the `fix-manifest-parsing-and-streaming-regression` changes: (1) `make reset` does not reset `VITE_SITE_TITLE` in `.env.development`, leaving the old corpus title persisted, (2) `make reset` does not remove `backend/targets/manifest.json`, so the Vector Store Overview shows stale corpus metadata, and `manifest_loader.py` never invalidates its in-memory cache, (3) the LLM streaming error at `response.py:138` logs without `exc_info=True`, so no traceback is captured for diagnosis, and (4) `manifest_loader.py` cache is never invalidated after a new corpus build.

## Motivation

- **VITE_SITE_TITLE persists after reset** — `make reset` (`deploy/dev/scripts/reset_dev.sh`) removes corpus data, configs, targets (`.txt` files only), and wizard state, but does NOT touch `config/.env.development`. The `VITE_SITE_TITLE` value written by a previous corpus wizard build persists across resets. Users expect `make reset` to return the system to a clean first-install state, but the UI title still shows the old corpus name.

- **Stale manifest after reset + rebuild** — The reset script removes `backend/targets/*.txt` but NOT `backend/targets/manifest.json`. After reset, the old manifest remains. After a new corpus build, the wizard copies the new manifest to `backend/targets/manifest.json` (`corpus_wizard.py:1487-1492`), but `manifest_loader.py` caches the manifest in a module-level variable (`_manifest_cache`) and the `invalidate_cache()` function at line 118 is never called anywhere in the codebase. The stale cached manifest is served until the server restarts.

- **Missing traceback in streaming error log** — At `response.py:138`, the error is logged as `logger.error(f"Error during streaming: {e}")` without `exc_info=True`. The telemetry-enabled code path at line 335 does include `exc_info=True`. Without the traceback, diagnosing LLM provider failures on the non-telemetry path is difficult.

- **Manifest cache never invalidated** — `manifest_loader.py:118` defines `invalidate_cache()` but no code calls it. The corpus wizard copies the new manifest file to `backend/targets/manifest.json` but does not invalidate the in-memory cache, so stale data is served until a server restart.

## Detailed Design

### 1. Reset VITE_SITE_TITLE During `make reset`

Add a step to `deploy/dev/scripts/reset_dev.sh` (after Step 3, configuration removal) that resets the `VITE_SITE_TITLE` line in `config/.env.development` to the generic default `"ATLAS"`.

The approach:
- Use `sed` to replace any existing `VITE_SITE_TITLE=...` line with `VITE_SITE_TITLE="ATLAS"` — the generic default that matches the frontend fallback at `App.vue:61` (`import.meta.env.VITE_SITE_TITLE || 'ATLAS'`)
- Only modify this specific line — do not replace the entire `.env.development` file, as it contains user-configured API keys and other settings that should survive a reset
- If `config/.env.development` does not exist, skip silently (the file is created from the template during first setup)

### 2. Remove Stale Manifest During `make reset`

Add manifest cleanup to `deploy/dev/scripts/reset_dev.sh` in the targets section (Step 5):
- Remove `backend/targets/manifest.json` alongside the existing `*.txt` cleanup
- This ensures Vector Store Overview starts clean after reset

### 3. Add exc_info to Streaming Error Log

At `backend/modules/response.py:138`, change:
```python
logger.error(f"Error during streaming: {e}")
```
to:
```python
logger.error(f"Error during streaming: {e}", exc_info=True)
```

This matches the pattern already used at `response.py:335` on the telemetry-enabled path.

### 4. Invalidate Manifest Cache After Corpus Build

At `backend/routers/corpus_wizard.py:1491-1492`, after copying the manifest to `backend/targets/manifest.json`, call `invalidate_cache()`:
```python
shutil.copy2(manifest_source, manifest_dest)
logger.info(f"Copied manifest to: {manifest_dest}")
# Invalidate cached manifest so the new data is served immediately
from backend.modules.manifest_loader import invalidate_cache
invalidate_cache()
```

This ensures the in-memory manifest cache is refreshed without requiring a server restart.

## Scope

Bug fixes only — restore expected behaviour after `make reset` and improve error diagnostics. No new features.

## Risks

- Modifying `.env.development` via `sed` in the reset script could corrupt the file if the `VITE_SITE_TITLE` line has an unexpected format. The `sed` command should be specific enough to avoid this.
- Invalidating the manifest cache during a build is safe since the new manifest file has already been written to disk.
