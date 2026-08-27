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

- [ ] **Task 2.1**: Confirm the route's current state: whether an Access
      application covers the hostname, and which authentication methods the host's
      sshd offers
- [ ] **Task 2.2**: Create a service token dedicated to this route. Record its
      client ID and secret in the operator's own credential store, not in the
      repository
- [ ] **Task 2.3**: Wire the token into this route's forward via
      `TUNNEL_SERVICE_TOKEN_ID` / `TUNNEL_SERVICE_TOKEN_SECRET`, keeping the secret
      out of the process command line
- [ ] **Task 2.4**: Confirm the forward still works with the token supplied and the
      route still unprotected. This isolates a token-plumbing failure from an
      Access-policy failure
- [ ] **Task 2.5**: Create the Access application for this hostname only. Leave
      browser rendering off unless browser-based SSH is wanted
- [ ] **Task 2.6**: Add a Service Auth policy accepting this route's service token
      only. Do not add the other routes' tokens
- [ ] **Task 2.7**: Verify an unauthenticated request to the hostname is now
      challenged, and that the token-bearing forward still connects
- [ ] **Task 2.8**: Verify a forward started without the token fails, and that the
      failure is visible in the forward's logs
- [ ] **Task 2.9**: Confirm the other SSH routes are unaffected by this route's
      application and token

## 3. Verify independence

- [ ] **Task 3.1**: Confirm each route has a distinct Access application, policy
      and service token, with nothing shared
- [ ] **Task 3.2**: Rotate one route's service token and confirm the other routes
      keep working
- [ ] **Task 3.3**: Record where each token is stored and how it is rotated

## 4. Archive

- [ ] **Task 4.1**: Archive this change
      (`openspec archive add-ssh-tunnel-access-control`)
