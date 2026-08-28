# Proposal: Update Feedback Forms and Reset Default Mode

## Change ID
`update-feedback-forms-and-defaults`

## Summary
Trim the feedback forms on both the standard and inter-rater UI (remove user-type radio and two fault checkboxes), reset the system default back to standard mode, and add testing tasks for the recently integrated OpenRouter LLM provider.

## Motivation

### Feedback form simplification
The Expert / Non-expert user-type radio and the Off-topic / Bias fault checkboxes were added for an earlier evaluation iteration. They are no longer required and add unnecessary cognitive load to respondents. Removing them reduces the form surface and aligns the UI with the current evaluation protocol.

### Default mode reset
`INTER_RATER_DEFAULT_UI` was set to `true` in all non-template environment files (`config/.env.development` is still at the default `false`; staging and production are `true`) to support a focus-group run. That run is complete; the system should return to standard (non–inter-rater) mode as the default. This is a manual operator task for staging/production; the proposal documents it.

### OpenRouter provider testing
OpenRouter was integrated in `backend/modules/llm.py` (provider `OPENROUTER`) and a test target `backend/targets/k20_openrouter_claude_sonnet.txt` was created. An `OPENROUTER_API_KEY` is present in `config/.env.development`. The integration has not been formally exercised end-to-end; the proposal adds a set of verification tasks.

## Scope

### In Scope
- Remove `user_type` (Expert / Non-expert) radio group from `ExtendedFeedback.vue` (standard form) and `InterRaterPlayback.vue` (inter-rater form)
- Remove `off_topic` and `bias` checkbox options from the Faults section in both components
- Update component data initialisation, reset logic, and submit payload construction to match the reduced field set
- Document the manual environment-file update required to set `INTER_RATER_DEFAULT_UI=false` on staging / production
- Add end-to-end testing tasks for the OpenRouter provider path

### Out of Scope
- Backend API changes — the backend already accepts `faults` as an optional partial object; omitting removed fields requires no schema changes
- Removing `user_type` from backend storage or Phoenix annotations — existing data retains the field; new submissions simply omit it
- Changing the OpenRouter integration code (already implemented)
- Resetting `INTER_RATER_DEFAULT_UI` in `config/.env.development` (already `false`)

## Current State

| Location | Field / Behaviour |
|---|---|
| `frontend/src/components/ExtendedFeedback.vue:262-268` | Expert / Non-expert radio (standard form) |
| `frontend/src/components/InterRaterPlayback.vue:337-343` | Expert / Non-expert radio (inter-rater form) |
| `frontend/src/components/ExtendedFeedback.vue:288-310` | Off-topic + Bias checkboxes (standard form) |
| `frontend/src/components/InterRaterPlayback.vue:363-382` | Off-topic + Bias checkboxes (inter-rater form) |
| `config/.env.staging`, `config/.env.production` | `INTER_RATER_DEFAULT_UI=true` |
| `backend/modules/llm.py:151-166` | OpenRouter provider, untested end-to-end |

## Proposed Changes

### Feedback form UI
Remove both occurrences of:
- The "User Type" section (Expert / Non-expert radio inputs and their labels)
- The `off_topic` and `bias` entries from the Faults grid

`faults` data object retains only `hallucination` and `inappropriate`.

### Environment files
Set `INTER_RATER_DEFAULT_UI=false` in `config/.env.staging` and `config/.env.production`. This is a manual operator task; the server-side service reads the value on startup.

### OpenRouter testing tasks
Structured verification using the existing `k20_openrouter_claude_sonnet` test target and the `OPENROUTER_API_KEY` already present in `config/.env.development`.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Existing feedback submissions reference removed fields | Low | Low | Backend stores only what is sent; no schema enforced on optional fields |
| Inter-rater form breaks if `user_type` is referenced elsewhere | Low | Medium | Audit all references before removing |
| OpenRouter API rate-limit or quota failure during testing | Medium | Low | Tests are manual verification tasks, not CI gates |
| `INTER_RATER_DEFAULT_UI` update on staging/production missed | Low | Low | Documented as explicit operator task in tasks.md |

## Acceptance Criteria
- [ ] Expert / Non-expert radio absent from standard and inter-rater feedback forms
- [ ] Off-topic and Bias checkboxes absent from Faults section of both forms
- [ ] Submitting feedback via both forms succeeds without errors
- [ ] `INTER_RATER_DEFAULT_UI=false` documented for manual update on staging/production
- [ ] OpenRouter provider exercises a full RAG query end-to-end in development without errors
