# Metadata Collection

## MODIFIED Requirements

### Requirement: Simplified Metadata Fields
The metadata step SHALL collect only essential corpus information.

#### Scenario: User enters metadata
GIVEN the user is on the metadata step
WHEN viewing the form
THEN only these fields SHALL be present:
- Title (required)
- Description (optional)
- Copyright status (required)
- DOI (optional)
AND no additional complex fields SHALL be shown

### Requirement: Copyright Status Options
The metadata step SHALL provide standard copyright status options.

#### Scenario: User selects copyright status
GIVEN the user is entering metadata
WHEN selecting copyright status
THEN standard options SHALL be available:
- Public Domain
- Creative Commons variants (BY, BY-SA, BY-NC)
- Proprietary/Licensed
- Mixed
AND the selection SHALL be required

## REMOVED Requirements

### Requirement: Complex Metadata Fields
The following metadata fields SHALL be removed from the initial configuration:
- Time period from/to
- Material type
- People/entities
- Locations
- Additional metadata

#### Scenario: Simplified metadata entry
GIVEN the user is configuring a new corpus
WHEN entering metadata
THEN no complex relationship fields SHALL be present
AND configuration SHALL focus on essential identification only