# Feedback Capability Spec Delta

## ADDED Requirements

### Requirement: Inter-Rater Annotation Numbering
The system SHALL number inter-rater annotations sequentially starting from 1 for each span.

#### Scenario: First inter-rater provides feedback
- **WHEN** the first inter-rater submits feedback for a span
- **THEN** the annotation name SHALL be prefixed with `[inter-rating-1]`

#### Scenario: Second inter-rater provides feedback
- **WHEN** a second inter-rater submits feedback for the same span
- **THEN** the annotation name SHALL be prefixed with `[inter-rating-2]`

#### Scenario: Third inter-rater provides feedback
- **WHEN** a third inter-rater submits feedback for the same span
- **THEN** the annotation name SHALL be prefixed with `[inter-rating-3]`

#### Scenario: Original feedback has no number
- **WHEN** original (non-inter-rater) feedback is submitted
- **THEN** the annotation name SHALL NOT have any inter-rating prefix
- **AND** SHALL use the base annotation name only

### Requirement: Inter-Rater Count Determination
The system SHALL determine the inter-rater number by querying existing inter-rater annotations for the span.

#### Scenario: No existing inter-rater annotations
- **WHEN** querying annotations for a span with no inter-rater feedback
- **THEN** the inter-rater count SHALL be 0
- **AND** the next inter-rater number SHALL be 1

#### Scenario: Existing inter-rater annotations present
- **WHEN** querying annotations for a span with existing inter-rater feedback
- **THEN** the inter-rater count SHALL equal the number of unique rater_ids with is_inter_rater=true
- **AND** the next inter-rater number SHALL be count + 1
