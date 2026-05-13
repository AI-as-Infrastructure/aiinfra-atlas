# Tasks: Add Seed Questions for Inter-Rater Focus Group Testing

## 1. Create seed questions JSON
- [x] 1.1 Create `data/seed_questions.json` (questions + corpus filters only — no synthetic feedback)
- [x] 1.2 Size the pool per the formula in `proposal.md` (default target: ≥100 for prod/staging)
- [x] 1.3 Distribute across corpus filters: ~30 AU, ~25 NZ, ~25 UK, ~15 general, ~5 suboptimal
- [x] 1.4 Base questions on `load_tests/utils/data_generators.py`, extend as needed

## 2. Relax inter-rater filter
- [x] 2.1 In `backend/services/phoenix_client.py`, allow spans without `original_feedback` to be returned for inter-rating (remove the `if span_id not in spans_with_feedback: continue` and `if not original_feedback: continue` gates, or gate them behind a flag)
- [x] 2.2 Rename `query_spans_with_feedback` → `query_spans_for_inter_rating` to reflect new semantics
- [x] 2.3 Update the call site in `backend/services/inter_rater_service.py`
- [x] 2.4 Confirm `safe_feedback` / `original_user_id` paths handle the no-original-feedback case (don't crash on `None`)

## 3. Create seeding script
- [x] 3.1 Create `utils/scripts/seed_questions.py`
- [x] 3.2 Read questions from JSON file path (configurable, default `data/seed_questions.json`)
- [x] 3.3 At startup, read `INTER_RATER_MAX_RATINGS` from env and print sizing check (`N questions × MAX_RATINGS=M → supports up to N·M ratings`)
- [x] 3.4 For each question: POST to `localhost:8000/api/ask/stream`, drain the full SSE stream to completion
- [x] 3.5 After each question, verify both the LLM span and the `com.atlas.rag.references` span exist in Phoenix for that `qa_id` before counting it as a successful seed
- [x] 3.6 Progress reporting (N/total complete, errors)
- [x] 3.7 `--dry-run` flag: validate JSON and print sizing check without submitting
- [x] 3.8 `--count N` flag: seed only first N questions (for testing)
- [x] 3.9 Handle errors gracefully (log and continue, report failures at end)

## 4. Add Makefile targets
- [x] 4.1 Add `seed` target to `deploy/Makefile` that runs the script via venv
- [x] 4.2 Add `seed-dry` target (validates JSON + sizing check)
- [x] 4.3 Add `seed-reset` target that deletes `INTER_RATER_PROJECT` from Phoenix; refuse on names containing "prod"/"production" unless `--force`; otherwise require an exact project-name confirmation prompt

## 5. Documentation
- [x] 5.1 Add usage instructions to `docs/inter_rater.md`, including the sizing formula and the `git pull && make seed` workflow on prod

## 6. Validation (requires running backend on localhost:8000)
- [ ] 6.1 Run `make seed` with `--count 5` to test with 5 questions
- [ ] 6.2 Verify seeded sessions appear in Phoenix with both LLM and REFERENCES spans (citations populated)
- [ ] 6.3 Verify inter-rater dashboard picks up seeded sessions (no baseline feedback required)
- [ ] 6.4 Submit a test inter-rater rating against a seeded session and confirm it's tagged `inter_rater_1`
