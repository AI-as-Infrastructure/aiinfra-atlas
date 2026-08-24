# inter-rater (delta)

## ADDED Requirements

### Requirement: Saturated Allocation Design
The allocator SHALL distribute a study pool so that every prompt receives exactly
`INTER_RATER_MAX_RATINGS` ratings and every reviewer receives exactly
`INTER_RATER_SESSIONS_PER_USER` prompts, whenever
`INTER_RATER_REVIEWERS × INTER_RATER_SESSIONS_PER_USER = pool size × INTER_RATER_MAX_RATINGS`.
Reviewer queues SHALL overlap evenly across the cohort rather than partitioning
it, so that rater severity is not confounded with any subset of prompts.

#### Scenario: Balanced assignment saturates the pool
- **GIVEN** a study pool whose size satisfies the capacity equation
- **WHEN** queues are derived for every reviewer slot
- **THEN** each prompt SHALL appear in exactly `INTER_RATER_MAX_RATINGS` queues
- **AND** each reviewer SHALL receive exactly `INTER_RATER_SESSIONS_PER_USER` prompts

#### Scenario: No two reviewers receive identical queues
- **GIVEN** a study pool whose size satisfies the capacity equation
- **WHEN** queues are derived for every reviewer slot
- **THEN** no two reviewers SHALL be assigned the same set of prompts
- **AND** the mean number of prompts shared by a pair of reviewers SHALL approach
  `pool × cap × (cap - 1) / (reviewers × (reviewers - 1))`

#### Scenario: Pool that breaks the capacity equation is rejected
- **GIVEN** a configured study pool
- **WHEN** the eligible prompt count no longer satisfies the capacity equation
- **THEN** allocation SHALL fail with the actual and required counts
- **AND** allocation SHALL NOT fall back to unbalanced ranking

### Requirement: Study Pool Purity
When a study pool manifest is configured, allocation SHALL be restricted to the
prompts it names, and the pool SHALL be identical for every reviewer.

#### Scenario: Organic sessions are excluded from a study
- **GIVEN** a study pool manifest naming a set of seeded prompts
- **WHEN** the Phoenix project also contains sessions from organic traffic
- **THEN** only prompts named in the manifest SHALL be offered for rating

#### Scenario: Configured but unreadable manifest is refused
- **GIVEN** `INTER_RATER_POOL_MANIFEST` is set
- **WHEN** no readable manifest exists at that path
- **THEN** allocation SHALL fail
- **AND** allocation SHALL NOT treat the whole project as an ad-hoc pool

#### Scenario: Manifest from another project is refused
- **GIVEN** a manifest recording a project name
- **WHEN** that name differs from the active Phoenix project
- **THEN** loading the manifest SHALL fail rather than yield an empty pool

### Requirement: Submission-Time Rating Cap
A rating SHALL NOT be recorded for a prompt that already holds
`INTER_RATER_MAX_RATINGS` ratings, or that the submitting reviewer has already
rated. The check and the write SHALL be serialised per prompt across all workers,
and SHALL fail closed.

#### Scenario: Concurrent submissions cannot exceed the cap
- **GIVEN** a prompt one rating below `INTER_RATER_MAX_RATINGS`
- **WHEN** two reviewers submit ratings for it at the same time
- **THEN** exactly one SHALL be recorded
- **AND** the other SHALL be told the session is no longer available

#### Scenario: Duplicate rating by the same reviewer is refused
- **GIVEN** a reviewer who has already rated a prompt
- **WHEN** they submit a rating for it again
- **THEN** the submission SHALL be refused rather than recorded twice

#### Scenario: Verification failure rejects rather than writes
- **GIVEN** the current rating count for a prompt cannot be verified
- **WHEN** a reviewer submits a rating
- **THEN** the rating SHALL NOT be written
- **AND** the reviewer SHALL be asked to retry

### Requirement: Pool-Scoped Reviewer Quota
Reviewer progress SHALL be counted against the active study pool, not against
every rating the reviewer has submitted in the Phoenix project. Allocation,
statistics and the sessions API SHALL report the same count.

#### Scenario: Ratings from a replaced pool do not consume quota
- **GIVEN** a reviewer who completed their quota against an earlier study pool
- **WHEN** a new pool is seeded in the same Phoenix project
- **THEN** their remaining quota SHALL be measured against the new pool only

#### Scenario: Reported progress matches allocation
- **GIVEN** a reviewer partway through their quota
- **WHEN** the sessions API and the statistics endpoint report completed sessions
- **THEN** both SHALL report the same count as allocation used
