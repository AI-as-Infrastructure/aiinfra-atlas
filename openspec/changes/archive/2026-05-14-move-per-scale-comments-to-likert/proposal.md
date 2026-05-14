# Change: Move free text to per-scale comments on feedback form

## Why
The single "Additional Comments" textarea at the bottom of the feedback form doesn't tie comments to specific Likert scales. Researchers need per-scale explanations, especially for extreme ratings (1, 2, or 5), to understand why raters gave those scores.

## What Changes
- Add a conditional free text field beneath each of the 6 Likert scales in ExtendedFeedback.vue and InterRaterPlayback.vue
- Free text appears only after a rating is selected
- Free text is mandatory when the Likert rating is 1, 2, or 5
- Remove the bottom "Additional Comments" textarea from both components
- Add 6 per-scale comment fields to the backend UserFeedback model
- Create per-scale Phoenix annotations for each comment

## Impact
- Affected specs: feedback (new)
- Affected code:
  - `backend/telemetry/feedback.py` — new fields on UserFeedback, new annotation blocks
  - `backend/telemetry/api.py` — pass new fields to feedback_data
  - `frontend/src/components/ExtendedFeedback.vue` — per-scale textareas, validation
  - `frontend/src/components/InterRaterPlayback.vue` — same changes
- **Not affected**: AIEnhancedFeedback.vue, SimpleFeedback.vue, InterRaterFeedback model (inherits)
- **Backward compatible**: existing `additional_comments` field kept on model, old submissions unaffected
