# Release inter-rater focus-group code as v0.4.0

## Why

The inter-rater allocation work is merged to `main` but unreleased and untested
against production. It needs a tag, because this is the version that will be
cited in publications if it runs the focus-group session, and because v0.3.0's
release notes now describe a superseded study design (15 reviewers, 3 ratings
per prompt) — citing v0.3.0 would misdescribe what ran.

The tag must name the code that actually produced the data, so it cannot be
created until the prod pilot has passed. That leaves a sequence of manual steps
spanning configuration, verification, seeding, tagging and provenance recording,
with ordering constraints that are easy to get wrong and expensive to get wrong
once paid reviewers are in the room.

This change exists to hold that sequence so it can be resumed from a clean
session, and to record the study-integrity requirements the code now enforces —
there is currently no `inter-rater` capability in `openspec/specs/`, so the
invariants live only in code and `docs/inter_rater.md`.

## What Changes

- Add an `inter-rater` capability spec covering the study-integrity invariants
  already implemented: the saturated allocation design, study pool purity,
  submission-time cap enforcement, and pool-scoped reviewer quota. Spec-only;
  no behaviour change.
- Track the manual release sequence in `tasks.md`: production configuration,
  deployment verification, pilot, study-pool seeding, tagging, and recording
  study provenance for the paper.

No code changes. Every task is a manual or operational step.

## Impact

- Affected specs: `inter-rater` (new capability)
- Affected code: none
- Affected operations: production configuration and deployment, Phoenix project
  `Hansard-Interrating`, the `v0.4.0` tag and GitHub release, and `CITATION.cff`

## Constraints and ordering

These are the constraints that make the sequence non-obvious. They are the
reason this is written down rather than done from memory:

1. **Tag after the pilot, before the session.** The tag is the citable artifact
   and must be the deployed, verified commit.
2. **Seeding needs a running backend.** `make seed` POSTs to `/api/ask/stream`
   on localhost, so the backend must start before a study pool exists. It does:
   the missing-manifest check runs at allocation, not startup.
3. **A short pilot pool cannot use the study settings.** Capacity must satisfy
   `pool × MAX_RATINGS = REVIEWERS × SESSIONS_PER_USER`, so `--count 5` under
   `20 × 20` is rejected. Pilot against the full pool, or set matching
   temporary values.
4. **`ATLAS_VERSION` must be bumped before seeding.** It is recorded as a
   top-level Phoenix span attribute, so it stamps the study data with the code
   version. Set after seeding, the seeded spans carry the old version.
5. **Zenodo archives only releases created after its webhook exists.** If a DOI
   is wanted for this version, confirm the integration before publishing.
