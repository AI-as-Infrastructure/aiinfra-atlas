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
- [ ] 3.2 Persist run *position* to session storage, keyed per reviewer — where
      the reviewer is in the allocation, not the ratings themselves.
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
      `Fault:` tags. Note `get_annotation_name` suffixes inter-rater
      annotations with `[inter-rating-N]`, so match accordingly.
      Do NOT extend `_USER_FEEDBACK_NAMES` for this — that frozenset gates the
      baseline-feedback path, not this one, and section 6 deletes it.
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
- [ ] 4.8 Correct the `session_unavailable` handling at
      `InterRaterDashboard.vue:230-240` so a refused duplicate reads as "you have
      already rated this prompt", distinct from genuine unavailability.
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

## 6. Resolve #75 — all of it; nothing here reaches the allocator
Rationale in `design.md`, Decision 4. Neither `has_user_feedback` nor
`span_ids_with_feedback` has a caller anywhere in the repo, so the frozenset
cannot move inter-rater eligibility. Do 6.1 and 6.2 before the rest.

- [ ] 6.1 Decouple reviewer identity from rubric category names: move the
      `user_id` capture at `annotations_cache.py:136-137` out from under the
      `if name not in _USER_FEEDBACK_NAMES: continue` guard (line 111), so it is
      taken from any non-inter-rater annotation carrying it.
      Fails safe — it can only ever add a `user_id`, never remove one, and an
      added one can only exclude a reviewer's own session
      (`inter_rater_service.py:306-307` keeps sessions whose
      `original_user_id` is absent, so today a capture miss offers a reviewer
      their own session).
- [ ] 6.2 Confirm the decoupling changes nothing for the current pool: capture
      `original_user_id` for every span in the study pool before and after 6.1
      and diff. A non-empty diff means eligibility moved — stop and reassess
      against the capacity equation rather than proceeding.
- [ ] 6.3 Stop sending the dead `original_feedback` payload
      (`phoenix_client.py:184, 193`): confirm nothing in `frontend/src/` reads
      it, then remove it. `original_user_id` is a separate key stripped at
      line 242 and is unaffected.
- [ ] 6.4 With 6.1 and 6.3 done, `_USER_FEEDBACK_NAMES` and the score mapping in
      `get_user_feedback` (lines 111, 118-131) gate nothing. Collapse
      `get_user_feedback` to the original-user-id lookup its one caller
      (`phoenix_client.py:170`) actually needs, and delete the frozenset.
      Delete rather than refresh — refreshing re-synchronises something that
      drifts again at the next rubric change.
- [ ] 6.5 Delete the uncalled `has_user_feedback` (line 141) and
      `span_ids_with_feedback` (line 151). Both are stale and obsoleted by the
      `feedback` requirement "Inter-Rater Eligibility Without Baseline
      Feedback". If either is wanted for planned work, keep it and correct its
      name set instead — but do not leave it uncalled *and* stale.
- [ ] 6.6 Close #75, noting that the shared-declaration refactor it suggested is
      moot once there is no name set to share.

## 7. Validation
- [ ] 7.1 Full reviewer run in Chrome, Firefox and Safari: rate several items,
      detour to FAQ and About, use Back and Forward, reload mid-run, open
      history, and confirm no rated prompt is re-presented.
- [ ] 7.2 Confirm no duplicate annotations reached Phoenix and that
      `[inter-rating-N]` numbering is unbroken.
- [ ] 7.3 Confirm inter-rater eligibility and allocation are unchanged: same
      pool size, same per-reviewer quota, capacity equation still satisfied.
- [ ] 7.4 `openspec validate update-inter-rater-reviewer-ux --strict`
- [ ] 7.5 Close #67, #70, #71, #72, #73 with the verifying evidence.
