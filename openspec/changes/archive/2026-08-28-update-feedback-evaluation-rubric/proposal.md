# Proposal: Update Feedback Evaluation Rubric

## Change ID
`update-feedback-evaluation-rubric`

## Summary
Replace the legacy 6-category Likert rubric in both feedback forms with a domain-specific set of evaluation criteria aligned to HASS historical research standards. Rename one fault tag, add tooltip definitions for all categories and tags, add endpoint labels to Likert scales, add a global fault rationale field, and update all instructional copy.

## Motivation

The current rubric (Factual Accuracy, Corpus Fidelity, Analysis Quality, Relevance, Difficulty, Clarity) was designed for general LLM evaluation. Following analysis of the focus-group run, the evaluation protocol has been refined to better target the specific quality dimensions relevant to historical RAG research. The new rubric:

- Eliminates the "Difficulty" category, which measures query complexity rather than response quality
- Replaces "Factual Accuracy" with "Citation Quality" to distinguish between the claim-level and citation-level dimensions of accuracy
- Replaces "Analysis Quality" with "Coherence" to focus on reasoning quality rather than a catch-all analysis label
- Replaces "Clarity" with "Historical Contextualisation" to capture whether the LLM contextualises primary material with appropriate scholarly knowledge
- Replaces "Uncertainty" as a new category to evaluate how well the LLM flags contested interpretations, gaps, and ambiguity
- Renames "Inappropriate" to "Harmful Handling" to more precisely describe the fault: the LLM endorsing or amplifying historical prejudices in its own analytical voice

## Scope

### In Scope
- Replace 4 Likert scale categories in `ExtendedFeedback.vue` and `InterRaterPlayback.vue`
- Update tooltips for all 6 categories and 2 fault tags in both components
- Add Likert scale endpoint labels ("1 (very poor)" / "5 (very good)") to all scales in both components
- Update per-scale comment placeholder to "Free text rationale (for extreme ratings only):"
- Rename `inappropriate` fault → `harmful_handling` in both components
- Add global fault rationale textarea (required when either fault checked) in both components
- Update header instruction text in both components
- Add instruction paragraph between rubric and faults section in both components
- Add new model fields to `backend/telemetry/feedback.py`
- Add description functions for new categories in `feedback.py`

### Out of Scope
- Removing old backend fields — old optional fields remain for backward compatibility with existing Phoenix annotations
- Changing the `SimpleFeedback.vue` or `AIEnhancedFeedback.vue` components
- Changing the API endpoint or response format
- Updating Phoenix annotation mapping logic (new fields flow through existing dynamic annotation construction)

## Current State

| Location | Current Value |
|---|---|
| `ExtendedFeedback.vue` categories | Factual Accuracy, Corpus Fidelity, Analysis Quality, Relevance, Difficulty, Clarity |
| `ExtendedFeedback.vue` faults | `hallucination`, `inappropriate` |
| `InterRaterPlayback.vue` categories | Same 6 categories (independent implementation) |
| `InterRaterPlayback.vue` faults | `hallucination`, `inappropriate` |
| Backend `UserFeedback` model | `factual_accuracy`, `analysis_quality`, `difficulty`, `clarity` fields; no `harmful_handling` |
| Scale endpoint labels | Numeric only (1–5) |
| Per-scale placeholder | "Please explain your rating (required)" / "Optional: explain your rating" |
| Header instructions | Generic rating instructions |
| Fault section | No instruction paragraph; no global rationale field |

## Proposed Changes

### Rubric categories (both forms)
| Old | New | Key |
|---|---|---|
| Factual Accuracy | Citation Quality | `citation_quality` |
| Corpus Fidelity | Corpus Fidelity | `corpus_fidelity` (updated tooltip) |
| Analysis Quality | Coherence | `coherence` |
| Relevance | Relevance | `relevance` (updated tooltip) |
| Difficulty | Uncertainty | `uncertainty` |
| Clarity | Historical Contextualisation | `historical_contextualisation` |

### Tooltip definitions
| Category | Tooltip |
|---|---|
| Corpus Fidelity | i.e. are all claims about what the Hansard records contain supported by a Hansard citation? |
| Citation Quality | i.e. does each citation support the specific claim it is attached to? |
| Relevance | i.e. does the LLM answer actually address the question asked, without padding or drift? |
| Coherence | i.e. to what extent is the LLM answer well-reasoned and argued? |
| Uncertainty | i.e. to what extent does the LLM answer flag contested interpretations, gaps, or ambiguity? |
| Historical Contextualisation | i.e. to what extent does the LLM answer contextualise the primary material with additional knowledge? |
| Hallucination | e.g. invented facts in the answer or false attributions of content to a source |
| Harmful Handling | i.e. the LLM adopts or endorses prejudices contained in the Hansard records in its own analytical voice, or introduces stereotyping/derogatory framing not present in the cited material |

### Instructional copy
**Top of form (before rubric):**
> *Please provide an independent evaluation of this LLM response.*
> *For each of the following points, rate the LLM response on a scale of 1 (very poor) to 5 (very good). For ratings that are 1, 2, or 5, please provide a one sentence rationale.*

**Between rubric and fault tags:**
> Finally, please note that if you identified any of the following faults in the LLM answer. If a fault is identified please provide a one sentence explanation.

### Fault rationale field
A single textarea below the faults grid with label "Free text rationale (only required if hallucination or harmful handling present):" — required when either fault is checked; blocks form submission if missing.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Old Phoenix annotations use old field names | Low | Low | Old annotations remain; new submissions use new names — no conflict |
| Inter-rater participants mid-session during deployment | Low | Low | Session reload picks up new form; per-scale comments backward compatible |
| `harmful_handling` key not recognised by existing annotation code | Low | Low | Annotation code iterates `faults` dict dynamically; new key flows through automatically |

## Acceptance Criteria
- [ ] 6 categories in both forms match new rubric exactly
- [ ] All category tooltips display correct domain-specific definitions
- [ ] Likert scales show "1 (very poor)" and "5 (very good)" endpoint labels
- [ ] Per-scale rationale placeholder reads "Free text rationale (for extreme ratings only):"
- [ ] Fault labels: "Hallucination" and "Harmful handling" with tooltips
- [ ] Global fault rationale textarea present; required when either fault checked
- [ ] Header instructions updated in both forms
- [ ] Fault section instruction paragraph present in both forms
- [ ] Backend `UserFeedback` model accepts new field names
- [ ] Feedback submission succeeds end-to-end on both standard and inter-rater paths
