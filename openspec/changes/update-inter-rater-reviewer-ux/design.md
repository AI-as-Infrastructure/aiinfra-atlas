# Design

## Context

Five defects from v0.4.0 focus-group testing. Four are contained frontend fixes
whose design is settled in the spec deltas. One — letting a reviewer look back at
their own completed ratings (#72) — is a research-design decision before it is an
engineering one, and is the subject of this document.

## Decision 1: Does reviewing your own prior ratings compromise the study?

The reviewer's stated motive was self-consistency: "i wanted to see if i was
being consistent". This cuts both ways.

**Against.** Inter-rater reliability statistics assume each rating is an
independent judgement of the item in front of the rater. A reviewer who consults
their earlier scores mid-run may anchor on them — rating item 12 to match item 3
rather than rating item 12. That deflates within-rater variance in a way that
looks like consistency but is partly an artefact of the interface, and it is
invisible in the recorded data.

**For.** Rater drift over a 20-item run is a real and well-documented threat.
A reviewer who notices they have shifted their interpretation of "Uncertainty"
halfway through, and who cannot go back, will either carry the drift or abandon
the run. Blocking the reviewer entirely does not make them consistent; it makes
their inconsistency unobservable.

**Decision.** Provide the view, constrained:

- **Own ratings only.** A reviewer never sees another reviewer's scores. This is
  not negotiable — cross-rater visibility would destroy independence outright.
- **Read-only.** No editing, no re-submission, no path from the history view back
  into a rating form. The recorded rating is what was recorded.
- **Scoped to the current run.** History covers the reviewer's own completed
  items in this allocation, not a permanent cross-cohort archive.

The residual anchoring risk is accepted. It is smaller than the drift risk it
mitigates, the alternative (reviewers silently guessing at their own past
behaviour) is not obviously better, and the constraint that matters most —
never seeing another rater — is preserved.

**Confirmed by the study lead (2026-09-03): available during the run.** The
alternative — deferring history to quota completion — removes the anchoring risk
entirely but also removes most of the benefit, since drift can no longer be
corrected once the run is over. Availability during the run is what makes the
feature answer the reviewer's actual question ("am I being consistent?") at the
point where the answer can still change how they rate.

The three constraints above are the whole of the mitigation: own ratings only,
read-only, current run only. They are requirements, not defaults — the
"Reviewer Rating History" requirement states each as a `SHALL`, and each has a
scenario. Loosening any one of them reopens Decision 1 and needs a new proposal.

## Decision 2: KeepAlive vs. store-backed state

#72, #73 and #67 all reduce to the same fault: inter-rater task state lives in
`InterRaterDashboard.vue`'s `setup()` closure — `handledSpanIds` is a bare `Set`
— and is destroyed by any remount. Two ways out.

**`<KeepAlive>` around the route.** Smallest change, no state migration, fixes
the FAQ/About round trip completely. But it only covers in-app navigation: a
browser reload or a Back that leaves the SPA still tears everything down, so it
does not on its own close #72.

**Move state into the Pinia store, persisted to session storage.** Survives
remount *and* reload, and gives `InterRaterButton` a count it can trust. More
work, and session storage brings its own failure mode when it is unavailable.

**Decision.** Store-backed, with `<KeepAlive>` as a cheap addition on top.
`<KeepAlive>` then avoids paying the rehydration cost on the common path.

**But client storage is the wrong home for the rating history**, which is a
distinction worth stating because the first draft of this design got it wrong.
Session storage dies with the tab. A reviewer who rates ten items today and ten
tomorrow — an entirely ordinary way to work through a twenty-item run — would
open the history on day two and find it empty, at exactly the moment
cross-referencing matters most.

So the two kinds of state are split by lifetime:

- **Run position** — where the reviewer is in the allocation. Client-side,
  session storage, disposable. Losing it costs a refetch.
- **Rating history** — what the reviewer recorded. Server-side, read back from
  the existing inter-rater annotations, which already carry `rater_id`,
  per-criterion scores and explanations keyed by span
  (`annotations_cache.py:169-204`). Losing it is not acceptable, so it is not
  stored anywhere that can be lost.

This costs one read endpoint, scoped server-side to the requesting `rater_id`.
That scoping is also the enforcement point for "own ratings only" — a
client-side filter would be a suggestion rather than a guarantee.

Per the project's fail-fast stance, a failed history read is reported as such
rather than rendered as an empty history that reads as authoritative.

## Decision 3: Tooltip mechanism

Native `title` is being dropped rather than debugged. Its display timing and
placement are entirely browser-controlled, so the existing `feedback` requirement
cannot actually be verified against it — which is how a broken implementation
passed review in the first place. A CSS/`data-`attribute tooltip is testable,
themeable to match the form, and lets the hover target grow past 12px.

No tooltip library is introduced. The project is a research prototype and this is
a `::after` rule.

## Decision 4: Which of #75's housekeeping comes forward

#75 records that `_USER_FEEDBACK_NAMES` went stale when the v0.4.0 rubric
landed. Nothing there is broken today, so the question is only which parts are
cheap enough to fold into this change rather than schedule separately.

The test applied was **whether the item can move inter-rater eligibility**.
Eligibility feeds the allocator, and the v0.4.0 allocator holds a strict capacity
equation — `reviewers × sessions_per_user = pool × max_ratings` — that fails
closed, so anything that can shift which spans qualify is not worth taking on
the way past.

**On inspection, nothing in #75 can move eligibility, so all of it comes
forward.** The first draft of this decision split the work on the assumption
that `_USER_FEEDBACK_NAMES` gates the allocator through `has_user_feedback` and
`span_ids_with_feedback`. It does not: neither function has a caller anywhere in
the repository — not in `backend/`, `tests/`, `analysis/`, `utils/` or
`create/`. They are dead code, and the `feedback` requirement "Inter-Rater
Eligibility Without Baseline Feedback" is why. Eligibility deliberately stopped
depending on baseline feedback; these two were left behind.

The frozenset therefore has exactly one live path — `get_user_feedback`, called
once at `phoenix_client.py:170` — producing two things:

- `original_feedback`, sent to the client at line 193 and read by nothing in
  `frontend/src/`.
- `original_user_id`, backend-only, stripped at line 242, used for own-session
  filtering at `inter_rater_service.py:306-307`.

Neither reaches the allocator.

**What that implies for the fix.** Refreshing the frozenset is the wrong move,
because tasks 6.1 and 6.4 between them make it dead:

- 6.1 lifts the `user_id` capture out from under the name-match guard, so
  identity no longer depends on it.
- 6.4 stops sending `original_feedback`, so the score mapping it gates has no
  consumer.

After both, `_USER_FEEDBACK_NAMES` and the score mapping in `get_user_feedback`
gate nothing, and the only thing that caller still needs is the original user's
id. So the work is deletion, not refreshing: collapse `get_user_feedback` to the
id lookup its one caller actually uses, and remove the frozenset along with the
two uncalled functions.

This is a smaller diff than the refresh #75 originally proposed, and it removes
the desynchronisation permanently rather than re-synchronising something that
will drift again at the next rubric change. It also makes #75's remaining
suggestion — deriving the name set from a declaration shared with the writer in
`feedback.py` — unnecessary, since there is no longer a name set to share.

**The one judgement call** is deleting `has_user_feedback` and
`span_ids_with_feedback` rather than leaving them. They are uncalled, stale, and
obsoleted by a requirement, and the project's stated preference is a lean
codebase without unnecessary machinery. Deleting them is consistent with that.
If they are wanted for planned work, leave them and fix their name set instead —
but they should not be left uncalled *and* stale.

## Risks

- **Anchoring**, per Decision 1. Accepted and documented; revisit if
  within-rater variance drops sharply against the v0.4.0 cohort.
- **Mid-run deployment** would change the rating surface underneath active
  reviewers. Ship between cohorts.
- **Hover-card repositioning** touches shared citation rendering; the standard
  chat view uses the same pattern and must be checked alongside the inter-rater
  view.
- **Eligibility drift** from the Decision 4 housekeeping. Argued to be nil and
  checked empirically by task 6.2, but it is the one risk in this change that
  reaches the allocator rather than the interface. If the 6.2 diff is non-empty,
  drop tasks 6.1-6.4 back into #75 rather than reasoning past it — none of them
  is worth delaying the UX fixes for.
