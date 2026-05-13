# Tasks: Add inter-rater default UI mode

## 1. Environment configuration
- [ ] 1.1 Add `INTER_RATER_DEFAULT_UI=false` to `config/.env.template` with comment
- [ ] 1.2 Add `INTER_RATER_DEFAULT_UI=true` to `config/.env.production`
- [ ] 1.3 Add `INTER_RATER_DEFAULT_UI=false` to other env files that have INTER_RATER vars

## 2. Backend
- [ ] 2.1 Read `INTER_RATER_DEFAULT_UI` in `InterRaterService.__init__` (`backend/services/inter_rater_service.py`)
- [ ] 2.2 Include `default_ui` in stats response from `get_inter_rater_stats`
- [ ] 2.3 Include `default_ui` in all early-return paths in `backend/routers/inter_rater.py`

## 3. Frontend store
- [ ] 3.1 Create `frontend/src/stores/interRater.js` Pinia store with `defaultUi`, `isEnabled`, `availableSessions`, `loaded` refs and `fetchConfig()`/`refresh()` actions

## 4. Frontend UI changes
- [ ] 4.1 Add router redirect in `frontend/src/router/index.js` — redirect `/` to `/inter-rater` when `defaultUi` is true
- [ ] 4.2 Update `frontend/src/App.vue` — hide NewSessionButton and change site title link destination when `defaultUi` is true
- [ ] 4.3 Hide TelemetryToggle in `frontend/src/components/ChatContainer.vue` when `defaultUi` is true
- [ ] 4.4 Refactor `frontend/src/components/InterRaterButton.vue` to use shared store
- [ ] 4.5 Update loading message in `frontend/src/components/InterRaterDashboard.vue` to "Loading inter-rating tasks, please wait..."

## 5. Documentation
- [ ] 5.1 Update `docs/inter_rater.md` — document `INTER_RATER_DEFAULT_UI`, explain relationship with `INTER_RATER_ENABLED`

## 6. Validation
- [ ] 6.1 With `INTER_RATER_DEFAULT_UI=true`: verify redirect, hidden button, hidden toggle, loading message
- [ ] 6.2 With `INTER_RATER_DEFAULT_UI=false`: verify normal behaviour restored
