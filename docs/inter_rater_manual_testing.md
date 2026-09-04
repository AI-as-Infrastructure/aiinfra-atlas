# Inter-Rater Manual Test Protocol

Manual acceptance testing for the inter-rater workflow against a deployment.
Automated suite: [testing.md](testing.md). Architecture: [inter_rater.md](inter_rater.md).

Part 1 needs server access. Part 2 needs only a browser and can be sent to a
non-technical reviewer on its own. Run Part 1 first.

Placeholders: `<APP_URL>` = `VITE_API_URL`. `CAPITALS` = environment variables.

---

# Part 1 — Developer checks

Read the deployment's configured values first:

```bash
grep -E "^(ATLAS_VERSION|INTER_RATER_[A-Z_]+)=" config/.env.production
```

Stop and resolve before Part 2 if D1–D5 or D12 fail.

## D1 — Capacity arithmetic

```bash
make seed-dry
```

Expect the capacity line and target line to show the same number, and no
`WARNING: capacity ... is below ...`.

## D2 — Application imports cleanly

```bash
set -a; . config/.env.production; set +a
.venv/bin/python -c "import backend.app"
```

Expect silence. (`systemctl is-active` reports `active` during the ~20s boot, so it
is not proof.)

## D3 — Version stamp set before seeding

Confirm `ATLAS_VERSION` is the version under test. Must be set before `make seed`.

## D4 — Identities authenticate

Log in at `<APP_URL>` with each identity to be used, including the Part 2
reviewer's.

## D5 — Unseeded study reports an error

Run before seeding. With `INTER_RATER_DEFAULT_UI=true` and no readable
`INTER_RATER_POOL_MANIFEST`, load `/inter-rater`.

Expect an error naming the study pool. An empty queue is a failure.

## D6 — Manifest matches the intended pool

```bash
python3 -c "import json,os;d=json.load(open(os.environ['INTER_RATER_POOL_MANIFEST']));print(d['count'], d['project'], len(d['qa_ids']))"
```

Expect count = intended pool size, `project` = `INTER_RATER_PROJECT`, `qa_ids`
length = count. Back the file up alongside the telemetry export.

## D7 — Queues are full length and differ

Log in as two identities. Expect `INTER_RATER_SESSIONS_PER_USER` prompts each, and
the two sets not identical. Record the first few prompt IDs from each.

## D8 — Queue stable across reloads

Reload twice as one identity. Expect the same prompts in the same order.

## D9 — Rating stored complete, once only

Submit one full rating (six scales, per-scale rationales, faults, fault rationale).
Then attempt the same prompt again from the same identity.

Expect all fields stored; second attempt refused as unavailable.

## D10 — Annotations on the original span

In the telemetry backend, open the study project and find a rated prompt's span.
Expect annotations on that span, prefixed `[inter-rating-N]`, with all rubric
fields.

## D11 — Version stamp correct

Expect `atlas_version` on seeded spans to match D3.

## D12 — Reviewers anonymised

Expect identity to appear only as `anon_<hash>`. No email, name, or provider
subject identifier anywhere in the telemetry.

## D13 — Backup includes the study project

Run the deployment's backup command. Confirm the study project appears in the
output.

## D14 — Export is analysable

Export annotations before any reset. Confirm one record per reviewer per prompt,
each scale distinguishable.

## Not testable by hand

Per-prompt rating cap (`INTER_RATER_MAX_RATINGS`) — enforced by an atomic lock,
covered by the automated suite.

## Reference

| Symptom | Cause |
|---|---|
| No sign-in code email | Address not permitted by the access policy; the code screen still appears |
| Empty queue at `/inter-rater` | Pool guard inactive — failure |
| Study-pool error at `/inter-rater` | Correct before seeding; fault after |
| `is-active` active but nothing serves | Still booting, or booted and died — use D2 |
| Every page errors | Config fault; validation runs at import so any bad setting downs the app — use D2 |
| Refuses to start after env change | Fail-fast check: missing required study setting, project-name mismatch, or default anonymisation salt in production |

## Part 1 results

Environment: ______________  Version: ______________  Date: ______________

| Check | Pass | Notes |
|---|---|---|
| D1 capacity arithmetic | | |
| D2 imports cleanly | | |
| D3 version set before seeding | | |
| D4 identities authenticate | | |
| D5 unseeded reports error | | |
| D6 manifest matches pool | | |
| D7 queues full and differ | | |
| D8 queue stable | | |
| D9 stored complete, double refused | | |
| D10 annotations on span | | |
| D11 version stamp correct | | |
| D12 reviewers anonymised | | |
| D13 backup includes project | | |
| D14 export analysable | | |

---

# Part 2 — Reviewer walkthrough

*Self-contained — can be sent to a tester on its own.*

You are checking that the tool works, not judging the historical answers.

**Please work through your whole list of 20.** Some things only happen at the
very end, and those are the parts we most need checked. Allow about an hour,
and feel free to break it into two sittings — that is worth testing too.

Your ratings here are **test data and will be deleted** before the real study,
so nothing you record commits you to anything. Rate honestly but don't agonise.

Two notes before you start: an error message may be the correct result, so write
down its exact wording and continue rather than trying to fix anything; and please
do not copy the questions or answers anywhere else.

You need the web address and your authorised email address.

## 1. Sign in

1. Open the web address.
2. Enter your authorised email address.
3. Enter the emailed code, if one is sent.

If no email arrives after a few minutes, stop and tell the organiser — retrying
will not help.

- Did you get in? ______
- Anything confusing about signing in? ______

## 2. Your task list

- How many items are you offered? ______
- Any delay before the list appeared? Anything broken or badly positioned while it
  loaded? ______
- An error instead of a list? Exact wording: ______

## 3. Rate one item

Open the first item — question, answer, and sources.

- Are there six rating scales? ______
- Is it clear what each is asking? Note any wording you hesitated over: ______
- Each scale has a small ⓘ next to it. Hover your mouse over one. Does a
  definition appear? ______ (This is the check we most need — please try it on
  two or three different scales.)
- Hover over one of the numbered sources under the answer. Does a box appear,
  and can you read all of it, or is any part cut off at the edge of the
  screen? ______
- Try that on the **first** source in the row and the **last** one. Any
  difference? ______
- Give one scale a very high or very low score. Are you asked to explain it? ______
- Try to submit without that explanation. Does it stop you, with a clear message?
  ______
- Complete everything — six scales, explanations, faults and fault explanation —
  and submit. Did it succeed? ______
- Roughly how long did the item take? ______

## 4. After submitting

- Did the item leave your list? ______
- Did the remaining count drop by one? ______
- Does the count at the **top right** match the count on the page? ______
- Try to rate the same item again. What happens? ______ Exact wording: ______
  (Refusal is correct. We need to know whether it says you *already rated it*,
  or that it is *no longer available* — those mean different things.)

If the organiser has named a specific question for you to rate — one another
reviewer has already rated — find it in your list and do that one now. Note
anything unusual, and whether it looked any different from the others: ______

## 5. Moving around mid-task

Do these after two or three items, then carry on rating.

- Press your browser's **Back** button. What happens? ______ Are you offered an
  item you have already rated? ______ (You should not be.)
- **Reload** the page. Are you back where you left off, with the right number
  remaining? ______
- Click **FAQ** in the menu, then click the **ATLAS Hansard** title to return.
  How long before your task reappears? ______ Did it lose your place? ______

## 6. Review my ratings

There is a **Review my ratings** button on the task.

- Open it part-way through. Do you see the items you have rated, with the
  scores you gave? ______
- Roughly how long did it take to appear? ______
- Are the answers you rated clearly distinguishable from your own scores, or do
  they run together? ______
- Do you see **only your own** ratings, or anyone else's? ______ (You should
  only ever see your own.)
- Close it. Are you returned to the item you were working on, with anything you
  had already filled in still there? ______

## 7. Finish your list

Keep going until you have rated all 20.

- Did any item behave differently from the rest? ______
- Did the tool ever offer you an item you had already rated? ______
- Did you ever see a message saying an item was no longer available? ______
  Exact wording: ______
- When you finished the last one, what did you see? ______
- Is **Review my ratings** still reachable after finishing? ______ Does it show
  all 20? ______

## 8. Overall

- Anything visually wrong — misaligned, off-centre, odd colours, text cut off, hard
  to read? ______
- Anything you expected to do and couldn't? ______
- Having now rated 20, what irritated you most? ______
- Did your sense of what the scales mean shift as you went? ______
- Anything else? ______

## Send back

- Your answers above
- Browser and device: ______ (please be specific — Chrome, Firefox, Safari,
  Edge — as some problems only appear in one)
- Date and approximate time: ______
- Exact wording of any error messages
- For anything that went wrong, what you were doing immediately beforehand
