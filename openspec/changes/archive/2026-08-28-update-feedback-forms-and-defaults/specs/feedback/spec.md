# feedback (delta)

## ADDED Requirements

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
