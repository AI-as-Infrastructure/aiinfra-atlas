# Tasks: Security Updates May 2025

## 1. Replace python-jose with PyJWT
- [x] 1.1 Update `config/requirements.txt`: swap `python-jose[cryptography]==3.5.0` for `PyJWT[crypto]>=2.8.0`
- [x] 1.2 Update `backend/modules/auth.py` imports and API calls to PyJWT
- [x] 1.3 Update `tests/backend/modules/test_cloudflare_jwt.py` for PyJWT
- [x] 1.4 Run test suite to verify JWT validation

## 2. Gate debug endpoint in production
- [x] 2.1 Return 404 from `/api/debug/user-id` when `ENVIRONMENT=production`

## 3. Add FastAPI security headers
- [x] 3.1 Add security response headers to `security_middleware` in `backend/app.py`

## 4. Update outdated Python dependencies
- [x] 4.1 Update `psutil` to latest stable
- [x] 4.2 Check and update `numpy` compatibility
- [x] 4.3 Regenerate `config/requirements.lock`

## 5. Minor fixes
- [x] 5.1 Replace `print()` with `logger.info()` in `backend/app.py`
- [x] 5.2 Add salt generation guidance to `config/.env.template`

## 6. Validation
- [x] 6.1 Run existing test suite
- [x] 6.2 Verify JWT validation works with PyJWT
