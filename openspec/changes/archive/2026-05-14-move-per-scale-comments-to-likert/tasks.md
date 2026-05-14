# Tasks: Move Per-Scale Comments to Likert

## 1. Backend data model
- [x] 1.1 Add 6 per-scale comment fields to UserFeedback in `backend/telemetry/feedback.py`

## 2. Backend annotation creation
- [x] 2.1 Add per-scale comment annotation blocks in `backend/telemetry/feedback.py`

## 3. Feedback API
- [x] 3.1 Pass 6 new fields into feedback_data in `backend/telemetry/api.py`

## 4. ExtendedFeedback.vue
- [x] 4.1 Add conditional textarea beneath each Likert scale
- [x] 4.2 Add `scaleComments` data and `isCommentRequired()` method
- [x] 4.3 Update `hasExtendedFeedback` validation
- [x] 4.4 Include per-scale comments in submit payload
- [x] 4.5 Remove bottom "Additional Comments" section
- [x] 4.6 Add CSS styles

## 5. InterRaterPlayback.vue
- [x] 5.1 Add conditional textarea beneath each Likert scale
- [x] 5.2 Add `scaleComments` to feedback ref
- [x] 5.3 Add `isCommentRequired` function and update `isFormValid`
- [x] 5.4 Include per-scale comments in submit payload
- [x] 5.5 Remove "Additional Comments" section
- [x] 5.6 Add CSS styles

## 6. Validation
- [ ] 6.1 Verify ExtendedFeedback form: rating 1/2/5 requires comment, 3/4 optional
- [ ] 6.2 Verify InterRaterPlayback form: same validation
- [ ] 6.3 Verify per-scale comment annotations appear in Phoenix
