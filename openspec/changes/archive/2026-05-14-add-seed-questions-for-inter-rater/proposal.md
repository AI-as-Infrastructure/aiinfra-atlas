# Change: Add seed questions mechanism for inter-rater focus group testing

## Why
The inter-rater reliability system needs a pool of pre-populated sessions for focus group testing (15 participants rating sessions, ~20 ratings each). There is currently no mechanism to seed these — they would have to be created manually through the UI one at a time.

Additionally, the existing inter-rater pipeline filters out spans that lack baseline ("original") feedback (`backend/services/phoenix_client.py:157,162`). For the focus group we want *only* human ratings from the 15 participants — no synthetic baseline anchoring or contaminating the dataset. The filter therefore needs to be relaxed so seeded sessions without baseline feedback are eligible for inter-rating.

Colleagues may want to review and edit the question list before testing, so the questions should live in an editable JSON file that can be updated on the server independently of code deployments.

## What Changes
- Create `data/seed_questions.json` containing questions with corpus filters (questions only — no synthetic feedback). Pool size is sized per environment (see Design Decisions).
- Create `utils/scripts/seed_questions.py` that:
  1. Reads questions from the JSON file
  2. POSTs each question to `localhost:8000/api/ask/stream` to run through the full RAG pipeline
  3. Drains the SSE stream to completion so the `com.atlas.rag.references` (citations) span is emitted before moving on
  4. Verifies each seeded `qa_id` resulted in both an LLM span and a citations span in Phoenix
  5. Prints a sizing check at startup (`N questions × MAX_RATINGS=M → supports up to N·M ratings`) so operators catch under-sizing before kicking off a long run
  6. Reports progress and any failures
- Relax the inter-rater eligibility filter in `backend/services/phoenix_client.py` so spans without `original_feedback` are surfaced for rating. Rename `query_spans_with_feedback` → `query_spans_for_inter_rating` to match the new semantics.
- Add `make seed`, `make seed-dry`, and `make seed-reset` targets to `deploy/Makefile`. `seed-reset` deletes the `INTER_RATER_PROJECT` from Phoenix (refusing if the name contains "prod"/"production" unless `--force`, and otherwise requiring an exact project-name confirmation prompt) so iterative testing of the inter-rating UI can return to a clean seed baseline.
- Extend existing question pool in `load_tests/utils/data_generators.py` as needed to reach the target size

## Design Decisions
- **No synthetic baseline feedback** — all feedback on seeded sessions comes from human raters. The frontend (`InterRaterPlayback.vue:670`) always tags submissions `is_inter_rater: true`, so all 15 participant ratings are treated symmetrically (numbered 1..15, no "original").
- **Citations come from the pipeline, not from the JSON** — POSTing to `/api/ask/stream` causes the standard RAG flow to emit both an LLM span and a `com.atlas.rag.references` span linked by `qa_id`. Seeded sessions get real citations the same way real user sessions do.
- **Localhost-only execution on prod** — script targets `localhost:8000`, so `AUTH_METHOD=cloudflare` stays on for public traffic the entire time. Workflow on prod is simply `git pull && make seed`. No auth disabling, no maintenance window.
- **Pool size is environment-dependent, not hardcoded** — the script seeds whatever is in the JSON file; operators size the file based on the env config. The sizing formula is `pool_size ≥ (participants × ratings_per_participant) / INTER_RATER_MAX_RATINGS`. For the focus group target (15 × 20 = 300 rating slots):
  - prod (`MAX_RATINGS=3`) → ≥ 100 questions
  - staging (`MAX_RATINGS=3`) → ≥ 100 questions
  - dev (`MAX_RATINGS=1`) → ≥ 300 questions, or lower the participant target on dev
- **Additive, not destructive** — running `make seed` adds new sessions; existing ones are untouched.
- **JSON file is editable in place** — colleagues can update questions on the server before running `make seed`.
- **Sequential submission** — questions submitted one at a time to avoid overwhelming the LLM provider and to keep span correlation clean.

## Impact
- Affected specs: `feedback` capability — adds requirements for inter-rater eligibility without baseline feedback and for seed question ingestion (matches the pattern used by `2026-05-12-update-inter-rater-annotation-numbering`)
- Affected code:
  - `data/seed_questions.json` — new
  - `utils/scripts/seed_questions.py` — new
  - `utils/scripts/seed_reset.py` — new
  - `backend/services/phoenix_client.py` — relax `original_feedback` filter, rename function
  - `backend/services/inter_rater_service.py` — update call site to match renamed function
  - `deploy/Makefile` — new `seed` target
- No frontend changes — `InterRaterPlayback.vue` / `InterRaterDashboard.vue` do not reference `original_feedback`.
