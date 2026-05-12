# Change: Security updates May 2025

## Why
The `python-jose` JWT library is unmaintained (last release 2021) and used for all JWT validation in both Cognito and Cloudflare auth modes. A debug endpoint leaks auth configuration info in production. FastAPI lacks defense-in-depth security headers. Some Python dependencies are outdated.

## What Changes
- Replace `python-jose[cryptography]` with `PyJWT[crypto]` in auth module
- Gate `/api/debug/user-id` endpoint behind `ENVIRONMENT != production`
- Add security response headers to FastAPI security middleware
- Update outdated Python dependencies (`psutil`, `numpy`)
- Replace `print()` with `logger.info()` in app.py
- Add anonymous ID salt generation guidance to .env.template

## Impact
- Affected specs: `security-dependencies` (MODIFIED), `auth` (MODIFIED)
- Affected code:
  - `backend/modules/auth.py` — JWT library migration
  - `backend/routers/core.py` — debug endpoint gating
  - `backend/app.py` — security headers, print→logger
  - `config/requirements.txt` — dependency updates
  - `tests/backend/modules/test_cloudflare_jwt.py` — test updates
  - `config/.env.template` — salt documentation
