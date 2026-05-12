# Tasks: Add Seed Questions for Inter-Rater Focus Group Testing

## 1. Create seed questions JSON
- [ ] 1.1 Create `data/seed_questions.json` with 100 questions
- [ ] 1.2 Distribute across corpus filters: ~30 AU, ~25 NZ, ~25 UK, ~15 general, ~5 suboptimal
- [ ] 1.3 Include synthetic feedback ratings (varied 1-5 Likert scores) for each question
- [ ] 1.4 Base questions on `load_tests/utils/data_generators.py`, extend to 100

## 2. Create seeding script
- [ ] 2.1 Create `utils/scripts/seed_questions.py`
- [ ] 2.2 Read questions from JSON file path (configurable, default `data/seed_questions.json`)
- [ ] 2.3 For each question: POST to `/api/ask/stream`, accumulate SSE response
- [ ] 2.4 For each response: POST synthetic feedback to `/api/feedback`
- [ ] 2.5 Add progress reporting (N/100 complete, errors)
- [ ] 2.6 Add `--dry-run` flag to validate JSON without submitting
- [ ] 2.7 Add `--count N` flag to seed only first N questions (for testing)
- [ ] 2.8 Handle errors gracefully (log and continue, report failures at end)

## 3. Add Makefile target
- [ ] 3.1 Add `seed` target to `deploy/Makefile` that runs the script via venv

## 4. Documentation
- [ ] 4.1 Add usage instructions to `docs/inter_rater.md`

## 5. Validation
- [ ] 5.1 Run `make seed --count 5` to test with 5 questions
- [ ] 5.2 Verify seeded sessions appear in Phoenix with feedback annotations
- [ ] 5.3 Verify inter-rater dashboard picks up seeded sessions
