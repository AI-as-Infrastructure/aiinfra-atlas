# cloudflare-deployment (delta)

## ADDED Requirements

### Requirement: SSH Tunnel Route Access Control
Every tunnel public hostname route that forwards to an SSH service MUST be covered
by a Cloudflare Access application for that exact hostname. A deployment with an
SSH route and no corresponding Access application MUST be treated as
misconfigured, because the route is a path through Cloudflare's edge to the host's
SSH port and neither the tunnel's outbound-only connection nor a deny-all UFW
policy restricts who may traverse it.

#### Scenario: SSH route without an Access application
- **GIVEN** a tunnel route of the form `ssh://localhost:22`
- **WHEN** no Access application covers that hostname
- **THEN** the deployment SHALL be considered misconfigured
- **AND** the hostname SHALL be reachable by any client that knows it, with the
  host's own sshd configuration as the only remaining control

#### Scenario: Operator verifies Access coverage
- **WHEN** an operator checks whether an SSH hostname is protected
- **THEN** an unprotected hostname SHALL be distinguishable from a protected one
  by an unauthenticated request: a protected hostname redirects to the Access
  login endpoint, an unprotected one does not
- **AND** `cloudflared access login <url>` SHALL report that no Access application
  was found for an unprotected hostname

### Requirement: Independent Access Control Per SSH Route
Each SSH route MUST be an independent unit of access control: its own Access
application, its own policy, and its own service token. No Access application,
policy, or credential SHALL be shared between two SSH routes, so that revoking,
rotating or misconfiguring the credentials of one route cannot affect access to
another.

#### Scenario: Credential revoked on one route
- **GIVEN** two hosts each reachable through their own SSH route
- **WHEN** the service token for one route is revoked or rotated
- **THEN** access to the other route SHALL be unaffected

#### Scenario: Policy change on one route
- **GIVEN** two hosts each reachable through their own SSH route
- **WHEN** the Access policy for one route is changed or its application deleted
- **THEN** the other route's policy SHALL remain in force and independently
  verifiable

### Requirement: Service Token Authentication For Unattended Forwards
An unattended local forward (`cloudflared access tcp`) used by a native SSH client
MUST authenticate with an Access service token, supplied as
`TUNNEL_SERVICE_TOKEN_ID` and `TUNNEL_SERVICE_TOKEN_SECRET` or the equivalent
flags. It MUST NOT depend on an interactive `cloudflared access login` token,
because a background or hidden forward cannot prompt for re-authentication when
that token expires with the application's session duration.

#### Scenario: Forward runs unattended across a session expiry
- **GIVEN** a forward configured with a service token
- **WHEN** the Access application's session duration elapses
- **THEN** the forward SHALL continue to authenticate without operator interaction

#### Scenario: Forward started without a token against a protected route
- **GIVEN** an SSH route covered by an Access application
- **WHEN** a forward is started with no service token
- **THEN** the forward SHALL fail rather than serve an unauthenticated listener
- **AND** the failure SHALL be recorded where an operator can read it, rather than
  surfacing only as a connection refused at the SSH client

### Requirement: Accurate Edge Security Documentation
Deployment documentation MUST NOT describe the SSH Access application as optional,
and MUST distinguish between having no inbound listening ports and being
authenticated at Cloudflare's edge. Documentation describing an SSH route MUST
state which client flows it serves, and MUST NOT imply browser rendering is
enabled when it is a separate setting.

#### Scenario: Reader follows the deployment checklist completely
- **WHEN** an operator completes every checklist step in the deployment guide
- **THEN** no SSH route SHALL be left without an Access application

#### Scenario: Reader consults the security notes
- **WHEN** an operator reads the security notes to establish the deployment's posture
- **THEN** the notes SHALL state that Zero Trust policies apply only to hostnames
  covered by an Access application
- **AND** SHALL NOT imply that the absence of inbound ports authenticates SSH
