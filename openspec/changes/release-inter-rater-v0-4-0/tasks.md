# Tasks

All steps are manual. Order matters — see the constraints in `proposal.md`.
Everything up to task 5.1 is reversible; from 5.1 onward you are publishing a
citable artifact.

## Verified 2026-08-28

Ticked above from direct evidence, not inspection:

- Config and Redis confirmed by `utils/scripts/inter_rater_preflight.py` run on
  the prod server: 100-prompt manifest, `20 x 20 = 100 x 4` balanced, 100 of 100
  spans indexed, cohort slots readable from Redis.
- Two reviewers each offered 20 prompts with non-identical queues (overlap 4,
  design predicts ~3.2). A shared *first* prompt is expected: the lowest-sorted
  span goes to `max_ratings` slots and leads each of their queues.
- Both reviewers' ratings confirmed in the Phoenix export as
  `[inter-rating-1]` / `[inter-rating-2]` on the original span, carrying all six
  scales, per-scale rationales, faults and fault rationale. Rationales appear
  only against extreme scores, as the form requires.
- `atlas_version = "Hansard 0.4.0"` on all 100 seeded spans.
- Anonymisation: the whole export contains no email addresses and exactly two
  `anon_` identifiers.
- `PHOENIX_PROJECT_BACKUPS` includes `Hansard-Interrating`; nightly export runs
  01:20, USB copy 02:30.

Still open in sections 2-3, for the manual tester: **Task 2.4** (`make seed-dry`),
**Task 3.5** (per-prompt cap under real use) and **Task 3.6** (double submission
refused). **Task 2.1** stays open pending the full rebuild before the focus group.

Two reviewer cohort slots are already spent by pilot logins. Section 4's re-seed
clears them — new `qa_ids` give a new pool fingerprint and a fresh cohort of 20.

Post-deployment sequence for section 5 now lives in
`openspec/specs/post-deployment/spec.md` (`add-post-deployment-spec`, archived
2026-08-28).

## 1. Production configuration

- [x] **Task 1.1**: Confirm `config/.env.production` **on the prod server** has
      the values below. The local dev-machine copies of `.env.production`,
      `.env.staging` and `.env.development` were updated on 2026-08-27; the
      server's copy is separate and must be edited there:
      `INTER_RATER_ENABLED=true`, `INTER_RATER_PROJECT=Hansard-Interrating`,
      `PHOENIX_PROJECT_NAME=Hansard-Interrating`,
      `PHOENIX_PROJECT_BACKUPS=Hansard-Prod,Hansard-Interrating`,
      `INTER_RATER_MAX_RATINGS=4`, `INTER_RATER_REVIEWERS=20`,
      `INTER_RATER_SESSIONS_PER_USER=20`, `INTER_RATER_DEFAULT_UI=true`,
      `INTER_RATER_POOL_MANIFEST=data/seed_pool.json`
- [x] **Task 1.2**: Set `ATLAS_VERSION="Hansard 0.4.0"` in
      `config/.env.production` (and staging). Must happen before seeding — it is
      written to every Phoenix span, so it stamps the study data with the code
      version
- [x] **Task 1.3**: Confirm `REDIS_URL` is set and Redis is reachable. The
      submission gate and cohort registry both require it and fail closed
      without it
- [x] **Task 1.4**: Confirm `AUTH_METHOD=cloudflare` (or `cognito`) — inter-rating
      returns an empty session list under `AUTH_METHOD=none`

## 2. Deploy and verify startup

- [ ] **Task 2.1**: `git pull` on the prod server, then run the full deploy
      (`make cf` — prod runs behind the Cloudflare tunnel, `AUTH_METHOD=cloudflare`).
      A frontend rebuild *is* required: `INTER_RATER_DEFAULT_UI` is served at
      runtime, but `InterRaterPlayback.vue`, `InterRaterDashboard.vue` and
      `ExtendedFeedback.vue` all changed since v0.3.0, so a bare backend restart
      would leave reviewers on the old rubric UI
- [ ] **Task 2.2**: Confirm the backend starts. It should, with no study pool yet
      present — the missing-manifest check runs at allocation, not startup
- [ ] **Task 2.3**: Load `/inter-rater` as an authenticated user and confirm it
      reports an error about the study pool rather than showing an empty queue.
      An empty queue here means the pool guard is not active
- [ ] **Task 2.4**: `make seed-dry` — confirm the sizing check and that
      `INTER_RATER_PROJECT` matches `PHOENIX_PROJECT_NAME`

## 3. Pilot

Pick one approach. The first needs no settings churn and is preferred.

- [x] **Task 3.1a**: *Full-pool pilot.* `make seed` (all 100 questions). Confirm
      `data/seed_pool.json` is written with `count: 100` and
      `project: Hansard-Interrating`
- [ ] **Task 3.1b**: *Or short pilot.* Temporarily set `INTER_RATER_MAX_RATINGS=4`,
      `INTER_RATER_REVIEWERS=4`, `INTER_RATER_SESSIONS_PER_USER=5`, restart, then
      `make seed SEED_ARGS="--count 5"`. Restore study values afterwards
- [x] **Task 3.2**: Log in as two distinct reviewers and confirm each is offered a
      queue, and that the two queues are not identical
- [x] **Task 3.3**: Submit a full rating from each account. Confirm all six scales,
      the per-scale rationales, faults and fault rationale are all captured
- [x] **Task 3.4**: In Phoenix, confirm annotations land on the original span
      under `Hansard-Interrating` with `[inter-rating-N]` prefixes, and that
      `atlas_version` on the spans reads `Hansard 0.4.0`
- [ ] **Task 3.5**: Confirm no prompt exceeds `INTER_RATER_MAX_RATINGS` ratings.
      `make rater-load` now covers the coordination for this — 400 submissions
      racing on real Redis with 8 independent worker views — but it stubs
      Phoenix, so it proves the gate never *decides* to overfill, not that the
      write path agrees. This remains the end-to-end check
- [ ] **Task 3.5a**: `make rater-load` on the server. Expect 5 passed. Re-run
      after any change to the submission gate or the pool snapshot
- [ ] **Task 3.6**: Rate the same prompt twice from one account and confirm the
      second attempt is refused as **already rated**, distinct from a prompt
      someone else filled, and is not written twice
- [ ] **Task 3.6a**: With a second reviewer, rate a prompt the first reviewer
      already rated. This is the only way to reach the multi-rater paths — a
      single tester cannot, because the allocator will not re-offer a rated
      prompt. Then `make rater-check` and confirm attribution stays clean:
      every group resolving to exactly one rater, zero collisions
- [ ] **Task 3.6b**: Reviewer-facing checks from `update-inter-rater-reviewer-ux`
      §6 — tooltips visible on hover in Chrome, Firefox and Safari; citation
      cards not clipped; Back, reload and an FAQ detour do not re-present a
      rated prompt; rating history opens mid-run and shows only own ratings;
      header count agrees with the task view after a submission
- [x] **Task 3.7**: `make backup-prod` and confirm `Hansard-Interrating` appears
      in the backup output
- [x] **Task 3.8**: Export or note the pilot annotations, then confirm the
      rubric fields survive export in a form usable for IRR analysis

## 4. Seed the study pool

- [ ] **Task 4.1**: `make seed-reset` — deletes the Phoenix project and the study
      pool manifest. Verify the project name it prints before confirming
- [ ] **Task 4.2**: `make seed` (all 100 questions)
- [ ] **Task 4.3**: Confirm `data/seed_pool.json` has `count: 100`, and back it
      up alongside the Phoenix export. It defines the pool for reproducibility
      and is gitignored
- [ ] **Task 4.4**: Log in as one reviewer and confirm a 20-prompt queue is
      offered with no errors
- [ ] **Task 4.4a**: `make rater-check`. The pre-flight must report the design
      saturated — the capacity equation is exact, and a pool that misses it now
      blocks submissions as well as allocation. The annotation check must report
      every name recognised. Do this before reviewers arrive, not after
- [ ] **Task 4.5**: Do not seed again after this point. Re-seeding changes the
      cohort fingerprint and reassigns every reviewer slot

## 5. Tag and release

- [x] **Task 5.1**: Push `main` to origin — done, `origin/main` == `main` at `7c0bcb5`
- [ ] **Task 5.2**: If a DOI is wanted, confirm the GitHub–Zenodo integration is
      active *before* publishing. Zenodo only archives releases created after its
      webhook exists; v0.3.0 has no recorded DOI, so verify rather than assume
- [ ] **Task 5.3**: Add `version: 0.4.0` and `date-released:` to `CITATION.cff`,
      plus ORCIDs for both authors, and confirm the author list is complete
- [ ] **Task 5.4**: Tag `v0.4.0` on the exact commit deployed to prod and verified
      in the pilot. Candidate as of 2026-08-27: **`f12b322`** (tip of `main`,
      pushed). Prod was last deployed at `93b582d`; `08ab229` and `f12b322` on top
      of it are docs-only. Pull on prod before testing so the verified tree and the
      tagged commit are the same, then tag the SHA that `git log --oneline -1`
      reports on the server. If further commits land during testing, the candidate
      moves — tag what was actually deployed and verified, not the branch tip:

      ```bash
      git tag -a v0.4.0 <verified-sha> -m "v0.4.0 - inter-rater study integrity"
      git push origin v0.4.0
      ```
- [ ] **Task 5.5**: Publish the GitHub release using `docs/releases/v0.4.0.md`,
      removing its DRAFT banner
- [ ] **Task 5.6**: Add v0.4.0 to the "Major Releases" list in `ReadMe.md`, with
      its DOI once Zenodo has minted one

## 6. Record study provenance

Needed for the paper's methods section and for replication. Record before
reviewers begin, because some of it changes afterwards.

- [ ] **Task 6.1**: Record the `v0.4.0` commit SHA
- [ ] **Task 6.2**: Record the active test target: LLM provider, model name,
      temperature (`TEST_TARGET` and `backend/targets/<target>.txt`)
- [ ] **Task 6.3**: Record the vector store version and embedding model
- [ ] **Task 6.4**: Record the Phoenix project name and the study pool manifest
      (`count`, `created`, and the qa_id list)
- [ ] **Task 6.5**: Record the study design actually configured: pool size,
      `MAX_RATINGS`, `REVIEWERS`, `SESSIONS_PER_USER`, and the resulting ratings
      per prompt
- [ ] **Task 6.6**: Record the rubric version — the six scales as shipped, noting
      that superseded fields remain on the model for older data

## 7. After the session

- [ ] **Task 7.1**: Export and back up the Phoenix project immediately, before
      any reset. Annotations are the only source of truth for ratings
- [ ] **Task 7.2**: Confirm every prompt received the expected number of ratings,
      and record any that did not along with the reason. `make rater-check`
      reports rated spans and per-span rating counts; the export is the record
- [ ] **Task 7.2a**: Confirm `make rater-check` still exits clean on the final
      data — zero groups with no rater identity, zero with colliding
      identities. A collision would mean some rationales cannot be attributed,
      which matters for the IRR analysis and is easier to find now than later
- [ ] **Task 7.3**: Archive this change (`openspec archive release-inter-rater-v0-4-0`)
- [ ] **Task 7.4**: Archive `update-inter-rater-reviewer-ux` once its §6
      validation tasks are ticked. It must archive *after* this one, since its
      deltas add to the `inter-rater` capability this change creates
- [ ] **Task 7.5**: Close the issues the reviewer UX change fixes — #67, #70,
      #71, #72, #73 — with the verifying evidence
- [ ] **Task 7.6**: Deferred work now unblocked by the archive, in priority
      order: #78 (httpx/authlib conflict — a dependency bump, safe only once the
      tree is unfrozen), #75 (`_USER_FEEDBACK_NAMES`, which needs the
      fail-closed guard extended past author exclusion first), #77 (test env
      leakage), #76 (missing `is_inter_rater` on metadata-poor annotations),
      #74 (reviewer score matrix)
