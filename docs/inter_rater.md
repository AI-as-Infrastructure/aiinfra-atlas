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

## Configuration

**Important:** Inter-rater settings are now configured through the Corpus Wizard and stored in the corpus manifest (`backend/corpus/manifest.json`). Environment variables for inter-rater settings have been removed.

### Corpus Wizard Configuration

When building a new corpus using the Corpus Wizard, you can enable and configure inter-rater reliability in Step 7 (System Requirements):

1. Navigate to the **Inter-Rater Reliability** section
2. Toggle **Enable Inter-Rater Feedback** to on
3. Configure the following settings:
   - **Maximum Ratings per Session** (1-10): How many different users can rate each session
   - **Sessions per User** (1-50): How many sessions each user will be asked to rate

### Manifest Configuration

The settings are stored in `backend/corpus/manifest.json`:

```json
{
  "inter_rater": {
    "enabled": true,
    "max_ratings": 3,
    "sessions_per_user": 5
  }
}
```

### Phoenix Project

The Phoenix project name is configured via the standard `PHOENIX_PROJECT_NAME` environment variable (no separate inter-rater project variable needed).

### Authentication Requirement

Ensure Cognito auth is enabled where required:
```bash
VITE_USE_COGNITO_AUTH=true
```

## Configuration Guidelines

### Choosing Optimal Values

The relationship between `max_ratings` and `sessions_per_user` determines coverage and workload distribution:

**Small Teams (2-5 users):**
```json
{
  "inter_rater": {
    "enabled": true,
    "max_ratings": 2,
    "sessions_per_user": 10
  }
}
```
- Good for quick validation with limited resources
- Each session gets 2 independent ratings
- Users rate more sessions but with lighter coverage

**Medium Teams (5-10 users):**
```json
{
  "inter_rater": {
    "enabled": true,
    "max_ratings": 3,
    "sessions_per_user": 5
  }
}
```
- Recommended for most use cases
- Provides good statistical reliability
- Balanced workload per user

**Large Teams (10+ users):**
```json
{
  "inter_rater": {
    "enabled": true,
    "max_ratings": 5,
    "sessions_per_user": 3
  }
}
```
- Maximum inter-rater reliability
- Lower workload per user
- Requires more users for full coverage

### Coverage Calculation

To achieve full coverage of N sessions:
```
Minimum users needed = (N × max_ratings) / sessions_per_user
```

**Example:**
- 20 sessions to cover
- max_ratings=3
- sessions_per_user=5
- Minimum users = (20 × 3) / 5 = **12 users needed**

### Workload Estimation

Per-user time commitment:
```
Time per session: ~5-10 minutes (all 9 fields)
Total time = sessions_per_user × 5-10 minutes
```

With `sessions_per_user=5`: **25-50 minutes per user**

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
   - **Enforce `max_ratings`** limit (default: 3 per session)
   - **Apply deterministic user-specific allocation** (same user always gets same sessions)
   - **Limit to `sessions_per_user`** (default: 5 per user)
5. Counts cached per user (short TTL). Cache invalidated when the user submits inter-rater feedback.

## Allocation Algorithm Details

The allocation system uses **deterministic user-specific allocation** to ensure:
- Each user gets a consistent set of sessions (same user → same sessions)
- Different users get different, non-overlapping sessions
- Fair distribution across all available sessions

### How It Works

**Implementation:** `backend/services/inter_rater_service.py` (_allocate_sessions_to_user method)

1. **Sort Sessions:** All eligible sessions are sorted by `span_id` for consistent ordering
2. **Hash User ID:** User's Cognito UUID is hashed to generate a starting position
3. **Allocate Sequential Sessions:** Starting from hash position, allocate N sessions where N = `sessions_per_user`
4. **Wrap Around:** If needed, wrap around to the beginning (modulo operation)

### Example with 15 Sessions

```
Configuration:
- sessions_per_user=5
- 15 eligible sessions available (sorted by span_id)

User A (hash=0):  → Sessions [0, 1, 2, 3, 4]
User B (hash=5):  → Sessions [5, 6, 7, 8, 9]
User C (hash=10): → Sessions [10, 11, 12, 13, 14]
User D (hash=2):  → Sessions [2, 3, 4, 5, 6]  (overlaps with A and B)
```

**Note:** Some overlap occurs naturally. This is acceptable because the system also checks:
- User hasn't already rated the session
- Session hasn't reached `max_ratings` capacity

### Progressive Filling

As users complete ratings, sessions fill up:

```
Initial State:
- Session 001: 0/3 ratings
- Session 002: 0/3 ratings
- Session 003: 0/3 ratings

After User A rates:
- Session 001: 1/3 ratings ✓
- Session 002: 1/3 ratings ✓
- Session 003: 1/3 ratings ✓

After User B rates:
- Session 001: 2/3 ratings ✓
- Session 002: 2/3 ratings ✓
- Session 003: 2/3 ratings ✓

After User C rates:
- Session 001: 3/3 ratings [FULL - removed from allocation]
- Session 002: 3/3 ratings [FULL - removed from allocation]
- Session 003: 3/3 ratings [FULL - removed from allocation]
```

Once a session reaches `max_ratings`, it's automatically excluded from future allocations.

### Capacity and Coverage

The system self-balances:
- Sessions near capacity get fewer new allocations (already rated check)
- Users who complete their sessions get no new allocations (cache invalidation shows 0 available)
- New sessions with feedback automatically enter the allocation pool

## Data Flow (Submission)
1. Dashboard posts inter-rater feedback to `POST /api/feedback`
2. Backend verifies JWT, derives anonymous ID
3. Backend queries Phoenix to count existing inter-raters for this span (async, non-blocking)
4. Inter-rater number calculated: `existing_count + 1`
5. Feedback is attached to the original QA span in Phoenix as span annotations via `feedback.submit_span_annotation()`
6. Inter-rater entries:
   - Annotation names are prefixed with numbered format: `[inter-rating-1]`, `[inter-rating-2]`, `[inter-rating-3]`
   - Annotation IDs include the number for uniqueness: `inter_rater_{rater_id}_{number}_{qa_id}_{timestamp}`
   - Metadata includes `is_inter_rater=true`, `rater_id=<anon_id>`, `inter_rater_number=<N>`, `original_span_id=<phoenix_span>`
7. On success, the user's inter-rater cache is invalidated so counts update immediately

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
- **Session cache:** Per-user key `inter_rater_sessions_{anon_user_id}` with 60-second TTL
- **Stats cache:** Per-user key `stats_{anon_user_id}` with 10-second TTL
- Both caches invalidated immediately when user submits inter-rater feedback
- Cache validation: Cached sessions are validated against Phoenix to filter out deleted sessions
- Global cache clear available for significant Phoenix data changes

## Phoenix Notes
- POST annotations endpoint used: `/v1/span_annotations?sync=true`
- All inter-rater annotations are clearly separated by numbered name prefixes (`[inter-rating-1]`, `[inter-rating-2]`, etc.) and metadata
- Unique annotation IDs prevent overwrites when multiple raters rate the same session
- Headers include API key only; headers are redacted in logs
- Inter-rater counting uses GET endpoint: `/v1/projects/{project}/span_annotations` with async httpx for non-blocking queries

## Troubleshooting
- **No sessions available**:
  - Verify inter-rater is enabled in corpus manifest (`backend/corpus/manifest.json`)
  - Check `PHOENIX_PROJECT_NAME` is set correctly in your .env file
  - Ensure initial feedback with **user_id** exists in Phoenix annotations
  - Verify user is authenticated (Cognito JWT token present)
- **User sees own ratings**:
  - Fixed: Frontend now sends Authorization headers with all feedback submissions
  - Ensure user_id is properly captured during original feedback submission
- **Missing evaluation fields**:
  - Fixed: All 9 fields including User Type are now stored in Phoenix
- **Duplicate rating prevented**: Backend checks if the same rater already rated the same original span
- **Count not updating immediately**: Cache invalidation happens after submission (handled in backend)
- **Configuration not loading**:
  - The inter-rater service reloads config from manifest after corpus builds
  - To manually reload, rebuild the corpus or restart the backend server

## Recent Fixes

### 2026-02 (February)
- ✅ **Manifest-Based Configuration**: Inter-rater settings moved from .env files to corpus manifest (`backend/corpus/manifest.json`)
- ✅ **Corpus Wizard Integration**: Inter-rater configuration can now be set during corpus build via the Corpus Wizard UI
- ✅ **Environment Variable Cleanup**: Removed `INTER_RATER_ENABLED`, `INTER_RATER_PROJECT`, `INTER_RATER_MAX_RATINGS`, and `INTER_RATER_SESSIONS_PER_USER` from all .env files
- ✅ **Auto-Reload**: Inter-rater service automatically reloads configuration after corpus builds

### 2026-01 (January)
- ✅ **Numbered Annotations**: Inter-rater annotations now show as `[inter-rating-1]`, `[inter-rating-2]`, `[inter-rating-3]` instead of generic `[Inter-rater]` (GitHub issue #43)
- ✅ **Async Event Loop Fix**: Converted `submit_span_annotation()` to async to fix `inter_rater_number` determination in FastAPI's running event loop
- ✅ **Unique Annotation IDs**: Include `inter_rater_number` in annotation IDs to prevent overwrites when multiple raters rate the same session

### 2025-08 (August)
- ✅ **Authentication Bug**: Fixed frontend components to send Authorization headers with feedback
- ✅ **User Type Field**: Added missing User Type annotation to Phoenix feedback processing
- ✅ **Session Filtering**: Only sessions with existing feedback annotations are allocated for inter-rating
- ✅ **Anonymous ID Logging**: Enhanced logging for debugging while maintaining privacy
- ✅ **Filter Loading**: Fixed New Session button to properly reload dynamic filters


