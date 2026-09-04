# Inter-rater Ratings

## Overview
The inter-rater feature enables authenticated users to provide secondary ratings on organic or seeded sessions. Baseline feedback is optional. All inter-rater activity is anonymous by design and clearly delineated in Phoenix.

## Key Guarantees
- **Authentication required** (Cognito JWT tokens)
- **Users only rate sessions they did not originally author** (automatic exclusion)
- **Sessions are eligible regardless of baseline feedback** — both organically generated sessions and seeded focus-group sessions are surfaced
- **Anonymity**: users are represented by irreversible anonymous IDs
- **No client IPs** collected, logged, or exported
- **Inter-rater annotations** in Phoenix are clearly labeled and separate from original ratings
- **All rubric fields** are captured and stored in Phoenix (see Evaluation Fields below)

## Configuration (.env)
```bash
# Enable/disable feature
INTER_RATER_ENABLED=true

# Phoenix project (fallbacks supported in code)
INTER_RATER_PROJECT=YourPhoenixProject

# Allocation limits
INTER_RATER_MAX_RATINGS=4          # Max inter-rater ratings per session (required)
INTER_RATER_REVIEWERS=20           # Expected reviewers; used by seed sizing checks
INTER_RATER_SESSIONS_PER_USER=20   # Sessions each reviewer must complete

# Required by make seed/seed-reset; omit only for ad-hoc project-wide rating
INTER_RATER_POOL_MANIFEST=data/seed_pool.json

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

| Scenario | INTER_RATER_ENABLED | INTER_RATER_DEFAULT_UI | INTER_RATER_POOL_MANIFEST |
|----------|--------------------|-----------------------|---------------------------|
| Normal operation (no inter-rating) | `false` | `false` | not required |
| Inter-rating available alongside chat | `true` | `false` | optional (unset for ad-hoc; set it to require a seeded pool) |
| Focus group testing (inter-rater only) | `true` | `true` | **required** |

`INTER_RATER_DEFAULT_UI=true` means a study is running, so the study pool must be
explicit. Without it, allocation would revert to project-wide ad-hoc rating and
every study guarantee would quietly stop applying — no pool purity, no capacity
check, and a cohort key derived from query results rather than the manifest. One
organic session in the project is then enough to switch balanced allocation off
and under-rate part of the pool.

Two checks enforce this:

- **Unset setting — startup.** The backend refuses to start if
  `INTER_RATER_POOL_MANIFEST` is missing while `INTER_RATER_DEFAULT_UI=true`. A
  blank or whitespace value counts as unset.
- **Set but unreadable — pool refresh in either UI mode.** A configured path
  declares that allocation is restricted to that study pool, even when chat
  remains the default UI. If no readable manifest exists behind the path,
  inter-rating rejects the allocation rather than treating the entire project
  as an ad-hoc pool. Deliberate ad-hoc mode requires the setting to be unset.

The second check is deliberately not done at startup: `make seed` writes the
manifest by POSTing to the running backend, so requiring a readable pool to boot
would deadlock a first-time study. The app starts and serves normally; only
inter-rating refuses until the pool exists.

## Default Focus-Group Study Configuration

The canonical configuration for inter-rater reliability studies in ATLAS:

```bash
INTER_RATER_ENABLED=true            # required
INTER_RATER_MAX_RATINGS=4           # 4 independent ratings per prompt
INTER_RATER_REVIEWERS=20            # expected study cohort
INTER_RATER_SESSIONS_PER_USER=20    # each reviewer rates 20 prompts
INTER_RATER_DEFAULT_UI=true         # reviewers see only the inter-rater page
INTER_RATER_PROJECT=<must match PHOENIX_PROJECT_NAME>
INTER_RATER_POOL_MANIFEST=data/seed_pool.json   # required in focus-group mode
```

Paired with a seed pool of **100 prompts** and **20 paid reviewers**, this gives a perfectly saturated 1:1 design — `100 × 4 = 400 = 20 × 20`. Under full attendance every prompt receives exactly 4 independent ratings, suitable for academic IRR analysis (Fleiss' κ across the whole pool with no mixed-N caveats) and for fine-tuning labels.

`MAX_RATINGS` must be set so that `pool × MAX_RATINGS = reviewers × SESSIONS_PER_USER`. Leaving it at 3 with 20 reviewers caps capacity at 300 against 400 ratings demanded, and reviewers run out of work before completing their 20 — see `test_undersized_pool_starves_raters`. These settings are required when inter-rating is enabled; the application does not embed study-design defaults.

Configure these values in production and staging environment files. The tracked development template (`config/.env.template`) carries the canonical study values; if you're iterating locally as a solo developer, override `INTER_RATER_MAX_RATINGS=1` and `INTER_RATER_REVIEWERS=1` so a single rating saturates a session for visual testing.

### Issues Researchers Must Address

The harness enforces the rating-allocation math, but a good study outcome depends on several things outside its control. Plan for each of these before launching:

1. **Reviewer recruitment and payment.** Payment must be contingent on completing all 20 ratings, with the contract signed before reviewers see any prompts. The saturated 1:1 design has no automatic recovery path if a reviewer abandons mid-study — their share of the coverage is permanently lost. Have 1–2 standby reviewers ready in case of legitimate withdrawal (illness, hardware failure).

2. **Reviewer briefing and rubric.** The 6 Likert scales (corpus fidelity, citation quality, relevance, coherence, uncertainty, historical contextualisation — see Evaluation Fields below) need consistent interpretation across raters, or IRR will be artificially depressed. Provide written rubrics with concrete examples for each scale point and run a short calibration session — ideally rating 2–3 sample prompts together — before launch.

   Also tell reviewers what the two non-success messages mean, because they look
   similar and call for opposite responses:

   - **"Unable to verify or record this inter-rating. Please retry."** — the
     rating was **not** saved. Submit it again. The submission path deliberately
     fails closed: it will not write a rating it cannot first verify against the
     cap, so a momentary Redis or Phoenix interruption rejects the submission
     rather than risking a miscounted one. Re-submitting is safe and is the
     correct response; the work is only lost if they navigate away instead.
   - **"This inter-rating session is no longer available."** — expected, not an
     error. The prompt reached its rating cap, or they had already rated it. It
     is removed from their queue and replaced automatically. Nothing to redo.

   Because the rating path fails closed, Redis and Phoenix availability are hard
   dependencies during a session, not soft ones. Check both before reviewers
   start and keep an eye on them while the session runs; a reviewer losing 5–10
   minutes of work to a retry is recoverable, but only if they retry rather than
   assume the tool is broken. Worth saying explicitly in the briefing that
   occasional retries are normal.

   Retrying cannot corrupt anything. The gate checks `check_user_already_rated`
   before the cap, so if a first attempt did reach Phoenix but the reply was
   lost, the retry returns "no longer available" instead of writing twice. The
   progress count is derived from the distinct prompts a reviewer has rated in
   the active pool, not from submission attempts, so it cannot be inflated by a
   retry either — the counter shown mid-session is incremented locally on each
   success and re-read from Phoenix whenever the queue reloads.

3. **Pilot run.** Rate a handful of prompts with 1–2 reviewers before the main study to verify the full pipeline (seeding → allocation → submission → Phoenix annotations → export). Note that a short pilot pool must still satisfy `pool × MAX_RATINGS = REVIEWERS × SESSIONS_PER_USER`, so `--count 5` under the study settings will be rejected (`5 × 4 = 20` vs `20 × 20 = 400`). Either pilot against the full pool — seed all 100, have 1–2 people rate a few, then `make seed-reset` and re-seed for the clean run — or set matching pilot values temporarily (e.g. `MAX_RATINGS=4`, `REVIEWERS=4`, `SESSIONS_PER_USER=5` for a 5-prompt pool). A dedicated pilot project (`INTER_RATER_PROJECT`/`PHOENIX_PROJECT_NAME` both pointed elsewhere) keeps the live study's data clean.

4. **Question pool curation.** `data/seed_questions.json` should be reviewed by domain experts before seeding. Once a study has begun, the pool is locked — replacing a question mid-study invalidates the IRR analysis. Edit-then-seed is the workflow; never edit during a live study.

5. **Phoenix project naming.** `INTER_RATER_PROJECT` must match `PHOENIX_PROJECT_NAME` exactly (case-sensitive). Mismatches cause seeded sessions to land in one project while the allocator queries another, surfacing zero sessions to reviewers. Verify the match with `make seed-dry` before launch.

6. **Ethics, consent, and anonymisation.** Get appropriate IRB / ethics-committee approval and signed consent before reviewers begin. ATLAS anonymises user IDs irreversibly via `anonymous_id_service`, but the reviewer-identity → payment-record mapping is the researcher's responsibility and must be stored separately from the rating data.

7. **Data export and backup.** Phoenix annotations are the only source of truth for ratings. Export and back up the project immediately after the study completes, before any reset or cleanup. Phoenix retention policies vary by host — do not assume the data will persist indefinitely.

8. **Outlier handling protocol.** Decide in advance what to do if one reviewer's ratings are systematically distant from the others (e.g. always 5/5, or consistently low). Pre-registering the outlier-exclusion rule (on OSF or similar) avoids post-hoc bias accusations in peer review.

9. **Schedule and fatigue.** At 5–10 minutes per prompt, 20 prompts is 100–200 minutes per reviewer. Encourage reviewers to split this across two sittings rather than rush through in one — rating quality degrades with fatigue. The per-user quota is derived from Phoenix annotations, so reviewers can resume without receiving extra work.

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

**Current Study (20 paid reviewers × 20 ratings = exactly 4 ratings/prompt):**
```bash
INTER_RATER_MAX_RATINGS=4          # 4 inter-raters per session
INTER_RATER_SESSIONS_PER_USER=20   # 20 sessions per user (default)
```
- 100 prompts × 4 ratings = 400 = 20 reviewers × 20 ratings — perfectly saturated 1:1
- Balanced cohort allocation assigns every prompt to exactly 4 reviewers; suitable for Fleiss' κ across the full pool

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
- MAX_RATINGS=4
- SESSIONS_PER_USER=20
- Demand = 20 × 20 = **400 ratings**, distributed by the balanced allocator so each of the 100 sessions receives **exactly 4 ratings** under full attendance
- Ideal balanced outcome with one full no-show: 80 prompts receive 4 ratings and 20 receive 3 — still cleanly above the ≥2 floor

### Workload Estimation

Per-user time commitment:
```
Time per session: ~5-10 minutes (six scales plus comments and fault fields)
Total time = SESSIONS_PER_USER × 5-10 minutes
```

With `SESSIONS_PER_USER=20`: **100-200 minutes per user**

## Operational checks

Two make targets. Both resolve the env file the same way `make seed` does
(`ENV_FILE` > `.env.development` > `.env.production`).

```bash
ENV_FILE=config/.env.production make rater-check
```

Read-only; writes nothing. Runs the pool/cohort pre-flight and the
annotation-shape check together, answering three questions in one command:

- **Is the design still saturated?** The capacity equation
  (`reviewers × sessions_per_user = pool × max_ratings`) is exact, and a pool
  that no longer satisfies it fails closed — blocking submissions as well as
  allocation. Worth running before every session.
- **Do recorded annotations still match what the history reader expects?**
  The reader joins a reviewer's fault tags, Additional Comments and per-scale
  comments to their author by the `[inter-rating-N]` name prefix, because those
  annotations carry no `rater_id` of their own (see *Analysing the annotations*).
  An unrecognised name is silently omitted from history, so this fails loudly
  instead. It imports the extractor's own parser, so it cannot drift from it.
- **Which spans were rated, and when?** Listed newest-first by rating time.
  Paste a span id into Phoenix search to open it directly.

```bash
make rater-load
```

Runs the concurrency test: 20 reviewers, 100 prompts, 4 ratings each, 400
submissions racing across eight simulated workers. Each worker has its own
annotation cache, and Phoenix reads deliberately remain stale, so the test
depends on Redis for both the shared pool snapshot and immediate cross-worker
rater visibility. It asserts the cap holds, the pool saturates exactly, every
reviewer finishes their quota, `AT_CAPACITY` and `ALREADY_RATED` stay distinct,
concurrent duplicates consume one slot, and an out-of-pool span is refused.

It takes **real Redis locks**, so it runs against a scratch database on the same
server — DB 15 by default, overridable with `RATER_TEST_REDIS_DB`, and it
refuses to run if the application is already using that index. Phoenix is
stubbed: Redis holds the coordination, and writing to Phoenix would put
hundreds of junk annotations into a real project. Nothing is written to any
Phoenix project and no project name is needed.

Requires `pytest` (`pip install -r config/requirements-test.txt`); the target
says so rather than failing obscurely.

## Analysing the annotations

Not every annotation in a rating carries `rater_id`. Scores and `Fault Rationale`
do, via `get_annotation_metadata`. **Fault tags, Additional Comments and the ten
per-scale comments do not** — they hardcode `{"qa_id": ...}` and also lack
`is_inter_rater` (GitHub issue #76).

Consequences for anyone reading the data:

- Filtering on `metadata.is_inter_rater` silently misses fault tags and comments,
  and can read an inter-rater's fault tag as baseline user feedback.
- The only link from those annotations to their author is the shared
  `[inter-rating-N]` name prefix.

The history reader therefore joins by that prefix and attributes a group **only
when exactly one `rater_id` appears in it**. A group with no identity, or with
colliding identities, is omitted rather than guessed at — the alternative would
be disclosing one reviewer's rationales as another's. `make rater-check` reports
both counts.

## Manual testing

Before a focus-group session, run the manual acceptance protocol in
[inter_rater_manual_testing.md](inter_rater_manual_testing.md). Part 1 is developer
checks against a deployment; Part 2 is a self-contained walkthrough that can be sent
to a non-technical reviewer.

## Seeding Sessions for Focus Group Testing

For focus-group studies (e.g. 20 raters × 20 ratings each), there is rarely enough organic traffic to provide a pre-populated pool of sessions. The seeding script runs a JSON file of questions through the live RAG pipeline so each question becomes a ratable session in Phoenix — with real LLM answers and real citations, but no baseline feedback (so the only feedback comes from focus-group participants).

### Workflow on prod

```bash
git pull
make seed   # uses config/.env.development by default; override with ENV_FILE
```

**Order matters when `INTER_RATER_DEFAULT_UI=true`.** The manifest is written by
`make seed`, which POSTs to the running backend, so the backend must start before
a pool exists. It does: the missing-manifest check runs when inter-rating builds
an allocation, not at startup, precisely so a first-time study cannot deadlock
(no manifest → no boot → no seeding → no manifest). Between deploying and
seeding, the app runs normally and only the inter-rater page refuses.

Note also that a pilot seed smaller than the study pool will not satisfy the
capacity equation under the study settings — `5 prompts × 4 = 20` against
`20 reviewers × 20 = 400` — so the inter-rater page raises. Either pilot against
the full pool (seed all 100, have 1–2 people rate a few, then `make seed-reset`
and re-seed for the clean run), or set matching pilot values temporarily, e.g.
`INTER_RATER_MAX_RATINGS=4`, `INTER_RATER_REVIEWERS=4`,
`INTER_RATER_SESSIONS_PER_USER=5` for a 5-prompt pool.

The script targets `localhost:8000` directly, so `AUTH_METHOD=cloudflare` stays on for public traffic the entire time — no maintenance window is required.

### Sizing

The seed pool size determines the rating-density per prompt:

```
pool_size = (participants × ratings_per_participant) / INTER_RATER_MAX_RATINGS
```

For the default focus group target (20 reviewers × 20 ratings = 400 ratings) with `MAX_RATINGS=4`, this gives a saturated 1:1 design at **100 prompts × 4 ratings = 400**. Every prompt receives exactly 4 ratings under full attendance, which is the gold standard for inter-rater reliability (single Fleiss' κ across the pool, no mixed-N caveats).

This design assumes paid reviewers with completion-linked payment so attrition is rare. If you cannot assume that, add a buffer of ~20% (pool=120) to protect the ≥2-ratings-per-prompt floor against dropouts — at the cost of mixing 3- and 4-rated prompts in the output. The script derives its demand warning from `INTER_RATER_REVIEWERS` and `INTER_RATER_SESSIONS_PER_USER`.

### Files

- `data/seed_questions.json` — editable list of `{question, corpus_filter}` entries. Update on the server before running `make seed`; no code deployment required.
- `utils/scripts/seed_questions.py` — POSTs each question to `/api/ask/stream`, drains the SSE stream to completion, and verifies that both the LLM span and the `com.atlas.rag.references` (citations) span land in Phoenix.

### Useful options

- `make seed-dry` — validate JSON and print the sizing check without submitting
- `make seed SEED_ARGS="--count 5"` — seed only the first 5 questions (testing)
- `make seed SEED_ARGS="--no-verify"` — skip the post-seed Phoenix verification pass
- `make seed SEED_ARGS="--force-manifest"` — write the study pool manifest even if one
  exists or the run was partial. Needed only when deliberately replacing a pool without
  a reset, or accepting a short pool and re-sizing the study to match. Reviewer completion
  counts are scoped to the active manifest, so ratings from the replaced pool do not consume
  the new cohort's quota.
- `ENV_FILE=config/.env.production make seed` — explicitly use the prod env file (only needed when both env files exist on the same box; otherwise the Makefile auto-falls-back to `.env.production` when `.env.development` is absent)

### Resetting between test runs

For iterative testing of the inter-rating UI, `make seed-reset` deletes the configured `INTER_RATER_PROJECT` from Phoenix entirely — sessions, annotations, the lot. Run `make seed` afterwards to restore the baseline. The reset workflow is intended for dedicated test projects (e.g. set `INTER_RATER_PROJECT=ATLAS-SeedTest` in your env file) so it doesn't disturb organic data.

Safety:
- The script refuses to delete projects whose names contain "prod" or "production" unless `--force` is passed (`make seed-reset SEED_ARGS="--force --yes"`).
- An exact project-name confirmation prompt is required unless `--yes` is passed.

### Behavior

Seeded sessions have no baseline (`original`) feedback. The inter-rater service surfaces them anyway; the first participant rating on a seeded session is tagged `inter_rater_1` (no `original` annotation is ever created for seeded sessions, so all 20 raters are treated symmetrically).

## Architecture
- Backend
  - `backend/services/inter_rater_service.py`: fresh allocation and per-user quota enforcement
  - `backend/services/inter_rater_submission_gate.py`: Redis-serialized capacity check and Phoenix write
  - `backend/services/inter_rater_pool.py`: seeded study pool manifest and cohort fingerprint
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
   - **Enforce `INTER_RATER_MAX_RATINGS`** limit from the active environment
   - **Assign a stable Redis-backed cohort slot** and derive a balanced queue
   - **Limit to `INTER_RATER_SESSIONS_PER_USER`** from the active environment
5. Current annotations are refreshed from Phoenix before allocation; the per-user quota is enforced across reloads.

## Allocation Algorithm Details

When configured demand exactly matches capacity, the allocator uses a balanced
cohort design:

1. Redis atomically assigns each anonymous reviewer a stable slot from
   `0..INTER_RATER_REVIEWERS-1`. The key is a fingerprint of the study pool
   manifest, so reseeding creates a new cohort automatically while span churn
   during a run does not.
2. `_study_assignment` walks the pool in span-ID order and gives each prompt to
   the `max_ratings` slots with the most quota remaining, tie-broken by
   `SHA-256(span_id:slot)`.
3. Because `reviewers × sessions_per_user = pool × max_ratings`, every reviewer
   receives the configured number of distinct prompts and every prompt is assigned
   to exactly `max_ratings` reviewers.

### Why assignment spreads rather than blocks

Exact per-prompt counts are not on their own enough for cohort-wide analysis.
How reviewers overlap *with each other* decides whether rater severity can be
separated from prompt difficulty.

A simpler construction — handing reviewer `slot` a contiguous block starting at
`slot × sessions_per_user` modulo the pool size — also gives every prompt exactly
`max_ratings` ratings. But the modulo wraps, so slots differing by
`pool ÷ sessions_per_user` receive *identical* queues. At the canonical settings
that splits 20 reviewers into 5 disjoint groups of 4, each rating the same 20
prompts: 160 of 190 reviewer pairs then share no prompts at all, and the study
becomes five unrelated studies of 20 prompts rather than one study of 100.
Rater severity is confounded with prompt block, no reviewer can be compared
against the wider cohort, and the four reviewers holding identical queues
collide on the same spans in the submission gate.

Quota-greedy assignment with a hash tiebreak keeps the same exact saturation
while spreading each reviewer's prompts across the whole pool. Measured at the
canonical settings:

| design | ratings/prompt | prompts/reviewer | pairs sharing nothing | mean pair overlap |
|---|---|---|---|---|
| contiguous block | all 100 at exactly 4 | 20 | 160 / 190 | 3.16 |
| quota-greedy (current) | all 100 at exactly 4 | 20 | 11 / 190 | 3.16 |

Note that mean overlap is identical, so it cannot be used as the check on its
own — the block design reaches the same mean by pairing a few reviewers on
entire queues and the rest on nothing. `test_reviewer_pair_overlap_is_evenly_spread`
asserts the spread, not just the mean.

If demand and capacity do not match exactly, the service falls back to count-aware
ranking: `inter_rater_count ASC`, then `SHA-256(span_id:user_id)` as a stable
tiebreaker. Each allocation refreshes annotations from Phoenix before applying
either strategy.

### Concurrent raters and the submission-time cap

The balanced design deliberately assigns each prompt to the configured number of
reviewers, so normal concurrent work does not create over-cap conflicts. The
dashboard can still encounter stale work after manual project changes or legacy
allocations; it drops those spans and fetches replacements. The backend enforces
the total per-user quota across reloads.

`INTER_RATER_MAX_RATINGS` is therefore enforced in two places:

- **At allocation** (`inter_rater_service.py`) — a fresh Phoenix annotation query
  removes capped spans from `available_sessions`.
- **At submission** (`inter_rater_submission_gate.py`) — a Redis per-span lock is
  acquired across all application workers, the span is refreshed from Phoenix, and
  the lock is held through the synchronous annotation write. A capped span returns
  `session_unavailable`; the dashboard fetches replacement work.

`tests/backend/services/test_inter_rater_allocation_coverage.py` quantifies both
against the real allocator (100 prompts, 20 raters, 20 ratings each, cap 4):

| scenario | total | prompts <2 | prompts ==4 | prompts >4 | max |
|---|---|---|---|---|---|
| sequential arrival | 400 | 0 | 100 | 0 | 4 |
| concurrent arrival | 400 | 0 | 100 | 0 | 4 |
| unbalanced snapshot, no submission cap | 400 | **9** | 12 | 45 | **10** |

The balanced allocator gives the perfect saturated design for both arrival
patterns. The final row documents the former hash-snapshot failure mode: without
balanced assignments or a submission cap, 9 prompts fall below the 2-rating floor
and 45 exceed the cap, one reaching 10 ratings.

Note that reducing `INTER_RATER_SESSIONS_PER_USER` is not a substitute: smaller
snapshots protect the floor but never prevent over-cap ratings.

The guard fails closed: if Redis or the Phoenix refresh is unavailable, no
annotation is written and the reviewer is asked to retry. This protects the study
from silent over-cap writes. Production and staging deployments already require
Redis; `REDIS_URL` is therefore required for inter-rater submissions.

### Progressive Filling

As users complete ratings, sessions fill up:

```
Initial State:
- Session 001: 0/4 ratings
- Session 002: 0/4 ratings
- Session 003: 0/4 ratings

After User A rates:
- Session 001: 1/4 ratings ✓
- Session 002: 1/4 ratings ✓
- Session 003: 1/4 ratings ✓

After User B rates:
- Session 001: 2/4 ratings ✓
- Session 002: 2/4 ratings ✓
- Session 003: 2/4 ratings ✓

After Users C and D rate:
- Session 001: 4/4 ratings [FULL - removed from allocation]
- Session 002: 4/4 ratings [FULL - removed from allocation]
- Session 003: 4/4 ratings [FULL - removed from allocation]
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
3. Backend acquires the Redis lock for the Phoenix project/span
4. While holding the lock, backend refreshes the span's annotations and rejects capped or duplicate work
5. Inter-rater number is calculated as `existing_count + 1`, and feedback is written before the lock is released
6. Inter-rater entries:
   - Annotation names are prefixed with numbered format: `[inter-rating-1]` through `[inter-rating-4]`
   - Annotation IDs include the number for uniqueness: `inter_rater_{rater_id}_{number}_{qa_id}_{timestamp}`
   - Metadata includes `is_inter_rater=true`, `rater_id=<anon_id>`, `inter_rater_number=<N>`, `original_span_id=<phoenix_span>`
7. On success, local state and the user's cached statistics are updated immediately

## Reviewer navigation and rating history

- **Rating history.** A reviewer can review their own completed ratings during a
  run, from a button on the task, the completion state, or the error state.
  Read-only, own ratings only, current run only — see `openspec` change
  `update-inter-rater-reviewer-ux`, design decision 1, for the anchoring-versus-
  drift trade-off behind allowing it mid-run.
- **In-app navigation.** The task is kept alive across a detour to FAQ or About,
  so returning issues no allocation request and shows no loading state.
- **Retained state has two scopes.** *Position* belongs to one
  `allocation_snapshot_id` and is discarded when the pool changes. *Which prompts
  the reviewer has already rated* belongs to the reviewer and survives any pool
  change — it masks the window in which a worker that did not take the submission
  is still waiting on Phoenix propagation. Conflating the two is what previously
  let a capacity refusal suppress a prompt the reviewer never rated.
- **Refusals are distinguishable.** `ALREADY_RATED`, `AT_CAPACITY` and
  `OUT_OF_POOL` are separate statuses. A reviewer's own duplicate is reported as
  such, not as a concurrency loss.
- Only an authoritative history response prunes the local rated-prompt record —
  never a size cap or timeout, which could lift the mask before propagation
  completes.

## Anonymity & Privacy
- Anonymous IDs: `anonymous_id_service` hashes the Cognito `sub` with an environment-specific salt, producing `anon_<16-hex>` IDs
- No client IP collection/logging/export
- No emails or usernames logged
- Phoenix submissions contain only anonymized identifiers and rating metadata

## Evaluation Fields (Order)

The rubric shipped in `InterRaterPlayback.vue` and `ExtendedFeedback.vue` uses these
six Likert scales, in this order:

1. **Corpus Fidelity** (1–5) — groundedness in the retrieved corpus
2. **Citation Quality** (1–5)
3. **Relevance** (1–5)
4. **Coherence** (1–5) — well-reasoned and argued response
5. **Uncertainty** (1–5) — flags contested interpretations, gaps, ambiguity
6. **Historical Contextualisation** (1–5)

Plus:
- **Per-scale comments** — one free-text rationale per scale, required when the
  rating is extreme (1, 2 or 5); see `isCommentRequired`
- **Faults** — `hallucination`, `harmful_handling` (checkboxes)
- **Fault rationale** — free text, required when any fault is checked
- **Comments** — overall free text

> Superseded rubric: earlier versions used Factual Accuracy, Analysis Quality,
> Difficulty and Clarity. These were replaced by Citation Quality, Coherence,
> Uncertainty and Historical Contextualisation respectively, and the
> `inappropriate` fault was renamed `harmful_handling`. The old fields remain on
> the `UserFeedback` model and the Phoenix write path for backward compatibility
> with previously collected data, but the inter-rater UI no longer collects them.
> **Rater briefings must document the six scales above**, not the superseded set —
> rubric drift between briefing and UI depresses IRR directly.

## API Endpoints
- `GET /api/inter-rater/stats`
  - Returns user-specific availability and limits
  - **Requires Authentication**: Cognito JWT token in Authorization header
- `GET /api/inter-rater/sessions`
  - Returns the list of sessions available to the current user
  - Also returns `allocation_snapshot_id`, identifying the exact pool snapshot the
    allocation came from. The client keys its saved position on this, so a reseed
    cannot resurrect a stale allocation. Distinct from the cohort fingerprint,
    which is derived from manifest `qa_id`s, is `None` in ad-hoc mode, and is
    deliberately stable across span churn.
  - **Requires Authentication**: Cognito JWT token in Authorization header
- `GET /api/inter-rater/history`
  - Returns the requesting reviewer's **own** recorded ratings for the current
    pool: prompt, rated answer, scores, per-criterion rationales, fault tags.
  - Read-only. Scoping is server-side by `rater_id` taken from the request — a
    reviewer cannot ask for anyone else's ratings, and there is no write counterpart.
  - **Requires Authentication**: Cognito JWT token in Authorization header
- `POST /api/feedback`
  - Submits both regular and inter-rater feedback; inter-rater metadata is set server-side
  - **Requires Authentication**: Cognito JWT token in Authorization header
- `GET /api/debug/user-id` *(Development only)*
  - Debug endpoint to verify user ID extraction from JWT tokens

## Caching and concurrency
- The **study pool is cached for 60 seconds and shared across reviewers**. The
  Phoenix span query is the expensive part of an allocation and returns the same
  pool for everyone, so it is fetched once rather than per request. It is fetched
  without per-user exclusion; the self-authored filter is applied locally so one
  cached pool can serve every reviewer.
- Caching the pool is only safe because a reviewer's queue no longer depends on
  live rating counts: cohort assignment is deterministic, and the authoritative
  cap check happens under a distributed lock at submission. A count that goes
  stale within the TTL can only mean a reviewer is shown a prompt that has since
  filled — the gate rejects it and the dashboard fetches replacement work.
- Per-user navigation statistics have a five-minute cache and are invalidated after submission.
- Submission count/write operations are serialized by a Redis lock scoped to
  project and span. Successful rater identities are also retained briefly in a
  Redis set, bridging the interval before another worker can read the new
  annotation from Phoenix and preventing that worker from overfilling the span.
- **Pool membership is checked before that lock is taken.** Membership does not
  race with other submissions, and the check can be a cold Phoenix query — the
  pool cache expires in 60s while reviewers take minutes to rate. Holding the
  span lock across it would starve the other reviewers of the same prompt, who
  give up after `LOCK_WAIT_SECONDS`.
- **Membership comes from a Redis-shared pool snapshot**, not a per-worker cache.
  Production runs 8-16 Gunicorn workers, each of which would otherwise hold its
  own 60s pool cache and could reject a span another worker had just served.
  Refresh is guarded by a lock whose wait is
  `INTER_RATER_POOL_REFRESH_LOCK_WAIT_SECONDS` (default 30s, validated at startup).
- A submission for a span outside the current pool is refused server-side and
  fails closed if membership cannot be established. Client-supplied `qa_id` or
  snapshot identifiers are never treated as proof of membership.
- The dashboard requests replacement work after `session_unavailable` until its configured quota is complete.

## The study pool

`make seed` writes the path configured by `INTER_RATER_POOL_MANIFEST`, recording
the `qa_id` of every prompt it created, and the allocator treats exactly those
prompts as the study pool. The path has no code default because it is
environment-specific. Seeding and reset commands fail before making changes if
the setting is absent; the backend interprets an absent setting as explicit
ad-hoc mode over all eligible project spans.

This gives four properties the study depends on:

- **Purity** — organic traffic in the same Phoenix project cannot enter the pool,
  so reviewers only see prompts they were briefed on.
- **A single shared pool** — derived from a live query the pool is *not* the same
  for everyone, because `query_spans_for_inter_rating` drops sessions the
  requesting reviewer authored. Two reviewers with differently-sized pools would
  land in different cohorts and be handed the same queue.
- **A stable cohort key** — reviewer slots are keyed on the manifest fingerprint,
  so adding, deleting, or slow-indexing a span cannot re-slot the cohort
  mid-study. Filtering and fingerprinting use the same loaded snapshot, and
  manifest writes use atomic replacement, so a concurrent re-seed cannot combine
  old prompts with a new cohort key. Re-seeding intentionally changes the
  fingerprint and starts a fresh cohort.
- **Study-scoped completion** — the per-reviewer quota counts only ratings whose
  span IDs belong to the active manifest. Ratings from an earlier pool in the
  same Phoenix project cannot shorten a replacement cohort. Allocation, stats,
  and the sessions API all use this same scoped count, so the frontend cannot
  declare completion early from ratings belonging to a replaced pool.

`make seed-reset` deletes the manifest along with the project, since a manifest
naming deleted spans would surface an empty pool. If the manifest is absent the
allocator falls back to every eligible span in the project, which is the right
behaviour for ad-hoc inter-rating outside a study.

### Guards

A wrong manifest changes the study design without changing anything visible, so
each of these fails loudly rather than degrading:

- **Partial seeding is never recorded.** If any prompt fails, `make seed` writes
  no manifest and says so. A manifest listing only the prompts that happened to
  succeed shrinks the pool, breaks the capacity equation, and drops allocation
  back to unbalanced ranking.
- **An existing manifest is never overwritten.** `make seed` checks before any
  API submission, refuses with a non-zero exit, and reports the existing prompt
  count, so a pilot run (`--count 5`) cannot create untracked spans or quietly
  replace a full study pool. It checks again before the final atomic write in
  case another seeder created a manifest while the prompts were generated.
  `make seed-reset` removes it first, so the documented workflow is unaffected.
  `SEED_ARGS="--force-manifest"` overrides both guards.
- **Cross-environment manifests are rejected.** The manifest records the project
  it was seeded for; loading it against a different `INTER_RATER_PROJECT` raises
  rather than silently matching no spans.
- **A pool that no longer fits the configuration raises.** If the eligible span
  count means `reviewers × sessions_per_user ≠ pool × max_ratings`, allocation
  fails with the actual numbers instead of falling back to unbalanced ranking.
  Reviewers see an error, which is recoverable; silently under-rating part of an
  unrepeatable session is not. Only enforced in study mode.

Because the last guard raises before the pool is cached, a persistent mismatch
means every request re-queries Phoenix until it is fixed. It is meant to be a
stop, not a steady state.

Check the manifest matches the intended pool before reviewers arrive:

```bash
python3 -c "import json,os; d=json.load(open(os.environ['INTER_RATER_POOL_MANIFEST'])); print(d['count'], d['project'])"
```

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
  - Confirm the six current Likert scales and any required rationales appear in Phoenix
- **Duplicate rating prevented**: Backend checks if the same rater already rated the same original span
- **Submission asks reviewer to retry**: verify Redis and Phoenix availability; the cap guard fails closed
- **Phoenix shows the project as empty (0 traces, 0 spans) after ratings**:
  - Inter-rating writes **span annotations onto existing spans**. It creates no
    new spans or traces, so the counts never move when a rating is recorded.
  - The Phoenix project view filters by span age. Seeded spans keep their
    original timestamps, so a pool seeded more than the filter window ago
    disappears from the UI entirely. Widen the time range to 30 days or all time.
  - `make rater-check` lists rated spans newest-first by rating time; paste a
    span id into Phoenix search to open it directly.
- **A prompt is refused as out of pool**: the pool changed (reseed, span churn)
  after the reviewer was served it. Expected; the dashboard fetches replacement
  work. If it happens to every submission, the shared snapshot is stale or
  Redis is unreachable — check the backend log for "Cannot establish current pool".

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
