# Change: Require Access control on SSH tunnel routes

Tracks [#66](https://github.com/AI-as-Infrastructure/aiinfra-atlas/issues/66).

## Why

A tunnel public hostname route of the form `ssh://localhost:22` is reachable by
anyone who knows the hostname unless a Cloudflare Access application covers that
hostname. The route is a path through Cloudflare's edge to the host's SSH port; the
tunnel's outbound-only connection and a deny-all UFW policy do not restrict it,
because cloudflared reaches `localhost:22` from inside the host.

The deployment guidance does not currently reflect this:

- `docs/cloudflare.md` lists the SSH Access application as **optional**
  ("Optionally create a separate Access application for SSH with tighter
  policies"), so a deployment can follow the guide completely and still leave the
  SSH route unauthenticated.
- The Security Notes state "No ports are exposed to the internet; all traffic
  flows through Cloudflare's edge". That is literally true and reads as though
  Zero Trust policies cover SSH. They cover only hostnames that have an Access
  application.
- The route table describes the SSH row as "Browser-based SSH (Cloudflare renders
  terminal)", which describes only one of its uses. The same route also backs
  native clients via `cloudflared access tcp`, and browser rendering is a separate
  setting that may be off.
- `openspec/specs/cloudflare-deployment/spec.md` has no requirement covering SSH
  route authentication at all, so nothing fails a review when it is missing.

An unauthenticated SSH route is not equivalent to an open host — a key-only sshd
still rejects unauthenticated clients — but it removes the Zero Trust layer the
documentation implies, and it makes the host's own sshd configuration the only
control.

## What Changes

- Add requirements to the `cloudflare-deployment` capability: every SSH tunnel
  route MUST be covered by its own Access application; the deployment
  documentation MUST NOT describe SSH Access as optional; and the Security Notes
  MUST distinguish "no inbound ports" from "authenticated at the edge".
- Require that each SSH route is an **independent** unit: its own Access
  application, its own policy, and its own service token. No credential, policy or
  application is shared between SSH routes, so revoking or rotating one cannot
  affect another.
- Require that unattended local forwards authenticate with an Access **service
  token** rather than an interactive login, since a hidden or background forward
  cannot re-prompt when an interactive token expires.
- Update `docs/cloudflare.md`: correct the Security Notes wording, make the SSH
  Access application a required checklist step, correct the route table
  description, and document the service-token flow for native SSH clients.
- **BREAKING** for existing deployments: adding an Access application to an SSH
  hostname immediately breaks any forward that does not present a token. The
  Access application and the forward's service token MUST be introduced together.

No application code changes. All steps are operational or documentation.

## Impact

- Affected specs: `cloudflare-deployment`
- Affected code: none
- Affected docs: `docs/cloudflare.md`
- Affected operations: Cloudflare Access applications, service tokens, and any
  local `cloudflared access tcp` forward used by an SSH client

## Constraints and ordering

1. **The Access application and the service token go in together.** Creating the
   application first breaks unattended forwards; creating the token first is
   harmless. Create the token, wire it into the forward, then create the
   application and policy.
2. **Do not sequence this immediately before a session that needs the host.** If
   the change goes wrong, remote access is what is lost. Land it during a window
   where losing the forward is recoverable — for example while LAN access to the
   host is available.
3. **One route, one application, one token.** Routes must not share credentials
   or policies, so each route is verified and rotated independently.
4. **Leave browser rendering off** unless browser-based SSH is actually wanted.
   It is a separate setting on the Access application and is not required for
   native clients using `cloudflared access tcp`.
