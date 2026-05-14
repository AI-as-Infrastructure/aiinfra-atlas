# Tasks: Update Inter-Rater Session Allocation

## 1. Update configuration
- [x] 1.1 Change `INTER_RATER_SESSIONS_PER_USER` from 10 to 20 in `config/.env.template`
- [x] 1.2 Change `INTER_RATER_SESSIONS_PER_USER` from 10 to 20 in `config/.env.staging`
- [x] 1.3 Change `INTER_RATER_SESSIONS_PER_USER` from 10 to 20 in `config/.env.production`

## 2. Verification
- [ ] 2.1 Verify `InterRaterService.__init__` reads sessions_per_user=20
- [ ] 2.2 Verify `/api/inter-rater/sessions` returns up to 20 sessions
