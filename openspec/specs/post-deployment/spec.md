# post-deployment Specification

## Purpose
TBD - created by archiving change add-post-deployment-spec. Update Purpose after archive.

## Requirements

### Requirement: Tag Names The Deployed And Verified Commit
A release tag SHALL identify the exact commit that was deployed to production and
verified there. The tag SHALL NOT be created before deployment verification has
passed, and SHALL NOT be created on a commit that differs from the deployed one.

This exists because the tag is the citable artifact: published work names a
version, and a version that does not correspond to the running code misdescribes
what produced the results.

#### Scenario: Verification passes
- **GIVEN** a commit deployed to production
- **WHEN** post-deployment verification passes
- **THEN** the tag SHALL be created on that commit

#### Scenario: Further commits land before tagging
- **GIVEN** a commit deployed to production and verified
- **WHEN** additional commits land on the default branch before the tag is created
- **THEN** the tag SHALL name the deployed and verified commit, not the branch tip
- **OR** the newer tip SHALL be deployed and verified before it is tagged

#### Scenario: Verification fails
- **WHEN** post-deployment verification fails
- **THEN** no tag SHALL be created for that commit
- **AND** the release SHALL NOT be published

### Requirement: Release Artifacts Are Consistent With The Tag
When a release is published, the citation metadata, release notes, and the
repository's release list SHALL describe the tagged version and no other. Release
notes SHALL NOT be published while still marked as a draft.

#### Scenario: Release published
- **WHEN** a release is published for a tag
- **THEN** `CITATION.cff` SHALL record that version and its release date
- **AND** the release notes for that version SHALL have any draft marker removed
- **AND** the repository's release list SHALL include the version

#### Scenario: A previous version's notes describe a superseded design
- **GIVEN** an earlier release whose notes describe a design that has since changed
- **WHEN** the new release is published
- **THEN** the new notes SHALL state what changed relative to that earlier version,
  so that citing the wrong version is detectable

#### Scenario: A persistent identifier is wanted
- **GIVEN** a release for which a DOI is wanted
- **WHEN** the archival integration is not confirmed active before publication
- **THEN** the release SHALL NOT be assumed to be archived, because archival
  services may only capture releases created after their integration exists

### Requirement: Deployment Provenance Is Recorded Before Data Collection
Where a deployment produces research data, the configuration that produced it
SHALL be recorded before collection begins, because some of it changes afterwards
and cannot be reconstructed from the data.

The record SHALL identify at minimum: the tagged commit, the application version
string as reported in telemetry, the active test target including provider and
model, the vector store and embedding model, and the telemetry project the data
lands in.

#### Scenario: Data collection begins
- **WHEN** a deployment begins collecting research data
- **THEN** the provenance record SHALL already exist
- **AND** the recorded version string SHALL match what the deployment stamps onto
  its telemetry

#### Scenario: Version string set after collection starts
- **GIVEN** a version string recorded as a telemetry attribute
- **WHEN** it is changed after data collection has begun
- **THEN** the already-collected data SHALL be understood to carry the previous
  value, and the provenance record SHALL state the point at which it changed

### Requirement: Collected Data Is Exported Before Any Reset
Data collected in production SHALL be exported and backed up before any operation
that resets, re-seeds, or deletes the project holding it. Where annotations or
feedback are the only record of a result, they SHALL be treated as the source of
truth and exported first.

#### Scenario: Reset requested after collection
- **GIVEN** a telemetry project holding collected data
- **WHEN** a reset, re-seed, or project deletion is requested
- **THEN** the export and backup SHALL be completed and verified first

#### Scenario: Expected volume not reached
- **WHEN** collection ends
- **THEN** the actual quantity collected SHALL be compared against what was
  expected
- **AND** any shortfall SHALL be recorded with its reason, rather than left
  implicit in the data

### Requirement: Post-Deployment Steps Are Tracked To Completion
Post-deployment work SHALL be tracked in the change that introduced the
deployment, and that change SHALL be archived only once the post-deployment steps
are complete. Steps that are irreversible or outward-facing SHALL be distinguished
from reversible ones, so ordering mistakes are visible before they are made.

#### Scenario: Change archived
- **WHEN** a deployment's change is archived
- **THEN** its post-deployment steps SHALL be complete or explicitly recorded as
  not done, with the reason

#### Scenario: Operator resumes from a clean session
- **GIVEN** a partially completed post-deployment sequence
- **WHEN** an operator resumes it later
- **THEN** the tracked state SHALL be sufficient to identify the next step without
  re-deriving the ordering constraints
