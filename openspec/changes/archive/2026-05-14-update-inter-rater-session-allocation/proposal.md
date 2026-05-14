# Change: Update inter-rater session allocation for 100-prompt study

## Why
The inter-rater reliability study requires 100 preloaded prompts, 15 participants each completing 20 ratings, with no more than 3 ratings per session. The current configuration allocates only 10 sessions per user, requiring multiple cache refresh cycles to reach 20.

## What Changes
- Update `INTER_RATER_SESSIONS_PER_USER` from 10 to 20 in all environment configs
- No algorithmic changes needed — the existing SHA-256 allocation with max_ratings=3 cap is self-balancing

## Impact
- Affected specs: inter-rater allocation (new)
- Affected code: `config/.env.template`, `config/.env.staging`, `config/.env.production`
- Math: 100 prompts x 3 ratings = 300 total = 15 users x 20 ratings
