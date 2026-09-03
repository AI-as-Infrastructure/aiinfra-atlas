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
`InterRaterDashboard.vue`'s `setup()` closure — including a bare
`handledSpanIds` set that currently mixes successful ratings with capacity
refusals — and is destroyed by any remount. Two ways out.

**`<KeepAlive>` around the route.** Smallest change, no state migration, fixes
the FAQ/About round trip completely. But it only covers in-app navigation: a
browser reload or a Back that leaves the SPA still tears everything down, so it
does not on its own close #72.

**Move state into the Pinia store, persisted to session storage.** Survives
remount *and* reload, and gives `InterRaterButton` a count it can trust. More
work, and session storage brings its own failure mode when it is unavailable.

**Decision.** Store-backed, with `<KeepAlive>` as a cheap addition on top.
`<KeepAlive>` then avoids paying the rehydration cost on the common path.

Persisted state needs an identity, but the existing **cohort fingerprint is not
that identity**. The cohort fingerprint is derived from manifest `qa_ids`, is
`None` in ad-hoc mode, and is deliberately stable when the Phoenix span set
changes. Those are correct properties for keeping reviewer slots stable and the
wrong properties for deciding whether a saved client allocation is still real.

The sessions API will therefore return a separate server-issued
`allocation_snapshot_id`, derived from the exact shared pool snapshot before
per-reviewer completion and capacity filtering. It hashes the pool's authoritative
`span_id` and `qa_id` pairs, exists in both manifest-backed and ad-hoc modes, and
changes when the actual pool spans change even if the manifest `qa_ids` do not.
It is not used for cohort assignment.

The two navigation paths then behave differently on purpose:

- **In-app detour** — `<KeepAlive>` and the live Pinia store resume immediately;
  no allocation request is made.
- **Reload or remount** — request the current sessions response, compare its
  `allocation_snapshot_id` with session storage, and restore only the saved
  position and snapshot-scoped unavailable set when they match. On mismatch,
  use the fresh server allocation and replace those snapshot-scoped values.

The current `handledSpanIds` cannot be persisted as one unit. It contains two
facts with different meanings and lifetimes:

- **Recently rated spans** — added only after a successful submission or a
  duplicate refusal that confirms this reviewer already rated the prompt. This
  is a reviewer-scoped propagation-race mask and survives a snapshot change.
- **Unavailable spans** — prompts refused because they reached capacity or are
  outside the current pool. These are not ratings by this reviewer. They are
  snapshot-scoped and are discarded when the snapshot changes.

The recently-rated set is temporary rather than a permanent client ledger. The
history read provides the reconciliation point: retain a local entry while the
server has not yet exposed the corresponding recorded rating, and prune it only
after an authoritative history response confirms the rating. Do not bound the
set by arbitrary eviction, which could re-open the propagation race.

The submission gate is the second line of defence. It validates `span_id`
against the current server-side pool snapshot, without trusting a client-supplied
`qa_id` or snapshot identifier, and fails closed if membership cannot be
verified. This is a bounded change to submission acceptance, not a change to how
the allocator constructs reviewer queues.

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

## Decision 4: #75 is out of scope — it does reach the allocator

This decision was wrong twice. Recording both errors, because the second one is
the kind that ships.

**First draft:** kept #75 out on the grounds that `_USER_FEEDBACK_NAMES` gates
`has_user_feedback` and `span_ids_with_feedback`, which feed eligibility. False
— neither function has a caller anywhere in the repository.

**Second draft:** took all of #75 on the grounds that, with those two functions
dead, nothing in #75 could reach the allocator, and that the allocator fails
closed anyway. Also false, and this is the one that mattered. External review
caught it.

**What the allocator actually does** (`inter_rater_service.py:302-313`):

```python
all_sessions = [s for s in pool_sessions
                if not s.get("original_user_id")
                or s.get("original_user_id") != user_id]

balanced_design = (self.reviewer_count * self.sessions_per_user
                   == len(all_sessions) * self.max_ratings)
assigned_sessions = None
if balanced_design:
    ...
    assigned_sessions = self._balanced_assignment(all_sessions, reviewer_slot)
candidate_sessions = assigned_sessions if assigned_sessions is not None else all_sessions
```

`all_sessions` is the pool minus the sessions this reviewer authored, so its
length is a direct function of how many `original_user_id` values were
recovered. `balanced_design` is computed from that length. And when it is False
the code does not raise — it falls through to `all_sessions` and allocates
**unbalanced, silently**.

So the #75 change that recovers `user_id` from annotations currently missing it
can shrink `all_sessions`, break the capacity equation, and silently drop the
study from a balanced design to a ranked one. Rater severity would then be
confounded with the subset of prompts each reviewer saw — the exact failure the
"Saturated Allocation Design" requirement exists to prevent, arriving with no
error and no log line.

My "fails safe" argument was that recovering an id can only ever *exclude* a
session. That is true and it is precisely the mechanism of the harm: excluding
a session is what changes the count.

**Correction to the above, from a later pass.** The fail-closed behaviour *is*
built — `_validate_study_capacity` (`inter_rater_service.py:229-275`) raises in
study mode when `reviewers x sessions_per_user != len(sessions) x max_ratings`,
with the actual and required counts, exactly as the requirement specifies. My
claim that it was unimplemented was wrong.

What is actually true is narrower and more specific, and it still condemns #75.
The validation runs on `sessions` — the **shared pool**, after manifest
restriction and *before* author exclusion. The `balanced_design` test at line
310 runs on `all_sessions` — the **per-reviewer** list, after author exclusion.
The two are equal only while no reviewer authored a pool session.

So:

- In a seeded study, seeded sessions carry no `original_user_id`, author
  exclusion removes nothing, `all_sessions == sessions`, and the validation
  covers the balanced-design test. Safe.
- The moment a reviewer is recognised as the author of a pool session,
  `len(all_sessions) < len(sessions)` for that reviewer alone. Validation has
  already passed on the shared pool, and the per-reviewer fallback at line 313
  then fires silently, for that reviewer only.

Recovering more `original_user_id` values is precisely what moves a study from
the first case into the second. #75 does not defeat a missing guard; it steps
around an existing one, per reviewer, downstream of where it runs.

**Decision.** #75 comes out of this change entirely. Not deferred within it, not
gated behind a diff check — removed. Two reasons:

1. It touches allocation, and this repository is weeks from a live focus group
   followed by archiving. Nothing that can silently alter study allocation
   should move before then.
2. The remaining work is interface, read-path and bounded submission-validation
   work; none changes how reviewer queues are constructed. Keeping an
   allocation-construction change alongside it means the whole change inherits
   a risk profile it otherwise does not have.

`_USER_FEEDBACK_NAMES` stays stale. That is the correct outcome: it is
unreachable in any live path, and the cost of touching it right now exceeds the
cost of leaving it. #75 records the analysis for whoever picks it up after the
archive, including the finding that the fix is deletion rather than refreshing.

**Prerequisite for anyone who does pick it up:** extend the existing fail-closed
validation to the per-reviewer pool *after* author exclusion, or otherwise make
a mismatch at `inter_rater_service.py:313` raise instead of falling through to
ranked allocation. The shared-pool check at lines 229-275 is not sufficient for
that case. Until the downstream path fails closed, any change that recovers or
alters `original_user_id` values is unsafe.

## Risks

- **Anchoring**, per Decision 1. Accepted and documented; revisit if
  within-rater variance drops sharply against the v0.4.0 cohort.
- **Mid-run deployment** would change the rating surface underneath active
  reviewers. Ship between cohorts.
- **Hover-card repositioning** touches shared citation rendering; the standard
  chat view uses the same pattern and must be checked alongside the inter-rater
  view.
- **Allocation construction** is deliberately untouched, per Decision 4. This
  change does add submission-time validation against the pool already constructed
  by the server; it must not add, remove, rank or reassign pool members. If
  implementation finds itself changing those allocation rules, stop — that is
  out of scope and unsafe while `inter_rater_service.py:313` falls back silently.
- **Stale allocation after a reseed**, if persisted run state is keyed by
  reviewer alone or by the cohort fingerprint. Tasks 3.2 and 3.2a address both
  halves with a distinct allocation snapshot identifier and a server-side
  membership check.
- **Conflating ratings with unavailability.** The current `handledSpanIds` set
  contains both successful ratings and capacity refusals. Persisting it whole
  would suppress prompts the reviewer never rated after a snapshot change;
  discarding it whole would reopen the propagation race. Task 3.2b splits it
  into a reviewer-scoped recently-rated mask and snapshot-scoped unavailable
  state. The former is pruned only after the server history confirms the rating.
- **Ad-hoc state invalidation from organic traffic.** Accepted deliberately.
  Ad-hoc mode has no manifest-backed run boundary and defines its current pool
  from the bounded live Phoenix query, so a changed query result is a changed
  allocation snapshot. Retaining an older snapshot would preserve sessions the
  server no longer recognises as current and would only defer the failure to the
  submission gate. Study mode remains stable because its manifest defines the
  run and capacity validation fails closed.
- **Cross-rater disclosure in history**, because fault tags, Additional Comments
  and per-scale comment annotations carry no `rater_id` and can only be joined
  to their author by `[inter-rating-N]`. Task 3.4a requires every such annotation
  type to be tested against malformed and colliding group numbers, omitting
  rather than guessing.
