## MODIFIED Requirements

### Requirement: Manifest Cache MUST Be Invalidated After Corpus Build

After the corpus wizard copies a new manifest to `backend/targets/manifest.json`, the system MUST invalidate the in-memory manifest cache in `manifest_loader.py` so that subsequent API requests return the updated manifest data without requiring a server restart.

#### Scenario: New corpus build refreshes cached manifest

- **GIVEN** a corpus has been built and the manifest is cached in memory by `manifest_loader.py`
- **WHEN** the corpus wizard copies the new manifest to `backend/targets/manifest.json`
- **THEN** the in-memory cache MUST be invalidated immediately
- **AND** the next API request to the Vector Store Overview MUST return data from the new manifest
