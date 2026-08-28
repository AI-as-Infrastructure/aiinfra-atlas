# Change: Add a post-deployment capability spec

## Why

Post-deployment work — tagging, citation metadata, release publication, recording
provenance, exporting collected data, archiving the change — is currently
re-derived per release. It exists only inside
`openspec/changes/release-inter-rater-v0-4-0/tasks.md`, which is release-specific
and disappears into `changes/archive/` once that release is done. The next release
starts from nothing.

The ordering constraints are the part worth keeping. They are not obvious, and
they are expensive to get wrong:

- The tag must name the deployed, verified commit. Commits landing on the default
  branch between deployment and tagging silently break that, and the mistake is
  only visible later, in a citation that describes code which never ran.
- A version string recorded as a telemetry attribute stamps collected data. Set it
  after collection starts and the data carries the old version permanently.
- Archival services may only capture releases created after their integration
  exists, so a DOI cannot be assumed retrospectively.
- Annotations are often the only record of a result, so any reset must come after
  the export, never before.

Capturing these as requirements makes them reviewable, and gives future releases a
defined sequence instead of a remembered one.

## What Changes

- Add a `post-deployment` capability spec with requirements covering: the tag
  naming the deployed and verified commit; release artifacts being consistent with
  the tag; provenance recorded before data collection begins; collected data
  exported before any reset; and post-deployment steps tracked to completion
  before a change is archived.
- Spec-only. No code changes, and no change to how any release is currently
  executed — the requirements describe the practice the v0.4.0 release sequence
  already follows, generalised so it is not re-derived next time.

## Impact

- Affected specs: `post-deployment` (new capability)
- Affected code: none
- Related: `release-inter-rater-v0-4-0` is the first release to follow this
  sequence; its §5–7 are the concrete instance of these requirements

## Out of scope

- The deployment itself. This capability begins once a deployment is live, and
  says nothing about how it got there — that is `cloudflare-deployment`.
- Release *content* decisions: what goes in a release, versioning policy, and
  when to cut one. This covers only what must be true once one is being made.
