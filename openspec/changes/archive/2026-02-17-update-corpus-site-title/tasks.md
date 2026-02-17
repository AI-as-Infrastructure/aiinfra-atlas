# Tasks for update-corpus-site-title

## Implementation

- [x] Add VITE_SITE_TITLE update logic to corpus build completion in backend/routers/corpus_wizard.py
- [x] Extract display_name from corpus manifest after successful build
- [x] Use mode_manager to determine which environment file to update
- [x] Update VITE_SITE_TITLE value in the appropriate .env file
- [x] Add logging for the title update operation

## Testing

- [x] Build a test corpus with custom display_name
- [x] Verify .env.development contains updated VITE_SITE_TITLE
- [x] Restart frontend and verify title displays correctly
- [x] Test with different runtime modes (development, deploy)
- [x] Verify existing corpus builds still work correctly

## Documentation

- [x] Add note to corpus wizard documentation about title updates
- [x] Document that frontend restart may be needed for title changes