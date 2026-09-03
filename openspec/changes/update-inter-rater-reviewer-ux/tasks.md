# Tasks

## 0. Confirm before implementation
- [x] 0.1 Study lead confirmed Decision 1 in `design.md` (2026-09-03): rating
      history is available **during** the run, restricted to the reviewer's
      **own** ratings, **read-only**, and scoped to the **current run** only.
      Loosening any of those three constraints reopens Decision 1.
- [ ] 0.2 Confirm `release-inter-rater-v0-4-0` is archived, so the `inter-rater`
      capability exists in `openspec/specs/` before this change archives.

## 1. Tooltip rendering (#70) — independent of 2-5
- [ ] 1.1 Reproduce in Chrome and record the actual cause: hover-target size,
      `<label>` hit-testing, or both. Note it on #70.
- [ ] 1.2 Replace the native `title` mechanism in
      `frontend/src/components/InterRaterPlayback.vue` (rubric tooltips at lines
      104, 144, 184, 224, 264, 304; fault tooltips at 355, 366) with an
      application-rendered tooltip driven by a data attribute.
- [ ] 1.3 Apply the same treatment to the standard extended feedback form so both
      form variants share one mechanism.
- [ ] 1.4 Enlarge the ⓘ hover target to at least 16×16 CSS pixels.
- [ ] 1.5 Add viewport-edge handling so no tooltip is clipped.
- [ ] 1.6 Resolve `frontend/src/components/CitationList.vue:7-8`, where
      `has-tooltip-arrow` names a Bulma extension the project does not load:
      back it with real behaviour or remove the class.
- [ ] 1.7 Verify every rubric and fault definition renders on hover in Chrome,
      Firefox and Safari, and that the text matches the `feedback` spec.

## 2. Citation hover card (#71) — independent of 1, 3-5
- [ ] 2.1 Replace the fixed `left: 50%; transform: translateX(-50%)` placement at
      `InterRaterPlayback.vue:972-981` with collision-aware positioning.
- [ ] 2.2 Resolve the clipping from `overflow: hidden` on
      `.message-style-container` (line 793) — relax it or render the card outside
      the container.
- [ ] 2.3 Check upward vs downward opening so the card does not conceal the
      answer text being rated.
- [ ] 2.4 Verify the leftmost, rightmost and wrapped-row citations all show a
      fully visible card.
- [ ] 2.5 Check the same pattern in the standard chat view, which shares it.

## 3. Run state and history source — prerequisite for 4 and 5
- [ ] 3.1 Move the dashboard's run state out of `setup()` locals and into the
      Pinia store: allocation, current index, completed count, and
      separate `recentlyRatedSpanIds` and `unavailableSpanIds` sets. The current
      `handledSpanIds` (`InterRaterDashboard.vue:126`) mixes successful ratings
      with `session_unavailable` refusals (lines 205-206 and 233-236) and cannot
      be persisted with one lifetime.
- [ ] 3.2 Add an `allocation_snapshot_id` to the sessions response and persist
      run *position* to session storage keyed per reviewer and by that id. This
      is **not** the cohort/manifest fingerprint: `inter_rater_pool.py:132-155`
      shows that fingerprint is `None` in ad-hoc mode and intentionally stable
      across span churn. Derive the new id from the authoritative `span_id` and
      `qa_id` pairs in the exact shared pool snapshot, before per-reviewer rating
      and capacity filtering, so it exists in every mode and changes whenever
      the actual pool spans change. Return it from `/api/inter-rater/sessions`.
      After a reload, compare the server value before restoring saved position;
      on mismatch use the fresh allocation and replace the stored position.
      Persist `recentlyRatedSpanIds` under a **reviewer-only** key, not the
      snapshot key; keep `unavailableSpanIds` with snapshot-scoped position —
      see 3.2b.
      An in-app KeepAlive return still performs no allocation request. Test that
      the id is non-empty in ad-hoc mode, changes when pool span membership
      changes, and does not change merely because ratings are submitted or a span
      reaches its rating cap.
      Caveat for ad-hoc mode: the pool query truncates to
      `limit=sessions_per_user * 10` after sorting by timestamp descending
      (`phoenix_client.py:235-236`) within a `days_back` window, and
      `_validate_study_capacity` returns early without a manifest
      (`inter_rater_service.py:242-256`). So in ad-hoc mode ordinary organic
      traffic can change pool membership with no reseed and no loud failure,
      invalidating retained state. This sensitivity is accepted: ad-hoc mode has
      no stable run boundary, and retaining a snapshot that differs from the
      bounded live query would preserve spans the server no longer considers
      current. Study mode is protected because its manifest defines the run and
      the capacity validation raises when that pool is incomplete.
- [ ] 3.2b Split `handledSpanIds` by outcome and lifetime. Add a span to
      reviewer-scoped `recentlyRatedSpanIds` only after submission success or a
      distinct duplicate refusal confirming that this reviewer already rated
      it. A capacity or out-of-pool refusal SHALL NOT enter that set; if local
      suppression is needed, add it to snapshot-scoped `unavailableSpanIds`,
      which is discarded when the snapshot changes.
      The recently-rated set masks a real server-side race:
      `check_user_already_rated` consults the process-local
      `_local_ratings` set (`annotations_cache.py:60, 167`), production runs
      gunicorn with 8-16 workers (`deploy/production/production.sh:387`,
      `deploy/cloudflare/cloudflare.sh:296`), so a worker that did not receive
      the submission must wait for Phoenix propagation before
      `get_sessions_for_inter_rating` filters the span. That window is exactly
      why `InterRaterDashboard.vue` removes the rated session locally rather
      than refetching. Apply `recentlyRatedSpanIds` to every fresh allocation,
      including after a snapshot change. Reconcile it through the reviewer
      history endpoint: keep an entry while the server has not exposed that
      recorded rating, then prune it after an authoritative history response
      confirms the rating. Do not use arbitrary size eviction or expiry that can
      remove the mask before server propagation completes.
- [ ] 3.2a Reject submissions for spans outside the current pool. The gate
      (`inter_rater_submission_gate.py:88-97`) checks already-rated and
      max_ratings but never manifest membership, so a stale span rehydrated
      from client state is currently accepted. Validate the submitted `span_id`
      against an authoritative server-side pool snapshot; do not trust the
      client's `qa_id` or `allocation_snapshot_id`, and fail closed when current
      membership cannot be verified. Client-side snapshot checks are not
      sufficient on their own.
- [ ] 3.3 Add a read endpoint returning the requesting reviewer's own recorded
      ratings for the current pool, scoped server-side by `rater_id`. History is
      derived from this, not from client storage, so it survives a closed tab.
      Reuse the existing annotation path
      (`backend/services/annotations_cache.py:169-204`).
- [ ] 3.4 Write an inter-rater score extractor in `annotations_cache.py`. None
      exists — every inter-rater function there returns counts or identities,
      never scores, and `get_user_feedback` is not reusable because it
      deliberately skips inter-rater annotations (line 107). Key it on the six
      annotation names the current rubric writes: `Corpus Fidelity`,
      `Citation Quality`, `Relevance Rating`, `Coherence`, `Uncertainty`,
      `Historical Contextualisation`, plus the per-criterion rationales and
      `Fault:` tags. Note `get_annotation_name` (`feedback.py:365-372`)
      *prefixes* inter-rater annotations — `"[inter-rating-N] Corpus Fidelity"`
      — and falls back to the `"[Inter-rater] "` prefix when the number is
      missing. Match on the prefix, and handle the numberless fallback.
      Do NOT extend `_USER_FEEDBACK_NAMES` for this — that frozenset gates the
      baseline-feedback path, not this one.
- [ ] 3.4a Filtering on `rater_id` alone loses data and is unsafe. Verified:
      score and Fault Rationale annotations carry `rater_id` via
      `get_annotation_metadata()`, but **fault tags** (`feedback.py:657`),
      **Additional Comments** (`feedback.py:672`) and the **per-scale comment
      annotations** actually submitted by `InterRaterPlayback.vue:686-690`
      (`feedback.py:690-715`) hardcode metadata without `rater_id` or
      `is_inter_rater`. The extractor must join all of them to their author
      through the `[inter-rating-N]` group.
      Because that join is the only link, it is also the disclosure risk for
      the "own ratings only" SHALL: test explicitly that a malformed, missing,
      or colliding group number cannot attach another reviewer's fault tags or
      any comment or rationale to this reviewer's history. Cover every
      metadata-poor annotation type in the tests, and prefer omitting an
      unjoinable annotation over guessing its author.
- [ ] 3.4b (#76 updated 2026-09-03 to cover all three.) Metadata-poor types are
      fault tags, Additional Comments and the ten per-scale comment annotations. Each lacks `is_inter_rater`,
      so metadata alone cannot distinguish an inter-rater annotation from a
      baseline reviewer's. Recoverable from the name prefix, with no live
      consumer before this history reader — the writer-format cleanup remains
      out of scope here.
- [ ] 3.5 Fail loudly when the history read fails — say so, rather than
      rendering an empty history that reads as authoritative.
- [ ] 3.6 Use the live Pinia state without refetching when `<KeepAlive>`
      reactivates the route during an in-app return. After a reload or genuine
      remount, fetch the current sessions response first and rehydrate persisted
      position only when its `allocation_snapshot_id` matches; otherwise discard
      the saved position and use the fresh allocation. Never render a persisted
      allocation before that server validation. `recentlyRatedSpanIds` survives
      a snapshot mismatch and is applied to the fresh allocation; the
      snapshot-scoped `unavailableSpanIds` set does not — see 3.2b.

## 4. Navigation and history (#72, #73) — depends on 3
- [ ] 4.1 Wrap the `/inter-rater` route view in `<KeepAlive>` so an in-app
      detour does not unmount the dashboard.
- [ ] 4.2 Suppress the full-page loading state
      (`InterRaterDashboard.vue:3-8`) when the allocation is already known.
- [ ] 4.3 Filter rated spans from the presented allocation using the persisted
      `recentlyRatedSpanIds`, so Back and reload cannot re-present them. Filter
      snapshot-local capacity refusals with `unavailableSpanIds`, without
      treating them as ratings by this reviewer.
- [ ] 4.4 Build the read-only rating history view: prompt, rated answer, own
      scores and fault tags. No editable control, no path back into a rating form.
- [ ] 4.5 Gate history strictly to the requesting reviewer — verify no other
      reviewer's scores or identity can be reached from it.
- [ ] 4.6 Make history reachable mid-run, and confirm opening it consumes,
      forfeits and reorders nothing: the reviewer returns to the item they were
      rating with any in-progress scores intact.
- [ ] 4.7 Scope history to the current run — verify a reviewer who rated in an
      earlier cohort sees only this allocation.
- [ ] 4.8 Distinguish a refused duplicate from a full prompt. This needs a
      **backend** change first: the gate returns `SubmissionStatus.UNAVAILABLE`
      for both "already rated" (`inter_rater_submission_gate.py:88`) and "at
      max_ratings" (line 92), and `api.py:199-204` collapses both into one
      `session_unavailable` message. Add a distinct status or a reason field,
      then map it in `InterRaterDashboard.vue:230-240`. A frontend-only change
      cannot tell the two cases apart.
- [ ] 4.9 Measure `GET /api/inter-rater/sessions` warm and cold; if it is slow
      warm, raise that separately rather than absorbing it here.

## 5. Header count (#67) — depends on 3
- [ ] 5.1 Dispatch `inter-rater-completed` after every successful submission in
      `handleFeedbackSubmission`, not only from `showCompletionMessage`
      (`InterRaterDashboard.vue:293`).
- [ ] 5.2 Remove the 3-second `setTimeout` from the refresh path.
- [ ] 5.3 Confirm the header count and the task view's completed count agree
      immediately after a submission.
- [ ] 5.4 Keep the 5-minute poll in `InterRaterButton.vue:31` as a backstop.

## 6. Validation
- [ ] 6.1 Full reviewer run in Chrome, Firefox and Safari: rate several items,
      detour to FAQ and About, use Back and Forward, reload mid-run, open
      history, and confirm no rated prompt is re-presented.
- [ ] 6.2 Confirm no duplicate annotations reached Phoenix and that
      `[inter-rating-N]` numbering is unbroken.
- [ ] 6.3 Confirm inter-rater eligibility and allocation are unchanged: same
      pool size, same per-reviewer quota, capacity equation still satisfied.
- [ ] 6.4 Exercise allocation-snapshot invalidation in manifest-backed and ad-hoc
      modes: unchanged pool with new ratings retains state; changed span
      membership discards it; spoofed client identifiers do not bypass the
      submission membership check; an unavailable membership source fails closed.
- [ ] 6.5 Exercise the state split by outcome: success and confirmed duplicate
      enter `recentlyRatedSpanIds`; capacity and out-of-pool refusals enter only
      snapshot-scoped unavailable state; a snapshot change clears the latter but
      not the former; authoritative history confirmation prunes the former
      without allowing the prompt to reappear.
- [ ] 6.6 `openspec validate update-inter-rater-reviewer-ux --strict`
- [ ] 6.7 Close #67, #70, #71, #72, #73 with the verifying evidence.
