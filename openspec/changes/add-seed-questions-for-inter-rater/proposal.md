# Change: Add seed questions mechanism for inter-rater focus group testing

## Why
The inter-rater reliability system requires sessions with existing user feedback in Phoenix. For focus group testing with 15 participants rating 100 sessions each completing 20 ratings, we need 100 sessions pre-populated with original feedback. Currently there is no mechanism to seed these — they would need to be created manually through the UI one at a time.

Colleagues may want to review and edit the questions before testing, so the question list should be in an editable JSON file that can be updated on the server independently of code deployments.

## What Changes
- Create `data/seed_questions.json` containing 100 questions with corpus filters and synthetic feedback ratings
- Create `utils/scripts/seed_questions.py` script that:
  1. Reads questions from JSON file
  2. Submits each to `/api/ask/stream` to run through the full RAG pipeline
  3. Submits synthetic feedback to `/api/feedback` for each response
  4. Reports progress and results
- Add `make seed` target to run the seeding script
- Extend existing questions from `load_tests/utils/data_generators.py` to reach 100

## Design Decisions
- **All 100 questions get feedback** — inter-rater only picks up sessions with existing annotations
- **Additive, not destructive** — running `make seed` adds new sessions without clearing existing ones
- **AUTH_METHOD=none during seeding** — the script creates synthetic "original user" sessions without authentication; the server must be running with `AUTH_METHOD=none`
- **JSON file is editable** — colleagues can update questions on the server before running `make seed`
- **Sequential submission** — questions submitted one at a time to avoid overwhelming the LLM provider and to ensure proper span correlation

## Impact
- Affected specs: none (new utility, no behavior change to existing system)
- Affected code:
  - `data/seed_questions.json` — new: 100 questions with filters and feedback templates
  - `utils/scripts/seed_questions.py` — new: seeding script
  - `deploy/Makefile` — add `seed` target
- No changes to existing backend code — uses existing API endpoints as-is
