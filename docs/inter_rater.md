# Inter-rater Ratings

## Overview
The inter-rater feature enables authenticated users to provide secondary (inter-rater) ratings on sessions that already have initial feedback. All inter-rater activity is anonymous by design and clearly delineated in Phoenix.

## Key Guarantees
- **Authentication required** (Cognito JWT tokens)
- **Users only rate sessions they did not originally author** (automatic exclusion)
- **Sessions are eligible regardless of baseline feedback** — both organically generated sessions and seeded focus-group sessions are surfaced
- **Anonymity**: users are represented by irreversible anonymous IDs
- **No client IPs** collected, logged, or exported
- **Inter-rater annotations** in Phoenix are clearly labeled and separate from original ratings
- **All 9 evaluation fields** are captured and stored in Phoenix

## Configuration (.env)
```bash
# Enable/disable feature
INTER_RATER_ENABLED=true

# Phoenix project (fallbacks supported in code)
INTER_RATER_PROJECT=YourPhoenixProject

# Allocation limits
INTER_RATER_MAX_RATINGS=3          # Max inter-rater ratings per session (default: 3)
INTER_RATER_SESSIONS_PER_USER=20   # Sessions offered per user (default: 20)

# Default UI mode for focus group testing
INTER_RATER_DEFAULT_UI=false       # Set to true for focus groups (see below)
```

Also ensure authentication is enabled (inter-rater requires user identity):
```bash
AUTH_METHOD=cognito          # or AUTH_METHOD=cloudflare for tunnel deployments
# VITE_AUTH_METHOD is derived automatically from AUTH_METHOD at build time
```

### INTER_RATER_ENABLED vs INTER_RATER_DEFAULT_UI

These two flags serve different purposes:

- **`INTER_RATER_ENABLED`** — backend gate that controls whether the inter-rater feature exists at all. When `false`, the API returns `enabled: false`, the nav button is hidden, and the `/inter-rater` page shows nothing. This is the master switch.

- **`INTER_RATER_DEFAULT_UI`** — UI mode toggle (requires `INTER_RATER_ENABLED=true`). When `true`, the application enters "focus group mode":
  - Users land on the inter-rater page instead of the chat page
  - The site title link points to `/inter-rater` instead of `/`
  - The "New Session" button is hidden from the header
  - The privacy toggle is hidden (telemetry must be on for focus group data collection)

**Typical configurations:**

| Scenario | INTER_RATER_ENABLED | INTER_RATER_DEFAULT_UI |
|----------|--------------------|-----------------------|
| Normal operation (no inter-rating) | `false` | `false` |
| Inter-rating available alongside chat | `true` | `false` |
| Focus group testing (inter-rater only) | `true` | `true` |

## Default Focus-Group Study Configuration

The canonical configuration for inter-rater reliability studies in ATLAS:

```bash
INTER_RATER_ENABLED=true            # required
INTER_RATER_MAX_RATINGS=3           # 3 independent ratings per prompt
INTER_RATER_SESSIONS_PER_USER=20    # each reviewer rates 20 prompts
INTER_RATER_DEFAULT_UI=true         # reviewers see only the inter-rater page
INTER_RATER_PROJECT=<must match PHOENIX_PROJECT_NAME>
```

Paired with a seed pool of **100 prompts** and **15 paid reviewers**, this gives a perfectly saturated 1:1 design — `100 × 3 = 300 = 15 × 20`. Under full attendance every prompt receives exactly 3 independent ratings, suitable for academic IRR analysis (Fleiss' κ across the whole pool with no mixed-N caveats) and for fine-tuning labels.

These values are the default in `config/.env.production` and `config/.env.staging`. The development template (`config/.env.template`) carries the same `MAX_RATINGS=3` so a fresh install matches the canonical study design; if you're iterating locally as a solo developer, override `INTER_RATER_MAX_RATINGS=1` in your `.env.development` so a single rating is enough to saturate a session for visual testing.

### Issues Researchers Must Address

The harness enforces the rating-allocation math, but a good study outcome depends on several things outside its control. Plan for each of these before launching:

1. **Reviewer recruitment and payment.** Payment must be contingent on completing all 20 ratings, with the contract signed before reviewers see any prompts. The saturated 1:1 design has no automatic recovery path if a reviewer abandons mid-study — their share of triple-coverage is permanently lost. Have 1–2 standby reviewers ready in case of legitimate withdrawal (illness, hardware failure).

2. **Reviewer briefing and rubric.** The 6 Likert scales (factual accuracy, corpus fidelity, analysis quality, relevance, difficulty, clarity) need consistent interpretation across raters, or IRR will be artificially depressed. Provide written rubrics with concrete examples for each scale point and run a short calibration session — ideally rating 2–3 sample prompts together — before launch.

3. **Pilot run.** Seed and rate at least 5 prompts with 1–2 reviewers before the main study to verify the full pipeline (seeding → allocation → submission → Phoenix annotations → export). Use `make seed SEED_ARGS="--count 5"` against a dedicated test project (e.g. `INTER_RATER_PROJECT=ATLAS-Pilot`) so the live study's data stays clean.

4. **Question pool curation.** `data/seed_questions.json` should be reviewed by domain experts before seeding. Once a study has begun, the pool is locked — replacing a question mid-study invalidates the IRR analysis. Edit-then-seed is the workflow; never edit during a live study.

5. **Phoenix project naming.** `INTER_RATER_PROJECT` must match `PHOENIX_PROJECT_NAME` exactly (case-sensitive). Mismatches cause seeded sessions to land in one project while the allocator queries another, surfacing zero sessions to reviewers. Verify the match with `make seed-dry` before launch.

6. **Ethics, consent, and anonymisation.** Get appropriate IRB / ethics-committee approval and signed consent before reviewers begin. ATLAS anonymises user IDs irreversibly via `anonymous_id_service`, but the reviewer-identity → payment-record mapping is the researcher's responsibility and must be stored separately from the rating data.

7. **Data export and backup.** Phoenix annotations are the only source of truth for ratings. Export and back up the project immediately after the study completes, before any reset or cleanup. Phoenix retention policies vary by host — do not assume the data will persist indefinitely.

8. **Outlier handling protocol.** Decide in advance what to do if one reviewer's ratings are systematically distant from the others (e.g. always 5/5, or consistently low). Pre-registering the outlier-exclusion rule (on OSF or similar) avoids post-hoc bias accusations in peer review.

9. **Schedule and fatigue.** At 5–10 minutes per prompt, 20 prompts is 100–200 minutes per reviewer. Encourage reviewers to split this across two sittings rather than rush through in one — rating quality degrades with fatigue. The 60-second allocation cache expires between sittings so reviewers can resume without seeing stale queues.

10. **Reproducibility for the paper.** Record at study launch: the exact commit SHA, the active test target (LLM provider, model name, temperature), the vector store version, and the Phoenix project name. Replication requires the same code, the same RAG configuration, and the same prompt pool.

## Configuration Guidelines

### Choosing Optimal Values

The relationship between `INTER_RATER_MAX_RATINGS` and `INTER_RATER_SESSIONS_PER_USER` determines coverage and workload distribution:

**Small Teams (2-5 users):**
```bash
INTER_RATER_MAX_RATINGS=2          # 2 inter-raters per session
INTER_RATER_SESSIONS_PER_USER=10   # 10 sessions per user
```
- Good for quick validation with limited resources
- Each session gets 2 independent ratings
- Users rate more sessions but with lighter coverage

**Medium Teams (5-10 users):**
```bash
INTER_RATER_MAX_RATINGS=3          # 3 inter-raters per session (recommended)
INTER_RATER_SESSIONS_PER_USER=10   # 10 sessions per user
```
- Provides good statistical reliability
- Balanced workload per user

**Current Study (15 paid reviewers × 20 ratings = exactly 3 ratings/prompt):**
```bash
INTER_RATER_MAX_RATINGS=3          # 3 inter-raters per session
INTER_RATER_SESSIONS_PER_USER=20   # 20 sessions per user (default)
```
- 100 prompts × 3 ratings = 300 = 15 reviewers × 20 ratings — perfectly saturated 1:1
- Count-aware allocation drives every prompt to exactly 3 ratings under staggered arrival; suitable for Fleiss' κ across the full pool

**Large Teams (10+ users):**
```bash
INTER_RATER_MAX_RATINGS=5          # 5 inter-raters per session
INTER_RATER_SESSIONS_PER_USER=3    # 3 sessions per user
```
- Maximum inter-rater reliability
- Lower workload per user
- Requires more users for full coverage

### Coverage Calculation

To achieve full coverage of N sessions:
```
Minimum users needed = (N × INTER_RATER_MAX_RATINGS) / INTER_RATER_SESSIONS_PER_USER
```

**Example (current study):**
- 100 sessions to cover
- MAX_RATINGS=3
- SESSIONS_PER_USER=20
- Demand = 15 × 20 = **300 ratings**, distributed by the count-aware allocator so each of the 100 sessions receives **exactly 3 ratings** under full attendance
- Worst-case (one reviewer fully no-shows): 80 prompts triple-rated, 20 double-rated — still cleanly above the ≥2 floor

### Workload Estimation

Per-user time commitment:
```
Time per session: ~5-10 minutes (all 9 fields)
Total time = SESSIONS_PER_USER × 5-10 minutes
```

With `SESSIONS_PER_USER=20`: **100-200 minutes per user**

## Seeding Sessions for Focus Group Testing

For focus-group studies (e.g. 15 raters × 20 ratings each), there is rarely enough organic traffic to provide a pre-populated pool of sessions. The seeding script runs a JSON file of questions through the live RAG pipeline so each question becomes a ratable session in Phoenix — with real LLM answers and real citations, but no baseline feedback (so the only feedback comes from focus-group participants).

### Workflow on prod

```bash
git pull
make seed   # uses config/.env.development by default; override with ENV_FILE
```

The script targets `localhost:8000` directly, so `AUTH_METHOD=cloudflare` stays on for public traffic the entire time — no maintenance window is required.

### Sizing

The seed pool size determines the rating-density per prompt:

```
pool_size = (participants × ratings_per_participant) / INTER_RATER_MAX_RATINGS
```

For the default focus group target (15 reviewers × 20 ratings = 300 ratings) with `MAX_RATINGS=3`, this gives a saturated 1:1 design at **100 prompts × 3 ratings = 300**. Every prompt receives exactly 3 ratings under full attendance, which is the gold standard for inter-rater reliability (single Fleiss' κ across the pool, no mixed-N caveats).

This design assumes paid reviewers with completion-linked payment so attrition is rare. If you can't assume that, add a buffer of ~20% (pool=120) to protect the ≥2-ratings-per-prompt floor against dropouts — at the cost of mixing 2- and 3-rated prompts in the output. The script prints a sizing check at startup and warns if the pool is undersized.

### Files

- `data/seed_questions.json` — editable list of `{question, corpus_filter}` entries. Update on the server before running `make seed`; no code deployment required.
- `utils/scripts/seed_questions.py` — POSTs each question to `/api/ask/stream`, drains the SSE stream to completion, and verifies that both the LLM span and the `com.atlas.rag.references` (citations) span land in Phoenix.

### Useful options

- `make seed-dry` — validate JSON and print the sizing check without submitting
- `make seed SEED_ARGS="--count 5"` — seed only the first 5 questions (testing)
- `make seed SEED_ARGS="--no-verify"` — skip the post-seed Phoenix verification pass
- `ENV_FILE=config/.env.production make seed` — explicitly use the prod env file (only needed when both env files exist on the same box; otherwise the Makefile auto-falls-back to `.env.production` when `.env.development` is absent)

### Resetting between test runs

For iterative testing of the inter-rating UI, `make seed-reset` deletes the configured `INTER_RATER_PROJECT` from Phoenix entirely — sessions, annotations, the lot. Run `make seed` afterwards to restore the baseline. The reset workflow is intended for dedicated test projects (e.g. set `INTER_RATER_PROJECT=ATLAS-SeedTest` in your env file) so it doesn't disturb organic data.

Safety:
- The script refuses to delete projects whose names contain "prod" or "production" unless `--force` is passed (`make seed-reset SEED_ARGS="--force --yes"`).
- An exact project-name confirmation prompt is required unless `--yes` is passed.

### Behavior

Seeded sessions have no baseline (`original`) feedback. The inter-rater service surfaces them anyway; the first participant rating on a seeded session is tagged `inter_rater_1` (no `original` annotation is ever created for seeded sessions, so all 15 raters are treated symmetrically).

## Architecture
- Backend
  - `backend/services/inter_rater_service.py`: allocation, per-user cache, limits
  - `backend/services/phoenix_client.py`: queries/duplicate checks against Phoenix
  - `backend/telemetry/api.py`: unified feedback endpoint (regular + inter-rater)
  - `backend/telemetry/feedback.py`: Phoenix span annotations (adds "[inter-rating-N]" prefix and per-scale comments)
  - `backend/services/anonymous_id_service.py`: generates environment-scoped anonymous IDs from Cognito `sub`
- Frontend
  - `frontend/src/components/InterRaterButton.vue`: shows available session count
  - `frontend/src/components/InterRaterDashboard.vue`: loads sessions and submits ratings
  - `frontend/src/components/InterRaterPlayback.vue`: rating UI for a single session

## Data Flow (Allocation)
1. User logs in (Cognito), navigates to app
2. Inter-rater button calls `GET /api/inter-rater/stats`
3. Backend verifies JWT, derives anonymous ID
4. Allocation service queries Phoenix for eligible sessions and applies rules:
   - **Include all generation-response spans** (sessions without baseline feedback are eligible — see Seeding section)
   - **Exclude sessions authored by this anonymous user** (prevents self-rating; seeded sessions have no `original_user_id` and pass through)
   - **Exclude sessions already inter-rated by this user** (prevents duplicate rating)
   - **Enforce `INTER_RATER_MAX_RATINGS`** limit (default: 3 per session)
   - **Apply deterministic user-specific allocation** (same user always gets same sessions)
   - **Limit to `INTER_RATER_SESSIONS_PER_USER`** (default: 20 per user)
5. Counts cached per user (short TTL). Cache invalidated when the user submits inter-rater feedback.

## Allocation Algorithm Details

The allocator (`_allocate_sessions_to_user` in `backend/services/inter_rater_service.py`) ranks eligible sessions for each user using a **count-aware** sort that fills the pool bottom-up:

1. Primary key — `inter_rater_count ASC`. Sessions with fewer existing ratings surface first, so the pool fills evenly and every session is more likely to clear the ≥2-ratings floor before any session is saturated.
2. Tiebreaker — `SHA-256(span_id:user_id)`. Within a count bucket (e.g. all sessions still at 0 ratings) each user gets a deterministic, de-correlated ordering so two users at the same count don't dogpile the same session.
3. Top-N selected — first `INTER_RATER_SESSIONS_PER_USER` sessions returned.

The per-user cache TTL is **60 seconds** so rankings stay in step with current `inter_rater_count` as ratings come in during the focus group. The `INTER_RATER_MAX_RATINGS` cap is enforced upstream of the ranker via the `inter_rater_count` pre-filter — capped sessions drop out of `available_sessions` on the next cache refresh.

### Why count-aware ranking

Pure hash-based ranking (the previous behaviour) de-correlates users but does not load-balance ratings across sessions. With 15 users picking top-20 from a 100-session pool, ~16% of sessions end up with fewer than 2 raters under the binomial distribution. Count-aware ranking corrects this by progressively concentrating fresh ratings on the least-rated sessions, so the floor is reliably met under realistic focus-group conditions (simulated dogpile and 15-minute staggered arrival both produce 0 sessions below floor with `pool=120`).

### Progressive Filling

As users complete ratings, sessions fill up:

```
Initial State:
- Session 001: 0/3 ratings
- Session 002: 0/3 ratings
- Session 003: 0/3 ratings

After User A rates:
- Session 001: 1/3 ratings ✓
- Session 002: 1/3 ratings ✓
- Session 003: 1/3 ratings ✓

After User B rates:
- Session 001: 2/3 ratings ✓
- Session 002: 2/3 ratings ✓
- Session 003: 2/3 ratings ✓

After User C rates:
- Session 001: 3/3 ratings [FULL - removed from allocation]
- Session 002: 3/3 ratings [FULL - removed from allocation]
- Session 003: 3/3 ratings [FULL - removed from allocation]
```

Once a session reaches `INTER_RATER_MAX_RATINGS`, it's automatically excluded from future allocations.

### Capacity and Coverage

The system self-balances:
- Sessions near capacity get fewer new allocations (already rated check)
- Users who complete their sessions get no new allocations (cache invalidation shows 0 available)
- New sessions with feedback automatically enter the allocation pool

## Data Flow (Submission)
1. Dashboard posts inter-rater feedback to `POST /api/feedback`
2. Backend verifies JWT, derives anonymous ID
3. Backend queries Phoenix to count existing inter-raters for this span (async, non-blocking)
4. Inter-rater number calculated: `existing_count + 1`
5. Feedback is attached to the original QA span in Phoenix as span annotations via `feedback.submit_span_annotation()`
6. Inter-rater entries:
   - Annotation names are prefixed with numbered format: `[inter-rating-1]`, `[inter-rating-2]`, `[inter-rating-3]`
   - Annotation IDs include the number for uniqueness: `inter_rater_{rater_id}_{number}_{qa_id}_{timestamp}`
   - Metadata includes `is_inter_rater=true`, `rater_id=<anon_id>`, `inter_rater_number=<N>`, `original_span_id=<phoenix_span>`
7. On success, the user's inter-rater cache is invalidated so counts update immediately

## Anonymity & Privacy
- Anonymous IDs: `anonymous_id_service` hashes the Cognito `sub` with an environment-specific salt, producing `anon_<16-hex>` IDs
- No client IP collection/logging/export
- No emails or usernames logged
- Phoenix submissions contain only anonymized identifiers and rating metadata

## Evaluation Fields (Order)
Both main ratings and inter-ratings use the same field order - **all 9 fields are captured**:
1. **Factual Accuracy** (1–5 Likert scale)
2. **Corpus Fidelity** (1–5 Likert scale)
3. **Analysis Quality** (1–5 Likert scale)
4. **Relevance** (1–5 Likert scale) 
5. **Difficulty** (1–5 Likert scale)
6. **Clarity** (1–5 Likert scale)
7. **User Type** (Expert / Non-expert) - *Fixed: Now properly stored in Phoenix*
8. **Comments** (Free text feedback)
9. **Faults** (hallucination, off_topic, inappropriate, bias checkboxes)

**Recent Fix**: User Type field was previously not being stored in Phoenix annotations - this has been resolved.

## API Endpoints
- `GET /api/inter-rater/stats`
  - Returns user-specific availability and limits
  - **Requires Authentication**: Cognito JWT token in Authorization header
- `GET /api/inter-rater/sessions`
  - Returns the list of sessions available to the current user
  - **Requires Authentication**: Cognito JWT token in Authorization header
- `POST /api/feedback`
  - Submits both regular and inter-rater feedback; inter-rater metadata is set server-side
  - **Requires Authentication**: Cognito JWT token in Authorization header
- `GET /api/debug/user-id` *(Development only)*
  - Debug endpoint to verify user ID extraction from JWT tokens

## Caching
- **Session cache:** Per-user key `inter_rater_sessions_{anon_user_id}` with 60-second TTL
- **Stats cache:** Per-user key `stats_{anon_user_id}` with 10-second TTL
- Both caches invalidated immediately when user submits inter-rater feedback
- Cache validation: Cached sessions are validated against Phoenix to filter out deleted sessions
- Global cache clear available for significant Phoenix data changes

## Phoenix Notes
- POST annotations endpoint used: `/v1/span_annotations?sync=true`
- All inter-rater annotations are clearly separated by numbered name prefixes (`[inter-rating-1]`, `[inter-rating-2]`, etc.) and metadata
- Unique annotation IDs prevent overwrites when multiple raters rate the same session
- Headers include API key only; headers are redacted in logs
- Inter-rater counting uses GET endpoint: `/v1/projects/{project}/span_annotations` with async httpx for non-blocking queries

## Troubleshooting
- **No sessions available**: 
  - Verify `INTER_RATER_ENABLED=true` in .env
  - **`INTER_RATER_PROJECT` must exactly match `PHOENIX_PROJECT_NAME`** — spans are exported to the project named by `PHOENIX_PROJECT_NAME`, so inter-rater must query the same project. A mismatch (e.g. `ATLAS-Prod` vs `Hansard-Prod`) results in zero sessions.
  - Confirm `com.atlas.rag.generation.response` spans exist in the project (either from real user traffic or from `make seed`)
  - Verify user is authenticated (Cognito or Cloudflare Access — inter-rater requires user identity)
- **Seeded sessions not appearing in Phoenix**:
  - The seed script must send `X-Telemetry-Opt-In: true` and `X-Trace-Id` headers with each request, otherwise the app's telemetry middleware disables span creation. These headers are included automatically by the current script.
  - Seeding runs against `localhost:8000` and does not require `AUTH_METHOD=none` — the `/api/ask/stream` endpoint has no auth enforcement. Keep `AUTH_METHOD=cloudflare` (or `cognito`) active so inter-rating works simultaneously.
- **User sees own ratings**: 
  - Fixed: Frontend now sends Authorization headers with all feedback submissions
  - Ensure user_id is properly captured during original feedback submission
- **Missing evaluation fields**: 
  - Fixed: All 9 fields including User Type are now stored in Phoenix
- **Duplicate rating prevented**: Backend checks if the same rater already rated the same original span
- **Count not updating immediately**: Cache invalidation happens after submission (handled in backend)

## Recent Fixes

### 2026-01 (January)
- ✅ **Numbered Annotations**: Inter-rater annotations now show as `[inter-rating-1]`, `[inter-rating-2]`, `[inter-rating-3]` instead of generic `[Inter-rater]` (GitHub issue #43)
- ✅ **Async Event Loop Fix**: Converted `submit_span_annotation()` to async to fix `inter_rater_number` determination in FastAPI's running event loop
- ✅ **Unique Annotation IDs**: Include `inter_rater_number` in annotation IDs to prevent overwrites when multiple raters rate the same session

### 2025-08 (August)
- ✅ **Authentication Bug**: Fixed frontend components to send Authorization headers with feedback
- ✅ **User Type Field**: Added missing User Type annotation to Phoenix feedback processing
- ✅ **Session Filtering**: Only sessions with existing feedback annotations are allocated for inter-rating
- ✅ **Anonymous ID Logging**: Enhanced logging for debugging while maintaining privacy
- ✅ **Filter Loading**: Fixed New Session button to properly reload dynamic filters


