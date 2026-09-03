# Reviewer-Facing UX Fixes for the Inter-Rater Task

## Why

Manual and focus-group testing of the v0.4.0 inter-rater release surfaced five
reviewer-facing defects. None corrupts data — the submission gate holds — but
each degrades the conditions under which ratings are produced, and the rubric
tooltips in particular are a construct-validity risk: a reviewer who cannot read
the definition of "Corpus Fidelity" is rating against a two-word label.

A sixth item, #75, came out of tracing those five rather than from testing. It
is included because it is adjacent to the same code and demonstrably cannot
reach the allocator — not because it was reported.

| # | Finding | Capability |
|---|---------|-----------|
| [#70](https://github.com/AI-as-Infrastructure/aiinfra-atlas/issues/70) | Rubric and fault ⓘ tooltips do not appear on hover in Chrome | feedback |
| [#71](https://github.com/AI-as-Infrastructure/aiinfra-atlas/issues/71) | Citation hover card is clipped for citations at the left of the list | inter-rater |
| [#72](https://github.com/AI-as-Infrastructure/aiinfra-atlas/issues/72) | Browser Back re-presents a rated session; no way to review own ratings | inter-rater |
| [#73](https://github.com/AI-as-Infrastructure/aiinfra-atlas/issues/73) | Returning to the task via the site title reloads the whole allocation | inter-rater |
| [#67](https://github.com/AI-as-Infrastructure/aiinfra-atlas/issues/67) | Header `Inter-rate (N)` count lags up to 5 minutes behind a submission | inter-rater |
| [#75](https://github.com/AI-as-Infrastructure/aiinfra-atlas/issues/75) | `_USER_FEEDBACK_NAMES` stale since the v0.4.0 rubric; reviewer identity depends on it | — |

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
  in-app detour to FAQ or About instead of refetching it.
- **Header count** — refresh the count after every submission, not only on
  quota completion.
- **Stale baseline-feedback plumbing**
  ([#75](https://github.com/AI-as-Infrastructure/aiinfra-atlas/issues/75)) —
  decouple reviewer identity from rubric category names, and delete the
  `_USER_FEEDBACK_NAMES` frozenset and the two uncalled functions it gates.
  Included because none of it can reach the allocator: see `design.md`,
  Decision 4. Task 6.2 verifies that empirically rather than on argument.

Out of scope: the allocation algorithm, the submission gate, and the rubric
itself. Ratings already recorded are untouched.

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
  #67). #75 is internal cleanup behind existing requirements and adds none.
- Affected code: `frontend/src/components/InterRaterPlayback.vue`,
  `InterRaterDashboard.vue`, `InterRaterButton.vue`, `ExtendedFeedback.vue`,
  `CitationList.vue`, `frontend/src/stores/interRater.js`,
  `frontend/src/App.vue`, `backend/routers/inter_rater.py`,
  `backend/services/annotations_cache.py`, `backend/services/phoenix_client.py`
- Mostly frontend. Two backend pieces: a read endpoint returning the requesting
  reviewer's own recorded ratings, scoped server-side by `rater_id`, so history
  survives a closed tab and "own ratings only" is enforced rather than filtered
  client-side; and the #75 cleanup in `annotations_cache.py` and
  `phoenix_client.py`. Both read through the existing Phoenix annotation path —
  no schema or annotation-format change, and no stored data is rewritten.
- **Sequencing**: the `inter-rater` capability spec does not exist in
  `openspec/specs/` yet — it arrives when `release-inter-rater-v0-4-0` is
  archived. Archive that change before this one.
- **Deployment**: reviewers must not be mid-run when this ships. It changes the
  rating surface, so it belongs between cohorts, not during one.
