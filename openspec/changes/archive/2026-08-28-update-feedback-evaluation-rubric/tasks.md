# Tasks: Update Feedback Evaluation Rubric

## Prerequisites
- [x] Confirm current categories in `ExtendedFeedback.vue` and `InterRaterPlayback.vue`
- [x] Confirm `inappropriate` fault is the only fault to rename (off_topic/bias already removed)
- [x] Confirm no other components reference old category keys directly

## Phase 1: Backend — `backend/telemetry/feedback.py`

- [ ] **Task 1.1**: Add new Likert fields to `UserFeedback` model: `citation_quality`, `coherence`, `uncertainty`, `historical_contextualisation` (all `Optional[int] = None`)
- [ ] **Task 1.2**: Add per-scale comment fields: `citation_quality_comments`, `coherence_comments`, `uncertainty_comments`, `historical_contextualisation_comments` (all `Optional[str] = None`)
- [ ] **Task 1.3**: Add `faults_rationale: Optional[str] = None` to `UserFeedback` model
- [ ] **Task 1.4**: Add description functions: `get_citation_quality_description`, `get_coherence_description`, `get_uncertainty_description`, `get_historical_contextualisation_description`

## Phase 2: Standard Feedback Form — `frontend/src/components/ExtendedFeedback.vue`

### Template
- [ ] **Task 2.1**: Update header subtitle to new italic instruction text (two-paragraph format)
- [ ] **Task 2.2**: Replace "Factual Accuracy" section with "Citation Quality" (`citation_quality`); set new tooltip
- [ ] **Task 2.3**: Update "Corpus Fidelity" tooltip to domain-specific definition
- [ ] **Task 2.4**: Replace "Analysis Quality" section with "Coherence" (`coherence`); set new tooltip
- [ ] **Task 2.5**: Update "Relevance" tooltip to domain-specific definition
- [ ] **Task 2.6**: Replace "Difficulty" section with "Uncertainty" (`uncertainty`); set new tooltip
- [ ] **Task 2.7**: Replace "Clarity" section with "Historical Contextualisation" (`historical_contextualisation`); set new tooltip
- [ ] **Task 2.8**: Add Likert scale endpoint labels ("1 (very poor)" / "5 (very good)") to all 6 scale rows
- [ ] **Task 2.9**: Update per-scale comment placeholder to "Free text rationale (for extreme ratings only):"
- [ ] **Task 2.10**: Add instruction paragraph before faults section
- [ ] **Task 2.11**: Rename `inappropriate` fault → `harmful_handling`; update label and add tooltip
- [ ] **Task 2.12**: Add tooltip to Hallucination fault label
- [ ] **Task 2.13**: Add global fault rationale textarea with required validation

### Script
- [ ] **Task 2.14**: Update `ratings` data object keys (remove old 4, add new 4)
- [ ] **Task 2.15**: Update `faults` data object: rename `inappropriate` → `harmful_handling`
- [ ] **Task 2.16**: Update `scaleComments` data object keys
- [ ] **Task 2.17**: Add `faultRationale: ''` to data
- [ ] **Task 2.18**: Update `hasExtendedFeedback` computed to block if fault rationale required but missing
- [ ] **Task 2.19**: Update `submitExtendedFeedback` payload construction (new field names, faultRationale)
- [ ] **Task 2.20**: Update `resetForm` to use new field names

## Phase 3: Inter-Rater Form — `frontend/src/components/InterRaterPlayback.vue`

Apply equivalent changes to the self-contained inter-rater form:

### Template
- [ ] **Task 3.1**: Update header subtitle to new italic instruction text
- [ ] **Task 3.2**: Replace "Factual Accuracy" section with "Citation Quality"; set new tooltip
- [ ] **Task 3.3**: Update "Corpus Fidelity" tooltip
- [ ] **Task 3.4**: Replace "Analysis Quality" section with "Coherence"; set new tooltip
- [ ] **Task 3.5**: Update "Relevance" tooltip
- [ ] **Task 3.6**: Replace "Difficulty" section with "Uncertainty"; set new tooltip
- [ ] **Task 3.7**: Replace "Clarity" section with "Historical Contextualisation"; set new tooltip
- [ ] **Task 3.8**: Add Likert scale endpoint labels to all 6 scale rows
- [ ] **Task 3.9**: Update per-scale comment placeholder
- [ ] **Task 3.10**: Add instruction paragraph before faults section
- [ ] **Task 3.11**: Rename `inappropriate` → `harmful_handling` fault; update label and add tooltip
- [ ] **Task 3.12**: Add tooltip to Hallucination fault label
- [ ] **Task 3.13**: Add global fault rationale textarea

### Script
- [ ] **Task 3.14**: Update `feedback` reactive object keys (ratings, scaleComments, faults)
- [ ] **Task 3.15**: Add `faultRationale` field
- [ ] **Task 3.16**: Update `isCommentRequired` scale list
- [ ] **Task 3.17**: Update `hasAllRequiredRatings` / submit validation for fault rationale
- [ ] **Task 3.18**: Update submit payload construction
- [ ] **Task 3.19**: Update reset logic

## Verification

```bash
# Confirm old category keys removed from both components
grep -n "factual_accuracy\|analysis_quality\|difficulty\|clarity" \
  frontend/src/components/ExtendedFeedback.vue \
  frontend/src/components/InterRaterPlayback.vue

# Confirm new category keys present
grep -n "citation_quality\|coherence\|uncertainty\|historical_contextualisation" \
  frontend/src/components/ExtendedFeedback.vue \
  frontend/src/components/InterRaterPlayback.vue

# Confirm inappropriate renamed
grep -n "inappropriate" \
  frontend/src/components/ExtendedFeedback.vue \
  frontend/src/components/InterRaterPlayback.vue

# Confirm backend model updated
grep -n "citation_quality\|coherence\|uncertainty\|historical_contextualisation\|faults_rationale" \
  backend/telemetry/feedback.py
```
