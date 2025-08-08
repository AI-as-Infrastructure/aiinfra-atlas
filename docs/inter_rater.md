# Inter-rater Ratings

## Overview
The inter-rater feature enables authenticated users to provide secondary (inter-rater) ratings on sessions that already have initial feedback. All inter-rater activity is anonymous by design and clearly delineated in Phoenix.

## Key Guarantees
- **Authentication required** (Cognito JWT tokens)
- **Users only rate sessions they did not originally author** (automatic exclusion)
- **Users only see sessions with existing feedback annotations** (no empty sessions)
- **Anonymity**: users are represented by irreversible anonymous IDs
- **No client IPs** collected, logged, or exported
- **Inter-rater annotations** in Phoenix are clearly labeled and separate from original ratings
- **All 9 evaluation fields** are captured and stored in Phoenix

## Configuration (.env)
```bash
# Enable/disable feature
INTER_RATER_ENABLED=true

# Phoenix project (fallbacks supported in code)
INTER_RATER_PROJECT=YourPhoenixProject

# Allocation limits
INTER_RATER_MAX_RATINGS=3          # Max inter-rater ratings per session (default: 3)
INTER_RATER_SESSIONS_PER_USER=5    # Sessions offered per user (default: 5)
```

Also ensure Cognito auth is enabled where required:
```bash
VITE_USE_COGNITO_AUTH=true
```

## Architecture
- Backend
  - `backend/services/inter_rater_service.py`: allocation, per-user cache, limits
  - `backend/services/phoenix_client.py`: queries/duplicate checks against Phoenix
  - `backend/telemetry/api.py`: unified feedback endpoint (regular + inter-rater)
  - `backend/telemetry/feedback.py`: Phoenix span annotations (adds "[Inter-rater]" prefix and metadata)
  - `backend/services/anonymous_id_service.py`: generates environment-scoped anonymous IDs from Cognito `sub`
- Frontend
  - `frontend/src/components/InterRaterButton.vue`: shows available session count
  - `frontend/src/components/InterRaterDashboard.vue`: loads sessions and submits ratings
  - `frontend/src/components/InterRaterPlayback.vue`: rating UI for a single session

## Data Flow (Allocation)
1. User logs in (Cognito), navigates to app
2. Inter-rater button calls `GET /api/inter-rater/stats`
3. Backend verifies JWT, derives anonymous ID
4. Allocation service queries Phoenix for eligible sessions and applies rules:
   - **Only include sessions with existing feedback annotations** (no empty sessions)
   - **Exclude sessions authored by this anonymous user** (prevents self-rating)
   - **Exclude sessions already inter-rated by this user** (prevents duplicate rating)
   - **Enforce `INTER_RATER_MAX_RATINGS`** limit (default: 3 per session)
   - **Apply deterministic user-specific allocation** (same user always gets same sessions)
   - **Limit to `INTER_RATER_SESSIONS_PER_USER`** (default: 5 per user)
5. Counts cached per user (short TTL). Cache invalidated when the user submits inter-rater feedback.

## Data Flow (Submission)
1. Dashboard posts inter-rater feedback to `POST /api/feedback`
2. Backend verifies JWT, derives anonymous ID
3. Feedback is attached to the original QA span in Phoenix as span annotations via `feedback.submit_span_annotation()`
4. Inter-rater entries:
   - Annotation names are prefixed with `[Inter-rater]`
   - Metadata includes `is_inter_rater=true`, `rater_id=<anon_id>`, `original_span_id=<phoenix_span>`
5. On success, the user’s inter-rater cache is invalidated so counts update immediately

## Anonymity & Privacy
- Anonymous IDs: `anonymous_id_service` hashes the Cognito `sub` with an environment-specific salt, producing `anon_<16-hex>` IDs
- No client IP collection/logging/export
- No emails or usernames logged
- Phoenix submissions contain only anonymized identifiers and rating metadata

## Evaluation Fields (Order)
Both main ratings and inter-ratings use the same field order - **all 9 fields are captured**:
1. **Factual Accuracy** (1–5 Likert scale)
2. **Corpus Fidelity** (1–5 Likert scale)
3. **Analysis Quality** (1–5 Likert scale)
4. **Relevance** (1–5 Likert scale) 
5. **Difficulty** (1–5 Likert scale)
6. **Clarity** (1–5 Likert scale)
7. **User Type** (Expert / Non-expert) - *Fixed: Now properly stored in Phoenix*
8. **Comments** (Free text feedback)
9. **Faults** (hallucination, off_topic, inappropriate, bias checkboxes)

**Recent Fix**: User Type field was previously not being stored in Phoenix annotations - this has been resolved.

## API Endpoints
- `GET /api/inter-rater/stats`
  - Returns user-specific availability and limits
  - **Requires Authentication**: Cognito JWT token in Authorization header
- `GET /api/inter-rater/sessions`
  - Returns the list of sessions available to the current user
  - **Requires Authentication**: Cognito JWT token in Authorization header
- `POST /api/feedback`
  - Submits both regular and inter-rater feedback; inter-rater metadata is set server-side
  - **Requires Authentication**: Cognito JWT token in Authorization header
- `GET /api/debug/user-id` *(Development only)*
  - Debug endpoint to verify user ID extraction from JWT tokens

## Caching
- Per-user cache key: `inter_rater_sessions_{anon_user_id}`
- Short TTL (~5 minutes)
- Invalidated immediately on successful inter-rater submission by that user

## Phoenix Notes
- POST annotations endpoint used: `/v1/span_annotations?sync=true`
- All inter-rater annotations are clearly separated by name prefix and metadata
- Headers include API key only; headers are redacted in logs

## Troubleshooting
- **No sessions available**: 
  - Verify `INTER_RATER_ENABLED=true` in .env
  - Check `INTER_RATER_PROJECT` matches your Phoenix project
  - Ensure initial feedback with **user_id** exists in Phoenix annotations
  - Verify user is authenticated (Cognito JWT token present)
- **User sees own ratings**: 
  - Fixed: Frontend now sends Authorization headers with all feedback submissions
  - Ensure user_id is properly captured during original feedback submission
- **Missing evaluation fields**: 
  - Fixed: All 9 fields including User Type are now stored in Phoenix
- **Duplicate rating prevented**: Backend checks if the same rater already rated the same original span
- **Count not updating immediately**: Cache invalidation happens after submission (handled in backend)

## Recent Fixes (2025-08)
- ✅ **Authentication Bug**: Fixed frontend components to send Authorization headers with feedback
- ✅ **User Type Field**: Added missing User Type annotation to Phoenix feedback processing  
- ✅ **Session Filtering**: Only sessions with existing feedback annotations are allocated for inter-rating
- ✅ **Anonymous ID Logging**: Enhanced logging for debugging while maintaining privacy
- ✅ **Filter Loading**: Fixed New Session button to properly reload dynamic filters


