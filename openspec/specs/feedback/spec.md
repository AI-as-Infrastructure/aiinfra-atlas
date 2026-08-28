# feedback Specification

## Purpose
TBD - created by archiving change add-seed-questions-for-inter-rater. Update Purpose after archive.

## Requirements

### Requirement: Inter-Rater Eligibility Without Baseline Feedback
The system SHALL surface spans for inter-rating regardless of whether they have baseline ("original") feedback. Seeded sessions created for focus group testing have no baseline feedback by design — all ratings come from inter-rater participants, who are treated symmetrically.

#### Scenario: Span without any feedback is eligible
- **GIVEN** a span exists in Phoenix with a valid `qa_id` but no feedback annotations
- **WHEN** the inter-rater service queries Phoenix for available sessions
- **THEN** the span SHALL be included in the result set
- **AND** the per-user allocation logic SHALL treat it the same as a span with baseline feedback

#### Scenario: Span without feedback is consumed without error
- **GIVEN** a span with no `original_feedback` is returned to the frontend
- **WHEN** the inter-rater playback view renders the session
- **THEN** the view SHALL render without referencing any baseline feedback fields
- **AND** the user SHALL be able to submit a rating against the session

#### Scenario: First rating on a seeded span is tagged as inter-rater
- **GIVEN** a seeded span with no prior feedback
- **WHEN** the first participant submits a rating via the inter-rater dashboard
- **THEN** the annotation SHALL be tagged `is_inter_rater: true` with `inter_rater_number: 1`
- **AND** no annotation SHALL be tagged `feedback_type: original` for that span

### Requirement: Seed Question Ingestion
The system SHALL provide a script that ingests a JSON file of questions through the live RAG pipeline to produce ratable sessions in Phoenix.

#### Scenario: Seeding a question produces both LLM and references spans
- **GIVEN** `data/seed_questions.json` contains a question with corpus filters
- **WHEN** the seeding script POSTs the question to `localhost:8000/api/ask/stream` and drains the SSE stream to completion
- **THEN** Phoenix SHALL contain an LLM span for the resulting `qa_id`
- **AND** Phoenix SHALL contain a `com.atlas.rag.references` span with the same `qa_id` containing the retrieved citations
- **AND** the seeded session SHALL be discoverable via the inter-rater sessions endpoint

#### Scenario: Seed pool sizing check is reported at startup
- **GIVEN** the seeding script is invoked with a JSON file of N questions
- **WHEN** the script starts up
- **THEN** the script SHALL read `INTER_RATER_MAX_RATINGS` from the environment
- **AND** print a sizing message indicating the maximum supported total ratings is N × `MAX_RATINGS`
- **AND** the operator SHALL be able to abort before submission if the pool is undersized

#### Scenario: Seeding is additive
- **GIVEN** Phoenix already contains seeded sessions from a previous run
- **WHEN** the seeding script is run again
- **THEN** previously seeded sessions SHALL remain unchanged
- **AND** new sessions SHALL be added alongside them

### Requirement: Feedback Form Evaluation Rubric
**MODIFIED** — replaces the legacy general-purpose Likert categories with a domain-specific HASS historical research evaluation rubric.

The extended feedback form (standard and inter-rater variants) SHALL present exactly six Likert scale categories rated 1 (very poor) to 5 (very good), in the following order:

1. **Corpus Fidelity** — i.e. are all claims about what the Hansard records contain supported by a Hansard citation?
2. **Citation Quality** — i.e. does each citation support the specific claim it is attached to?
3. **Relevance** — i.e. does the LLM answer actually address the question asked, without padding or drift?
4. **Coherence** — i.e. to what extent is the LLM answer well-reasoned and argued?
5. **Uncertainty** — i.e. to what extent does the LLM answer flag contested interpretations, gaps, or ambiguity?
6. **Historical Contextualisation** — i.e. to what extent does the LLM answer contextualise the primary material with additional knowledge?

Each category SHALL display the tooltip definition above as a hoverable ⓘ icon adjacent to the label.

The Likert scale for each category SHALL display endpoint labels: "1 (very poor)" below the 1 option and "5 (very good)" below the 5 option.

Each category SHALL show a free-text rationale field with placeholder "Free text rationale (for extreme ratings only):" when a rating is selected. The field SHALL be required (blocking form submission) for ratings of 1, 2, or 5.

#### Scenario: Six domain-specific categories displayed
- **GIVEN** a user opens the extended feedback form
- **WHEN** the Likert rubric section renders
- **THEN** exactly 6 categories SHALL appear: Corpus Fidelity, Citation Quality, Relevance, Coherence, Uncertainty, Historical Contextualisation
- **AND** no legacy categories (Factual Accuracy, Analysis Quality, Difficulty, Clarity) SHALL appear

#### Scenario: Endpoint labels visible
- **GIVEN** any Likert scale row in the rubric
- **WHEN** the user views the scale
- **THEN** the label "1 (very poor)" SHALL appear at the low end and "5 (very good)" at the high end

#### Scenario: Extreme rating requires rationale
- **GIVEN** a user selects a rating of 1, 2, or 5 for any category
- **WHEN** the rationale textarea appears
- **THEN** the placeholder SHALL read "Free text rationale (for extreme ratings only):"
- **AND** the form submit button SHALL remain disabled until the rationale field is non-empty

### Requirement: Feedback Form Fault Tags
**MODIFIED** — renames the "Inappropriate" fault tag and adds tooltip definitions to both fault tags.

The faults section SHALL contain exactly two optional checkboxes:

1. **Hallucination** — e.g. invented facts in the answer or false attributions of content to a source
2. **Harmful handling** — i.e. the LLM adopts or endorses prejudices contained in the Hansard records in its own analytical voice, or introduces stereotyping/derogatory framing not present in the cited material

Each fault label SHALL display the tooltip definition above as a hoverable ⓘ icon adjacent to the label.

A global fault rationale textarea SHALL appear below the faults grid with label "Free text rationale (only required if hallucination or harmful handling present):". This field SHALL be required (blocking form submission) when either fault checkbox is checked.

The backend field key for the renamed fault SHALL be `harmful_handling` (within the `faults` dict).

#### Scenario: Fault rationale required when fault checked
- **GIVEN** a user checks either the Hallucination or Harmful Handling checkbox
- **WHEN** the fault rationale textarea is empty
- **THEN** form submission SHALL be blocked
- **AND** a validation message SHALL be shown

#### Scenario: No fault rationale required when no fault checked
- **GIVEN** a user has not checked any fault checkbox
- **WHEN** the user attempts to submit
- **THEN** the fault rationale field SHALL NOT block submission

### Requirement: Feedback Form Header Instructions
**MODIFIED** — replaces the generic rating instructions with research-specific instructional copy.

The header of the extended feedback form (before the rubric) SHALL display:

> *Please provide an independent evaluation of this LLM response.*
>
> *For each of the following points, rate the LLM response on a scale of 1 (very poor) to 5 (very good). For ratings that are 1, 2, or 5, please provide a one sentence rationale.*

Between the rubric and the fault tags section, the form SHALL display:

> Finally, please note that if you identified any of the following faults in the LLM answer. If a fault is identified please provide a one sentence explanation.

#### Scenario: Instructions visible before rubric
- **GIVEN** a user opens the extended feedback form
- **WHEN** the form renders
- **THEN** the two-paragraph italic instruction SHALL appear above the first Likert scale category
- **AND** the inter-section instruction SHALL appear between the last category and the fault checkboxes

### Requirement: Feedback Form Field Scope
The feedback form (standard and inter-rater variants) SHALL collect only the fields required by the current evaluation protocol. User-type classification and the Off-topic and Bias fault categories are excluded.

#### Scenario: Standard form submits without user_type
- **GIVEN** a user completes the standard feedback form (`ExtendedFeedback.vue`)
- **WHEN** the form is submitted
- **THEN** the payload SHALL NOT include a `user_type` field
- **AND** the submission SHALL succeed without validation errors

#### Scenario: Inter-rater form submits without user_type
- **GIVEN** a participant completes the inter-rater feedback form (`InterRaterPlayback.vue`)
- **WHEN** the form is submitted
- **THEN** the payload SHALL NOT include a `user_type` field
- **AND** the submission SHALL succeed without validation errors

#### Scenario: Faults section contains only Hallucination and Inappropriate
- **GIVEN** either feedback form is rendered
- **WHEN** the Faults section is displayed
- **THEN** ONLY the Hallucination and Inappropriate checkboxes SHALL be present
- **AND** Off-topic and Bias checkboxes SHALL NOT appear

#### Scenario: Fault payload omits off_topic and bias
- **GIVEN** a user selects one or more faults and submits
- **WHEN** the faults object is constructed for submission
- **THEN** the object SHALL contain only `hallucination` and `inappropriate` keys
- **AND** `off_topic` and `bias` keys SHALL NOT be present
