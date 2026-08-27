# Inter-Rater Manual Test Protocol

Manual acceptance testing for the inter-rater reliability workflow, to be run
against a deployed environment before a focus-group session begins.

This is not the automated suite (see [testing.md](testing.md)) and not the
architecture reference (see [inter_rater.md](inter_rater.md)). It covers what only
a person can verify: that a real reviewer, logging in with real credentials,
receives a correct queue and that their ratings land intact.

It has two parts, run in order:

- **[Part 1 — Developer checks](#part-1--developer-checks)** requires server access
  and knowledge of the deployment. Run this first and fix anything it finds. A
  reviewer cannot diagnose these faults, and several of them make a reviewer's
  results useless without being visible in the interface.
- **[Part 2 — Reviewer walkthrough](#part-2--reviewer-walkthrough)** requires only a
  browser and a login. It is written to be sent to a non-technical tester on its
  own — copy that section into an email or share this page and point them at it.

---

# Part 1 — Developer checks

Run every check here before involving a reviewer. Record results in the
[Part 1 results table](#part-1-results).

## Conventions

- `<APP_URL>` — the deployed application address (`VITE_API_URL`)
- Settings in `CAPITALS` are environment variables in the deployment's env file
- "the study project" — the telemetry project named by `INTER_RATER_PROJECT`
- "the pool" — the prompts listed in the manifest at `INTER_RATER_POOL_MANIFEST`

Expected values come from the deployment's own configuration, not from this
document. Read them first:

```bash
grep -E "^(ATLAS_VERSION|INTER_RATER_[A-Z_]+)=" config/.env.production
```

## 1. Preconditions

Each failure here invalidates everything downstream. Do not continue past a
failure.

### D1 — The study design is arithmetically sound

```bash
make seed-dry
```

**Expect:** the capacity line and the target line show the **same** number, with no
`WARNING: capacity ... is below ...` line.

```
Seed pool: <N> questions × INTER_RATER_MAX_RATINGS=<C> → up to <N×C> total ratings
  Focus group target: <R> reviewers × <S> ratings = <R×S> rating slots
```

Balanced allocation is active only while `N × C = R × S`. If the numbers differ the
study is not saturated: some prompts receive fewer ratings than intended, or
reviewers run out of work before completing their quota. Note that `--count` on a
seed run only *warns* at seed time — the rejection happens later, at allocation.

### D2 — The application is genuinely up

```bash
systemctl is-active gunicorn llm-worker
```

`is-active` reports `active` while workers are still booting, and boot takes around
20 seconds. It is not proof. Confirm properly by reproducing the import in a single
process:

```bash
set -a; . config/.env.production; set +a
.venv/bin/python -c "import backend.app"
```

**Expect:** silence. Any traceback is a configuration fault, and this is the fastest
way to see it — service logs may show only `Worker failed to boot`, with the real
exception written to the error log file instead.

### D3 — Version stamping is correct, before any seeding

`ATLAS_VERSION` is written to every telemetry span, so it stamps collected data with
the code version. **Set it before seeding.** Set afterwards, the already-seeded
spans carry the old value permanently and cannot be corrected.

### D4 — Reviewer identities can authenticate

Confirm each identity that will be used — including the reviewer's in Part 2 — is
permitted by the access policy.

If your provider emails a one-time code, an address that is not permitted commonly
still shows the code-entry screen and simply never receives mail. "No email
arrived" and "not authorised" are indistinguishable from the outside, so verify the
policy rather than retrying.

## 2. The pool guard

### D5 — An unseeded study reports an error, not an empty queue

Run **before** the pool is seeded. Do not delete an existing pool to test this.

With `INTER_RATER_DEFAULT_UI=true` and no readable manifest at
`INTER_RATER_POOL_MANIFEST`, load `/inter-rater` as an authenticated user.

**Expect:** an error naming the study pool.

**A queue of zero prompts is a failure, not a pass.** It means allocation fell back
to rating whatever happens to be in the project, which removes every study
guarantee — pool purity, the capacity check, and a stable cohort key. Ratings
collected in that state cannot be used for the intended analysis, and nothing in
the interface indicates a problem.

## 3. Allocation

### D6 — The manifest describes the intended pool

```bash
python3 -c "import json,os;d=json.load(open(os.environ['INTER_RATER_POOL_MANIFEST']));print(d['count'], d['project'], len(d['qa_ids']))"
```

**Expect:** count equals the intended pool size, `project` equals
`INTER_RATER_PROJECT`, and `qa_ids` has the same length as the count. A short count
means a partial seed — do not test on a partial pool.

Back this file up alongside the telemetry export. It defines the pool for
reproducibility and is normally gitignored.

### D7 — Allocation spreads across the cohort

Log in as two distinct identities and compare their queues.

**Expect:** each receives exactly `INTER_RATER_SESSIONS_PER_USER` prompts, and the
two sets are **not identical**.

Identical queues mean allocation is not spreading. The consequence is statistical
rather than visible: rater severity becomes inseparable from which prompts a
reviewer saw. Record the first few prompt identifiers from each queue as evidence.

### D8 — A queue is stable for its reviewer

Reload twice as one identity. **Expect:** same prompts, same order. A queue that
changes between reloads means the assignment is not stable and quota cannot be
tracked.

## 4. Submission

### D9 — Ratings are stored complete and once only

Submit one full rating, then attempt to rate the same prompt again from the same
identity.

**Expect:** the first submission stores every field; the second is refused as
unavailable. A second stored rating from one reviewer on one prompt breaks the
independence assumption the analysis relies on.

## 5. Telemetry and privacy

### D10 — Annotations attach to the original span

In the telemetry backend, open the study project and find the span for a prompt you
rated.

**Expect:** the rating attached to that span as annotations, prefixed to
distinguish each reviewer's submission (`[inter-rating-N]`), with all rubric fields
present.

### D11 — The version stamp is correct

**Expect:** `atlas_version` on seeded spans matches the value confirmed in D3. An
older value means it was set after seeding, and the provenance record must say so.

### D12 — Reviewers are not identifiable

**Expect:** reviewer identity appears only as an anonymised identifier
(`anon_<hash>`). No email address, name, or provider subject identifier anywhere in
the telemetry.

This is a privacy requirement, not a preference. Any leak stops testing.

## 6. The data survives

### D13 — Backups include the study project

Run the deployment's backup command; confirm the study project appears in its
output.

### D14 — Exported ratings are analysable

Export the annotations and confirm the rubric fields survive in a form usable for
inter-rater reliability analysis — one record per reviewer per prompt, each scale
distinguishable.

Do this **before** any reset. A reset deletes the project, and annotations are
usually the only record of a rating.

## Not testable by hand

**The per-prompt rating cap.** Proving no prompt exceeds `INTER_RATER_MAX_RATINGS`
requires that many reviewers rating one prompt plus one more being refused.
Enforcement is an atomic lock in the submission path, covered by the automated
suite. Its absence from manual testing is not a gap.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| No one-time-code email arrives | Address not permitted by the access policy. The code screen appears anyway, so it looks like a mail delay. |
| `/inter-rater` shows an empty queue | Pool guard inactive. This is a failure — see D5. |
| `/inter-rater` shows a study-pool error | Correct before seeding; a fault after it. |
| `is-active` says `active` but nothing serves | Workers still booting, or booted and died. Wait 20s, then use the D2 import check. |
| Every page errors | A configuration fault taking the whole application down. Config validation runs when modules are imported, so any bad setting presents as total failure regardless of which setting is wrong. Use the D2 import check. |
| Refuses to start after an env change | A deliberate fail-fast check: required study settings have no defaults, a project-name mismatch is rejected, and a default anonymisation salt is refused in production. |

A general rule: **an error is usually the system working.** The guards refuse rather
than degrade quietly, because quiet degradation produces data that looks valid and
is not.

## Part 1 results

Environment: ______________  Version: ______________  Date: ______________

| Check | Pass | Notes / evidence |
|---|---|---|
| D1 capacity arithmetic | | |
| D2 application imports cleanly | | |
| D3 version set before seeding | | |
| D4 identities authenticate | | |
| D5 unseeded reports error, not empty queue | | |
| D6 manifest matches intended pool | | |
| D7 queues full length and differ | | |
| D8 queue stable across reloads | | |
| D9 rating stored complete, double rating refused | | |
| D10 annotations on original span | | |
| D11 version stamp correct | | |
| D12 reviewers anonymised | | |
| D13 backup includes project | | |
| D14 export analysable | | |

Stop and resolve before Part 2 if D1–D5 or D12 fail.

---

# Part 2 — Reviewer walkthrough

*This section is self-contained. It can be sent to a tester on its own — it assumes
no technical knowledge and requires nothing but a browser.*

Thank you for helping test this. You are not being asked to judge the historical
answers themselves — you are checking that the **tool works properly** before a
group of reviewers uses it for real.

Please work through the steps below and note what happens. It should take about
20–30 minutes. There are no wrong answers, and finding a problem is a useful
result, not a failure.

**What you will need:** the web address, and the email address that has been
authorised for you.

## Before you start

Two things worth knowing, so nothing surprises you:

- **An error message may be the correct result.** The system is built to stop and
  say so when something is not right, rather than carry on quietly. If you see an
  error, write down exactly what it says — word for word if you can — and carry on
  to the next step. Do not try to fix anything.
- **Please do not copy the questions or answers anywhere else.** They are research
  material.

## 1. Signing in

1. Open the web address in your browser.
2. Enter your authorised email address.
3. If a code is emailed to you, enter it.

**If no email arrives after a few minutes, stop and tell the organiser.** It almost
certainly means your address has not been added yet, not that the email is slow.
Trying again will not help.

- Did you get in? ______
- Anything confusing about the sign-in? ______

## 2. Your list of tasks

Once signed in you should land on a page of rating tasks.

- How many items are you offered? ______
- Was there a delay before the list appeared? Did anything look broken or badly
  positioned while it loaded? ______
- Did you see an error instead of a list? If so, write it down exactly: ______

## 3. Rating one item

Open the first item. You should see a question, an answer, and the sources the
answer drew on.

Work through the rating form and note as you go:

- Are there **six** rating scales? ______
- Is it clear what each scale is asking? Note any wording that made you hesitate:
  ______
- Give one scale a very high or very low score. Does the form ask you to explain
  that score? ______
- Try to submit **without** writing that explanation. Does it stop you, and is the
  message clear? ______
- Now complete everything — all six scales, the explanations, and the fault section
  with its explanation — and submit.

- Did it submit successfully? ______
- Roughly how long did the whole item take? ______

## 4. After submitting

- Did the item disappear from your list? ______
- Did the number of remaining items go down by one? ______
- Go back and try to rate the **same** item again. What happens? ______

*(It should refuse. That is correct behaviour, not a bug.)*

## 5. A second item

Rate one more item, more quickly this time.

- Anything different or unexpected the second time? ______
- Did anything feel slow, confusing, or easy to get wrong by accident? ______

## 6. Overall

- Anything that looked visually wrong — misaligned, off-centre, odd colours, text
  cut off, hard to read? ______
- Anything you expected to be able to do and couldn't? ______
- If you were rating 20 of these in a sitting, what would irritate you most?
  ______
- Anything else? ______

## What to send back

Your answers above, plus:

- Which browser and device you used: ______
- The date and roughly what time you tested: ______
- **Exact wording** of any error messages you saw

If something went badly wrong, note what you were doing immediately beforehand —
that is usually the most useful detail.

Thank you.
