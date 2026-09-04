# Review brief — implementation of `update-inter-rater-reviewer-ux`

Commits under review: `a107cce`, `fcc0763` (sequential on `main`, nothing else on top).
Diff: `git diff 6486eec..fcc0763 -- backend/ frontend/ tests/`

The author of this code has **never run the application**. Verification so far is
a clean `vite build`, successful backend imports, and a unit suite that went
101 → 112 passing with no new failures. Treat every claim below as unproven at
runtime.

This is going into production shortly before an unrepeatable focus group
(20 reviewers, 20 prompts each, 4 ratings per prompt). A rating that fails to
record cannot be recovered.

---

## Where to concentrate

Risk is not evenly spread. In descending order:

**1. The submission gate can now refuse to record a rating.**
`backend/services/inter_rater_submission_gate.py`. This is the only change that
can lose data. It rejects spans outside the current pool and fails closed when
the pool cannot be established. It also calls `_validate_study_capacity`
(via `_get_pool`) on the submission path, which never invoked it before — so a
manifest problem that previously blocked only allocation now blocks submissions
too. Verify the failure modes are the intended ones and that a healthy pool
cannot produce a spurious `OUT_OF_POOL`.

Already found and fixed once here: the membership check was originally inside
`_span_lock`, which would have held a distributed lock across a cold Phoenix
query while other reviewers of the same span timed out after 15s
(`LOCK_WAIT_SECONDS`). Look for anything similar.

**2. Client run state can suppress prompts that were never rated.**
`frontend/src/stores/interRater.js`. `recentlyRated` (reviewer-scoped, survives
a snapshot change) and `unavailable` (snapshot-scoped, discarded) must not be
conflated — that conflation is the bug the change exists to fix. A capacity
refusal entering `recentlyRated` would permanently hide a prompt the reviewer
never rated.

**3. History could disclose another reviewer's data.**
`backend/services/annotations_cache.py:270-350`. Fault tags, Additional Comments
and the ten per-scale comments carry no `rater_id`; they are joined to an author
only by the `[inter-rating-N]` name prefix. Prod runs `MAX_RATINGS=4`, so
multiple raters share every span — this is the first time the join is exercised
against real multi-rater data.

**4. Everything else** — tooltips, citation card — is cosmetic and additive.

---

## Requirement → implementation map

Spec deltas: `specs/inter-rater/spec.md`, `specs/feedback/spec.md`.

### feedback: Tooltip Rendering Mechanism
- `frontend/src/components/InfoTooltip.vue` — app-rendered, `position: fixed`,
  measured and clamped before paint, 18px target, keyboard focus.
- Used by `InterRaterPlayback.vue` and `ExtendedFeedback.vue` (8 each).
- `CitationList.vue` — dead `has-tooltip-arrow` class removed.
- Not converted: `AIEnhancedFeedback.vue`, `FeedbackPrompt.vue` still use native
  `title`. Deliberate — they carry the legacy rubric the v0.4.0 spec replaced.
  Confirm that is acceptable.

### inter-rater: Citation Hover Card Placement
- `InterRaterPlayback.vue` — `showCitationCard`/`hideCitationCard`, fixed
  positioning, prefers above and drops below only when there is no room.
- Same fix applied to `ChatHistory.vue`, which shares the pattern.
- `.message-style-container`'s `overflow: hidden` is untouched; fixed
  positioning escapes it instead.

### inter-rater: Reviewer Rating History
- Endpoint: `backend/routers/inter_rater.py:70-128` (`GET /api/inter-rater/history`).
  Reviewer identity comes from the request, never a parameter.
- Extractor: `annotations_cache.py:270` `get_user_inter_rater_rating`,
  `:318` `_build_rating`, `:61` `_parse_inter_rater_name`.
- **Attribution rule:** a `[inter-rating-N]` group is attributed only when
  exactly one `rater_id` appears in it. No identity, or colliding identities →
  omitted, never guessed.
- View: `frontend/src/components/InterRaterHistory.vue` — read-only, no editable
  control, no path back into a rating form. Overlay, so the dashboard stays
  mounted and the reviewer returns to their in-progress item.
- Failure is stated, not rendered as an empty history.
- Tests: `tests/backend/services/test_inter_rater_history_extractor.py` (7).

### inter-rater: Rated Sessions Are Not Re-Presented
- `stores/interRater.js` — `recentlyRated` / `unavailable` split; `markRated`
  vs `markUnavailable`; `applyAllocation` filters by both.
- `allocation_snapshot_id`: `inter_rater_service.py:184` (derivation),
  `:308` (accessor), `routers/inter_rater.py:55` (returned).
  Hashed from `(span_id, qa_id)` pairs **before** per-reviewer filtering, so it
  exists in ad-hoc mode where the cohort fingerprint is `None`, and does not
  move when ratings are submitted.
- Server-side membership: `inter_rater_service.py:316`
  `span_ids_in_current_pool`, consumed by the gate.
- Distinct refusals: `SubmissionStatus.ALREADY_RATED` / `AT_CAPACITY` /
  `OUT_OF_POOL`, mapped in `backend/telemetry/api.py:199-218`.
- `pruneConfirmed` — only an authoritative history response prunes the local
  mask; no size cap or timeout, which could lift it before Phoenix propagates.

### inter-rater: Task State Survives In-App Navigation
- `frontend/src/App.vue` — `<KeepAlive :include="['InterRaterPage']">`.
- `InterRaterDashboard.vue` — `onActivated` issues no request when state is
  validated; full-page spinner suppressed when the allocation is known.

### inter-rater: Immediate Reviewer Count Refresh
- `InterRaterDashboard.vue` `announceProgress()` — dispatched after every
  success, no `setTimeout`. Five-minute poll retained in `InterRaterButton.vue`.

---

## What review cannot settle

Please do not sign these off from reading:

- **Whether the tooltips appear in Chrome.** The original defect (#70) was
  browser behaviour that passed code review once already.
- **Whether real Phoenix annotation names match the extractor's expectations.**
  If prod names differ from `[inter-rating-N] <base>`, history silently returns
  nothing. This is checkable with a read-only query against the live project and
  is the highest-value empirical check available.
- **Lock contention** under 20 concurrent reviewers.
- **Whether the pool is exactly 100 spans**, which the capacity equation
  (`20 × 20 = 100 × 4`) requires and which now gates submissions as well as
  allocation.

## Known-unfinished

12 of 44 tasks are unchecked in `tasks.md` and all require a running stack:
1.1, 1.7, 2.4, 4.9, 5.3, 6.1-6.5, plus 0.2 (archive
`release-inter-rater-v0-4-0` first).

## Pre-existing, not introduced here

- 5 `test_inter_rater_pool.py` failures from a `PHOENIX_PROJECT_NAME` leak out of
  the modules tests; 6 `test_phoenix_inter_rater_async.py` failures from an
  authlib/httpx metaclass conflict. Both reproduce at `HEAD` in a worktree given
  the same untracked config.
- `_USER_FEEDBACK_NAMES` is stale (#75) and deliberately untouched — it can move
  allocation. See `design.md` Decision 4.
