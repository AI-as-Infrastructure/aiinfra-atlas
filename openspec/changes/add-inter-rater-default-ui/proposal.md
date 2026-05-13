# Change: Add inter-rater default UI mode

## Why
Focus group testing requires participants to land directly on the inter-rater page without access to the chat UI or privacy toggle. Currently users always land on the chat page and must navigate to inter-rater manually. Operators need a single env var to switch the entire UI into "inter-rater mode" for focus group sessions.

## What Changes
- New env var `INTER_RATER_DEFAULT_UI` (default `false`). When `true` (requires `INTER_RATER_ENABLED=true`):
  - Users are redirected from `/` to `/inter-rater` on navigation
  - The site title link (e.g. "ATLAS Hansard") points to `/inter-rater` instead of `/`
  - The "New Session" button in the header is hidden
  - The privacy toggle on the chat page is hidden (telemetry must be on for focus group data collection)
- The inter-rater loading message is improved to "Loading inter-rating tasks, please wait..." (applies always, not just in default UI mode)
- A new Pinia store (`stores/interRater.js`) centralises inter-rater config fetching, replacing the duplicate fetch in `InterRaterButton.vue`
- Backend exposes `default_ui` in the `/api/inter-rater/stats` response
- Documentation updated to explain the relationship between `INTER_RATER_ENABLED` and `INTER_RATER_DEFAULT_UI`

## Design Decisions
- **Runtime config via API, not VITE_ compile-time** — the flag is read from the backend via `/api/inter-rater/stats` so operators can toggle it without rebuilding the frontend. Follows the same pattern as `INTER_RATER_ENABLED`.
- **Router redirect + link change** — both the router guard and the site title link are updated for robustness. The router catches direct URL navigation to `/`; the link change prevents unnecessary redirects.
- **Shared Pinia store** — `InterRaterButton` already fetches `/inter-rater/stats` on mount. A shared store deduplicates this call across the router guard, App.vue, and the button component.
- **Privacy toggle hidden, not disabled** — in focus group mode, telemetry must be on. Hiding the toggle prevents confusion rather than showing a disabled control.

## Impact
- Affected specs: none (new UI configuration, no changes to existing spec behaviour)
- Affected code:
  - `config/.env.template`, `config/.env.production` — new env var
  - `backend/services/inter_rater_service.py` — read env var, include in stats
  - `backend/routers/inter_rater.py` — include `default_ui` in all stats responses
  - `frontend/src/stores/interRater.js` — new Pinia store
  - `frontend/src/router/index.js` — redirect guard
  - `frontend/src/App.vue` — conditional NewSessionButton and site title link
  - `frontend/src/components/ChatContainer.vue` — conditional TelemetryToggle
  - `frontend/src/components/InterRaterButton.vue` — refactor to use shared store
  - `frontend/src/components/InterRaterDashboard.vue` — loading message text
  - `docs/inter_rater.md` — document flag relationship
