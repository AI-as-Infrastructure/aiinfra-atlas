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
      `handledSpanIds` (`InterRaterDashboard.vue:128`).
- [ ] 3.2 Persist run *position* to session storage, keyed per reviewer AND by
      the pool fingerprint (`_get_pool` returns one alongside the sessions,
      `inter_rater_service.py:299`). Keying by reviewer alone lets a stale
      allocation rehydrate after a reseed. Discard persisted state whose
      fingerprint does not match the current pool.
- [ ] 3.2a Reject submissions for spans outside the current pool. The gate
      (`inter_rater_submission_gate.py:88-97`) checks already-rated and
      max_ratings but never manifest membership, so a stale span rehydrated
      from client state is currently accepted. Client-side fingerprint checks
      are not sufficient on their own.
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
      `get_annotation_metadata()`, but **fault tags** (`feedback.py:657`) and
      **Additional Comments** (`feedback.py:672`) hardcode their metadata and
      carry neither `rater_id` nor `is_inter_rater`. The extractor must join
      them to their author through the `[inter-rating-N]` group.
      Because that join is the only link, it is also the disclosure risk for
      the "own ratings only" SHALL: test explicitly that a malformed, missing,
      or colliding group number cannot attach another reviewer's fault tags or
      comments to this reviewer's history. Prefer omitting an unjoinable
      annotation over guessing its author.
- [ ] 3.4b Raise separately (#76): those same two annotation types lack
      `is_inter_rater`, so metadata alone cannot tell an inter-rater's fault
      tags from a baseline reviewer's. Recoverable from the name prefix, no
      live consumer today — out of scope here.
- [ ] 3.5 Fail loudly when the history read fails — say so, rather than
      rendering an empty history that reads as authoritative.
- [ ] 3.6 Rehydrate on mount instead of refetching when valid state exists.

## 4. Navigation and history (#72, #73) — depends on 3
- [ ] 4.1 Wrap the `/inter-rater` route view in `<KeepAlive>` so an in-app
      detour does not unmount the dashboard.
- [ ] 4.2 Suppress the full-page loading state
      (`InterRaterDashboard.vue:3-8`) when the allocation is already known.
- [ ] 4.3 Filter rated spans from the presented allocation using the persisted
      `handledSpanIds`, so Back and reload cannot re-present them.
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
- [ ] 6.4 `openspec validate update-inter-rater-reviewer-ux --strict`
- [ ] 6.5 Close #67, #70, #71, #72, #73 with the verifying evidence.
