# Tasks: Update Feedback Forms and Reset Default Mode

## Prerequisites
- [x] Identify all `user_type` references in `ExtendedFeedback.vue` and `InterRaterPlayback.vue`
- [x] Identify all `off_topic` and `bias` references in both components
- [x] Confirm `INTER_RATER_DEFAULT_UI` values in all env files
- [x] Confirm OpenRouter target and API key are present in development env

## Phase 1: Standard Feedback Form (`ExtendedFeedback.vue`)

- [x] **Task 1.1**: Remove the User Type section from the template (lines ~262-269): the `<div>` containing both Expert and Non-expert radio labels and inputs
- [x] **Task 1.2**: Remove the `off_topic` fault option from the Faults grid (lines ~285-293): the `<div class="fault-option">` block containing `fault-off-topic`
- [x] **Task 1.3**: Remove the `bias` fault option from the Faults grid (lines ~303-311): the `<div class="fault-option">` block containing `fault-bias`
- [x] **Task 1.4**: Remove `userType` data property and `user_type` from the submit payload (`feedbackData.user_type = this.userType`, line ~514)
- [x] **Task 1.5**: Remove `off_topic` and `bias` keys from the `faults` data initialisation (lines ~382-386) and reset block (lines ~558-562)
- [x] **Task 1.6**: Remove `off_topic` and `bias` keys from `mounted` initialData merge (lines ~583-584)

## Phase 2: Inter-Rater Feedback Form (`InterRaterPlayback.vue`)

- [x] **Task 2.1**: Remove the User Type section from the template (lines ~337-344): both radio labels/inputs
- [x] **Task 2.2**: Remove the `off_topic` fault option from the Faults grid (lines ~360-367): the block containing `fault-off-topic`
- [x] **Task 2.3**: Remove the `bias` fault option from the Faults grid (lines ~377-384): the block containing `fault-bias`
- [x] **Task 2.4**: Remove `user_type` from `feedback` reactive data initialisation (line ~593) and reset block (line ~715-721)
- [x] **Task 2.5**: Remove `user_type` from the submit payload construction (lines ~630, ~668)
- [x] **Task 2.6**: Remove `off_topic` and `bias` from faults initialisation in both the initial `feedback` object and the reset path

## Phase 3: Default Mode Reset

- [x] **Task 3.1**: `config/.env.staging` updated — `INTER_RATER_DEFAULT_UI=false`
- [x] **Task 3.2**: `config/.env.production` updated — `INTER_RATER_DEFAULT_UI=false`
- [ ] **Task 3.3** *(manual)*: Restart backend on staging and production; verify home page loads at `/` (not `/inter-rater`)

## Phase 4: OpenRouter Provider Verification

> **Note**: These are manual verification tasks using the development environment with `TEST_TARGET=k20_openrouter_claude_sonnet`.

- [ ] **Task 4.1**: Set `TEST_TARGET=k20_openrouter_claude_sonnet` in `config/.env.development` and restart the backend (`make dev-backend` or equivalent)
- [ ] **Task 4.2**: Confirm backend starts without errors and logs "Using OpenRouter with API key"
- [ ] **Task 4.3**: Submit a test query via the frontend and verify a full streamed response is received
- [ ] **Task 4.4**: Check Phoenix telemetry for the resulting span — confirm LLM provider is recorded as `OPENROUTER` and token counts are present
- [ ] **Task 4.5**: Confirm citations are returned alongside the response (retrieval path unaffected by provider change)
- [ ] **Task 4.6**: Submit feedback on the test response via the standard form and confirm it is stored without errors
- [ ] **Task 4.7**: Restore `TEST_TARGET` to its original value in `config/.env.development`

## Verification

```bash
# Confirm user_type references removed from both components
grep -n "user_type\|userType\|expert\|non_expert" \
  frontend/src/components/ExtendedFeedback.vue \
  frontend/src/components/InterRaterPlayback.vue

# Confirm off_topic and bias removed from both components
grep -n "off_topic\|bias" \
  frontend/src/components/ExtendedFeedback.vue \
  frontend/src/components/InterRaterPlayback.vue

# Confirm default mode env values (development should already be false)
grep "INTER_RATER_DEFAULT_UI" config/.env.development config/.env.staging config/.env.production
```
