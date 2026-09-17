# Tasks

Documentation tasks (section 1) are safe to do at any time. The operational tasks
(sections 2 onward) change how the SSH routes authenticate and can cost remote
access to the host if done out of order — see the constraints in `proposal.md`.

Do not start section 2 immediately before a session that depends on remote access
to the host.

## 1. Documentation

- [x] **Task 1.1**: In `docs/cloudflare.md`, correct the Security Notes bullet
      "No ports are exposed to the internet; all traffic flows through
      Cloudflare's edge" so it distinguishes no-inbound-ports from
      authenticated-at-the-edge, and states that Access policies apply only to
      hostnames with an Access application
- [x] **Task 1.2**: Change the checklist item "Optionally create a separate Access
      application for SSH with tighter policies" to a required step, once per SSH
      route
- [x] **Task 1.3**: Correct the route table description for the SSH row: the route
      serves both browser-based SSH (only when browser rendering is enabled) and
      native clients via `cloudflared access tcp`
- [x] **Task 1.4**: Document the service-token flow for native SSH clients:
      creating a service token, the `TUNNEL_SERVICE_TOKEN_ID` /
      `TUNNEL_SERVICE_TOKEN_SECRET` environment variables, and why an interactive
      `cloudflared access login` token is unsuitable for an unattended forward
- [x] **Task 1.5**: Document how to verify a hostname is protected (unauthenticated
      request redirects to the Access login endpoint; `cloudflared access login`
      finds an application) so coverage can be checked rather than assumed

## 2. Per-route rollout

Repeat this section independently for each SSH route. Complete it fully for one
route before starting the next, and do not reuse any application, policy or token
between routes.

**Rollout status — 2026-09-17.** Two SSH routes are live behind Service Auth and verified
working from an operator workstation, over both a terminal `ProxyCommand` and an unattended
local forward. Host-specific configuration is recorded in the operator's own infrastructure
documentation, outside this repository.

The rollout did **not** follow this section's order: the Access applications and policies were
created *before* the tokens were wired into the forwards, which is the ordering `proposal.md`
warns against. The visible cost was that both unattended forwards were silently broken in the
interval — the local listener came up and the unit reported healthy, while every connection
failed with `websocket: bad handshake`. Consequently Task 2.4 can no longer be performed for
either route, and the dashboard-side steps are recorded below as verified-by-behaviour rather
than verified-by-inspection.

- [x] **Task 2.1**: Confirm the route's current state: whether an Access
      application covers the hostname, and which authentication methods the host's
      sshd offers
      — *both routes: each hostname returns 403 to an unauthenticated GET and each
      tokenless forward was refused with `bad handshake`, so an application covers
      both; both hosts are key-only with password authentication disabled, sshd on
      a non-default port.*
- [x] **Task 2.2**: Create a service token dedicated to this route. Record its
      client ID and secret in the operator's own credential store, not in the
      repository
      — *two distinct tokens, confirmed to differ in both client ID and secret.
      Operator-supplied; nothing token-bearing is in this repository.*
- [x] **Task 2.3**: Wire the token into this route's forward via
      `TUNNEL_SERVICE_TOKEN_ID` / `TUNNEL_SERVICE_TOKEN_SECRET`, keeping the secret
      out of the process command line
      — *one `0600` environment file per application, read both by the wrapper the
      `ProxyCommand` invokes (via `source`) and by the forward's service unit (via
      `EnvironmentFile=`, not `Environment=`, since unit files are world-readable).
      The token reaches cloudflared through the environment only; each secret was
      confirmed present in exactly one file on disk, and absent from both wrapper
      scripts.*
- [x] **Task 2.4**: Confirm the forward still works with the token supplied and the
      route still unprotected. This isolates a token-plumbing failure from an
      Access-policy failure
      — **WAIVED 2026-09-17.** Not performable for these two routes: both were
      already protected before the tokens were wired in, so no unprotected state
      remained in which to isolate token plumbing from an Access-policy failure.
      The isolation it buys was obtained after the fact instead, by the cross-token
      negative test in 2.6 and the tokenless-forward test in 2.8 — together these
      distinguish a token fault from a policy fault, which is what 2.4 exists to do.
      The task remains correct and should be performed in order for any future SSH
      route; the waiver covers only the two routes rolled out on this date.
- [x] **Task 2.5**: Create the Access application for this hostname only. Leave
      browser rendering off unless browser-based SSH is wanted
      — *an application exists for each hostname (evidenced by 2.1), one hostname
      per application, and `cloudflared access login` resolves each. **Browser
      rendering is off on both** — operator-confirmed, being dashboard state that
      cannot be checked from a client. Consistent with the 403 (rather than a login
      page) each hostname returns to an unauthenticated GET.*
- [x] **Task 2.6**: Add a Service Auth policy accepting this route's service token
      only. Do not add the other routes' tokens
      — *verified by cross-token negative test: each route's token presented against
      the **other** route's hostname is refused with `bad handshake`, in both
      directions, while each token connects on its own route. Neither policy accepts
      the other's token.*
- [x] **Task 2.7**: Verify an unauthenticated request to the hostname is now
      challenged, and that the token-bearing forward still connects
      — *both routes: 403 to an unauthenticated GET, and both token-bearing forwards
      connect. **Note:** a protected SSH route returns 403 with no redirect, not the
      302 an HTTP application gives — see the correction to `docs/cloudflare.md`
      under Task 1.5, and Task 5.1 below.*
- [x] **Task 2.8**: Verify a forward started without the token fails, and that the
      failure is visible in the forward's logs
      — *both routes: observed in the forward's journal as
      `ERR failed to connect to origin error="websocket: bad handshake"`. Note that
      the service manager still reports the unit active: cloudflared opens the local
      listener regardless and fails per-connection, so unit state is not a health
      signal — the log is.*
- [x] **Task 2.9**: Confirm the other SSH routes are unaffected by this route's
      application and token
      — *a four-way regression after each change: both terminal `ProxyCommand` paths
      and both local forwards, each returning its expected host.*

## 3. Verify independence

- [x] **Task 3.1**: Confirm each route has a distinct Access application, policy
      and service token, with nothing shared
      — *distinct applications (one hostname each), distinct tokens (differing in ID
      and secret), and distinct policies demonstrated by the mutual rejection in
      2.6. Each wrapper and each service unit reads only its own route's environment
      file, checked by inspecting every consumer's configured path.*
- [ ] **Task 3.2**: Rotate one route's service token and confirm the other routes
      keep working
      — *not exercised. Needs a new token issued in the dashboard; the mutual
      rejection in 2.6 is evidence of isolation but not of rotation. **Both tokens
      are non-expiring** (operator-confirmed), so nothing forces a rotation and this
      will not be exercised incidentally — but it also means a leaked token stays
      valid until explicitly revoked. The operator has accepted non-expiry as a
      deliberate trade-off (single operator and single user on a hardened system,
      with revocation rather than expiry as the control). That makes revocation the
      incident response, which is the argument for proving this task's path before it
      is needed rather than during an incident.*
- [x] **Task 3.3**: Record where each token is stored and how it is rotated
      — *recorded in the operator's own infrastructure documentation, outside this
      repository, per Task 2.2: one `0600` environment file per application, the
      consumers of each, and the rotation procedure (edit the environment file, then
      restart the forward's service unit; a terminal `ProxyCommand` picks up the new
      value on the next connection without a restart).*

## 4. Archive

- [x] **Task 4.1**: Archive this change
      (`openspec archive add-ssh-tunnel-access-control`)
      — *archived 2026-09-17. The `openspec` CLI is not installed on the machine that
      did this, so the archive was performed by hand to match the documented Stage 3
      steps: the four ADDED requirements were merged into
      `openspec/specs/cloudflare-deployment/spec.md`, and this change folder was
      moved to `openspec/changes/archive/2026-09-17-add-ssh-tunnel-access-control/`.
      Worth running `openspec validate --strict` when the CLI is next available —
      structure was checked by hand only.*

      **Archived with Task 3.2 open.** Rotation was never exercised and is not
      waived; it is carried forward as outstanding work rather than resolved. See
      3.2. Anyone treating this archived change as "everything verified" would be
      wrong on that one point.

## 5. Follow-up raised by the rollout

- [x] **Task 5.1**: The spec delta's scenario "Operator verifies Access coverage"
      stated that a protected hostname is distinguishable because it "redirects to
      the Access login endpoint". Measured against two live protected SSH routes, a
      protected **SSH/TCP** route returns **403 with no redirect**; only HTTP
      applications 302-redirect. As written the scenario would have failed a
      correctly protected SSH route — the exact route type this change governs.
      **Amended:** the scenario now specifies the
      `.well-known/cloudflare-access-protected-resource/` probe (200 protected, 404
      not) as the type-independent check, and explicitly forbids relying on a
      redirect-only test. A new scenario, "Redirect-based verification applied to an
      SSH route", records the 403-vs-302 difference so the false negative is stated
      rather than implied.
- [x] **Task 5.2**: The same scenario asserted `cloudflared access login` "SHALL
      report that no Access application was found for an unprotected hostname". That
      holds, but a single observation of it is easily over-generalised into a belief
      that `access login` never resolves a TCP route. It does, once an application
      exists. **Amended:** the bullet now says `access login` SHALL resolve the
      application for a protected hostname *including a TCP/SSH route*, so the check
      is not discarded as inapplicable to SSH.
- [x] **Task 5.3**: Added a "Documentation describes how to verify coverage"
      scenario under *Accurate Edge Security Documentation*, requiring that a
      documented verification procedure work for a TCP/SSH route and not present a
      redirect-only check as sufficient. This is what `docs/cloudflare.md` got wrong
      while every documentation task in section 1 was marked complete.
