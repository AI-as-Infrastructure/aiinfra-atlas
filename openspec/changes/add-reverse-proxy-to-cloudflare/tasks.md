# Tasks: Add Reverse Proxy to Cloudflare Tunnel Deployment

## Prerequisites
- [x] Review production `nginx.conf.template` for reusable patterns
- [x] Review current `cloudflare.sh` for sections that need modification
- [x] Confirm no other active changes conflict with these files

## Implementation Tasks

### Phase 1: Nginx Configuration Template
- [x] **Task 1.1**: Create `deploy/cloudflare/nginx-cloudflare.conf.template` derived from production template -- localhost-only binding (`listen 127.0.0.1:80`), no SSL, no certbot, no HSTS
- [x] **Task 1.2**: Add `Cache-Control: no-cache, no-store, must-revalidate` for `index.html` (exact match `location = /index.html`)
- [x] **Task 1.3**: Keep static asset caching (`expires 30d`) for hashed files (JS, CSS, images, fonts)
- [x] **Task 1.4**: Keep `/api` proxy and `/ws` WebSocket proxy blocks targeting `127.0.0.1:8000`

### Phase 2: Update Deploy Script
- [x] **Task 2.1**: Add `nginx` to the `apt install` line in `cloudflare.sh` (currently explicitly excludes it)
- [x] **Task 2.2**: Add Nginx config deployment section -- substitute `$APP_DIR` and `$SERVER_NAME` in template, install to `/etc/nginx/sites-available/`, symlink to `sites-enabled/`, remove default site
- [x] **Task 2.3**: Add Nginx systemd management -- enable and start Nginx service
- [x] **Task 2.4**: Update cloudflared `config.yml` ingress from `http://localhost:8000` to `http://localhost:80`
- [x] **Task 2.5**: Remove `SERVE_STATIC=true` from Gunicorn systemd service definition
- [x] **Task 2.6**: Update deployment summary output to reflect Nginx in the architecture
- [x] **Task 2.7**: Add Nginx to the health check loop alongside existing services

### Phase 3: Update Lifecycle Scripts
- [x] **Task 3.1**: Update `stop_cloudflare.sh` -- add Nginx stop between cloudflared and Gunicorn (cloudflared first, then Nginx, then LLM worker, then Gunicorn, then Redis)
- [x] **Task 3.2**: Update `clean_cloudflare.sh` -- remove Nginx site config, disable Nginx service, remove symlink

### Phase 4: Remove SERVE_STATIC Code
- [x] **Task 4.1**: Remove the `SERVE_STATIC` conditional block from `backend/app.py` (lines 183-208)
- [x] **Task 4.2**: Remove any `SERVE_STATIC` references from `config/.env.template` if present (none found)

### Phase 5: Update Documentation and Help
- [x] **Task 5.1**: Update `help-cf` target in `deploy/help.mk` to reflect the Nginx architecture
- [x] **Task 5.2**: Update deployment documentation in `docs/cloudflare.md`

### Phase 6: Validation
- [x] **Task 6.1**: Run `openspec validate add-reverse-proxy-to-cloudflare --strict`
- [x] **Task 6.2**: Verify existing deploy scripts are unmodified (`git diff deploy/production/ deploy/staging/ deploy/dev/`)
- [x] **Task 6.3**: Verify shell script syntax (`bash -n` on all modified scripts)
- [x] **Task 6.4**: Verify Nginx config template syntax (visual inspection)
- [x] **Task 6.5**: Verify `backend/app.py` no longer contains `SERVE_STATIC` references

## Verification Commands
```bash
# Check shell syntax
bash -n deploy/cloudflare/cloudflare.sh
bash -n deploy/cloudflare/scripts/stop_cloudflare.sh
bash -n deploy/cloudflare/scripts/clean_cloudflare.sh

# Confirm no SERVE_STATIC in backend
grep -r "SERVE_STATIC" backend/

# Confirm no changes to existing deploy scripts
git diff --name-only deploy/production/ deploy/staging/ deploy/dev/

# Validate OpenSpec
openspec validate add-reverse-proxy-to-cloudflare --strict
```

## Rollback Plan
All changes are reversible:
1. Restore `SERVE_STATIC` block in `backend/app.py` from git
2. Revert `cloudflare.sh`, `stop_cloudflare.sh`, `clean_cloudflare.sh` from git
3. Remove `deploy/cloudflare/nginx-cloudflare.conf.template`
4. On deployed servers: stop Nginx, revert cloudflared ingress to port 8000, re-add `SERVE_STATIC=true` to Gunicorn service
