# Feedback Capability Spec Delta

## ADDED Requirements

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
