# Tasks: Add Cloudflare Zero Trust Tunnel Deployment

## Prerequisites
- [x] Verify existing deploy scripts are unmodified by this change
- [x] Review Cloudflare Tunnel token-based authentication model
- [x] Confirm FastAPI `StaticFiles` mount approach for serving Vue.js dist/

## Implementation Tasks

### Phase 1: Environment Configuration
- [x] **Task 1.1**: Add Cloudflare-specific variables to `config/.env.template` (CLOUDFLARE_TUNNEL_TOKEN, CLOUDFLARE_TUNNEL_NAME)
- [x] **Task 1.2**: Document Cloudflare tunnel vars in template comments (set in core env files alongside app settings)

### Phase 2: Main Deploy Script
- [x] **Task 2.1**: Create `deploy/cloudflare/cloudflare.sh` -- main deployment script
- [x] **Task 2.2**: Implement environment file loading from `config/.env.production`
- [x] **Task 2.3**: Implement required variable validation (CLOUDFLARE_TUNNEL_TOKEN, CLOUDFLARE_TUNNEL_NAME, VITE_API_URL, REDIS_URL)
- [x] **Task 2.4**: Implement system dependency installation (python, redis, cloudflared -- no nginx)
- [x] **Task 2.5**: Implement Python venv setup and dependency installation from requirements.lock
- [x] **Task 2.6**: Implement Node.js setup (nvm, v22.14.0) and frontend build
- [x] **Task 2.7**: Implement Redis configuration with authentication (extracted from REDIS_URL)
- [x] **Task 2.8**: Implement cloudflared config.yml generation with single HTTP ingress rule to localhost:8000
- [x] **Task 2.9**: Implement Gunicorn systemd service (serves API + static files on 127.0.0.1:8000)
- [x] **Task 2.10**: Implement LLM worker systemd service
- [x] **Task 2.11**: Implement cloudflared systemd service (tunnel run with token)
- [x] **Task 2.12**: Implement UFW firewall configuration (deny incoming, allow outgoing, warn about SSH)
- [x] **Task 2.13**: Implement service startup and health verification

### Phase 3: Lifecycle Scripts
- [x] **Task 3.1**: Create `deploy/cloudflare/scripts/stop_cloudflare.sh` -- graceful stop (cloudflared first, then LLM worker, Gunicorn, Redis last)
- [x] **Task 3.2**: Create `deploy/cloudflare/scripts/clean_cloudflare.sh` -- full cleanup (services, config, app dir, logs, cloudflared config; preserve UFW state)

### Phase 4: Makefile Integration
- [x] **Task 4.1**: Add `cf`, `scf`, `dcf` targets to `deploy/Makefile`
- [x] **Task 4.2**: Add `help-cf`, `help-dcf`, `help-scf` targets to `deploy/help.mk`

### Phase 5: FastAPI Static File Serving
- [x] **Task 5.1**: Add static file mount to FastAPI app for serving Vue.js dist/ when running behind cloudflared (conditional on SERVE_STATIC env var)
- [x] **Task 5.2**: Ensure SPA routing fallback (return index.html for non-API, non-static routes)

### Phase 6: Validation
- [x] **Task 6.1**: Run `openspec validate add-cloudflare-tunnel-deployment --strict`
- [x] **Task 6.2**: Verify existing deploy scripts are unmodified (`git diff deploy/production/ deploy/staging/ deploy/dev/`)
- [x] **Task 6.3**: Verify shell script syntax (`bash -n` on all new scripts)
- [x] **Task 6.4**: Test environment variable validation logic
- [x] **Task 6.5**: Verify Makefile targets register correctly (`make help`)

## Verification Commands
```bash
# Check shell syntax
bash -n deploy/cloudflare/cloudflare.sh
bash -n deploy/cloudflare/scripts/stop_cloudflare.sh
bash -n deploy/cloudflare/scripts/clean_cloudflare.sh

# Verify Makefile targets
make help | grep -E 'cf|dcf|scf'

# Confirm no changes to existing deploy scripts
git diff --name-only deploy/production/ deploy/staging/ deploy/dev/

# Validate OpenSpec
openspec validate add-cloudflare-tunnel-deployment --strict
```

## Rollback Plan
All changes are additive. Rollback requires:
1. Remove `deploy/cloudflare/` directory
2. Revert Makefile target additions
3. Revert help.mk additions
4. Revert .env.template additions
5. Revert FastAPI static file mount (if added)
6. UFW rules are NOT automatically reverted (operator manages firewall state)
