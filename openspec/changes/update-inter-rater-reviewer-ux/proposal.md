# Reviewer-Facing UX Fixes for the Inter-Rater Task

## Why

Manual and focus-group testing of the v0.4.0 inter-rater release surfaced five
reviewer-facing defects. None corrupts data — the submission gate holds — but
each degrades the conditions under which ratings are produced, and the rubric
tooltips in particular are a construct-validity risk: a reviewer who cannot read
the definition of "Corpus Fidelity" is rating against a two-word label.


| # | Finding | Capability |
|---|---------|-----------|
| [#70](https://github.com/AI-as-Infrastructure/aiinfra-atlas/issues/70) | Rubric and fault ⓘ tooltips do not appear on hover in Chrome | feedback |
| [#71](https://github.com/AI-as-Infrastructure/aiinfra-atlas/issues/71) | Citation hover card is clipped for citations at the left of the list | inter-rater |
| [#72](https://github.com/AI-as-Infrastructure/aiinfra-atlas/issues/72) | Browser Back re-presents a rated session; no way to review own ratings | inter-rater |
| [#73](https://github.com/AI-as-Infrastructure/aiinfra-atlas/issues/73) | Returning to the task via the site title reloads the whole allocation | inter-rater |
| [#67](https://github.com/AI-as-Infrastructure/aiinfra-atlas/issues/67) | Header `Inter-rate (N)` count lags up to 5 minutes behind a submission | inter-rater |

#70 is not a gap in the specs — it is a violation of one. `feedback` already
requires "Each category SHALL display the tooltip definition above as a hoverable
ⓘ icon adjacent to the label", and the implementation satisfies that only on
paper: it sets a native `title` attribute and leaves rendering to the browser.
This change adds the rendering constraint that wording was missing.

#72 carries a request as well as a defect. A reviewer asked for it directly:

> "i kind of wanted to be able to navigate back to previous sessions, because i
> wanted to see if i was being consistent"

That is the substantive part of this proposal and the reason it is a proposal
rather than four bug fixes — it adds a reviewer-facing surface with
methodological consequences. See `design.md`.

#73 and #67 are the same underlying shape as #72: inter-rater task state lives in
`setup()` locals and a 5-minute poll, and does not survive an in-app round trip.
Fixing them together avoids three overlapping patches to the same component.

## What Changes

- **Tooltip rendering** — replace the native `title` mechanism with an
  application-controlled tooltip, so the definitions render on hover in every
  supported browser and the hover target is larger than a 12px glyph. Applies to
  both the standard and inter-rater feedback forms.
- **Citation hover card** — position the card so it stays within the viewport
  and its container regardless of where its citation sits in the list.
- **Rating history** — add a read-only view of the reviewer's own completed
  ratings for the current run, and persist handled spans so a rated session is
  never re-presented as ratable. A duplicate submission that still reaches the
  gate is reported as such rather than as unavailability.
- **Task state across navigation** — retain the reviewer's allocation across an
  in-app detour to FAQ or About instead of refetching it. Persisted state used
  after a reload is accepted only after the server confirms that it belongs to
  the current allocation snapshot.
- **Header count** — refresh the count after every submission, not only on
  quota completion.

Out of scope: the allocation algorithm and the rubric itself. Ratings already
recorded are untouched. The submission gate changes in two bounded ways: it
rejects a span that is not in the current server-side pool, and it carries a
refusal *reason* so the client can distinguish a duplicate from a full prompt.
The existing duplicate and rating-cap decisions are unchanged.

**Also out of scope, deliberately:**
[#75](https://github.com/AI-as-Infrastructure/aiinfra-atlas/issues/75) — the
stale `_USER_FEEDBACK_NAMES` plumbing. An earlier draft folded it in on the
argument that it could not reach the allocator. External review showed
otherwise: recovering more `original_user_id` values shrinks the per-reviewer
pool, and `inter_rater_service.py:313` falls back from balanced to unbalanced
allocation **silently** when the capacity equation breaks. See `design.md`,
Decision 4. Nothing that can quietly alter study allocation belongs in a change
shipping near a live focus group.

**Deferred to a later cycle:**
[#74](https://github.com/AI-as-Infrastructure/aiinfra-atlas/issues/74) — a
tabular score matrix letting a reviewer cross-reference their scores across
items at a glance, requested by a second reviewer in the same testing round. It
is deliberately not in this change: it is new reviewer-facing surface too close
to a focus group, and it escalates the anchoring risk of Decision 1 enough to
need its own decision rather than inheriting one. The history view specified
here is its prerequisite, so it should be built as a reviewer-scoped read that a
matrix can later become a second view over.

## Impact

- Affected specs: `feedback` (tooltip rendering), `inter-rater` (#71, #72, #73,
  #67)
- Affected code: `frontend/src/components/InterRaterPlayback.vue`,
  `InterRaterDashboard.vue`, `InterRaterButton.vue`, `ExtendedFeedback.vue`,
  `CitationList.vue`, `frontend/src/stores/interRater.js`,
  `frontend/src/App.vue`, `backend/routers/inter_rater.py`,
  `backend/services/annotations_cache.py` (read path only),
  `backend/services/inter_rater_service.py`,
  `backend/services/inter_rater_submission_gate.py`, `backend/telemetry/api.py`
- Mostly frontend. Four backend pieces: a read endpoint returning the
  requesting reviewer's own recorded ratings, scoped server-side; a pool
  snapshot identifier returned with session allocations in study and ad-hoc
  modes; a fail-closed pool-membership check on submission, so a stale client
  allocation cannot be rated; and a refusal reason carried out of the submission
  gate. The history reader uses the existing Phoenix annotation path. No schema
  or format change is made to stored annotations, and no stored data is rewritten.
- **Sequencing**: the `inter-rater` capability spec does not exist in
  `openspec/specs/` yet — it arrives when `release-inter-rater-v0-4-0` is
  archived. Archive that change before this one.
- **Deployment**: reviewers must not be mid-run when this ships. It changes the
  rating surface, so it belongs between cohorts, not during one.
