# Wizard UI Specification

## MODIFIED Requirements

### Requirement: Wizard Visual Consistency
The Corpus Wizard UI SHALL match the minimalist design language of the main application, using a monochrome color palette.

#### Scenario: Monochrome color scheme applied
- **WHEN** the Corpus Wizard is displayed
- **THEN** all UI elements SHALL use only black (#000), white (#fff), and gray (#888, #eee, #f5f5f5) colors
- **AND** no blue (#3498db), green (#4caf50), or red (#e74c3c) colors SHALL appear

#### Scenario: Primary buttons use black styling
- **WHEN** a primary action button is displayed
- **THEN** it SHALL have `background: #000; color: #fff; border-radius: 2px;`
- **AND** on hover it SHALL have `background: #888;`

#### Scenario: Secondary buttons use outlined styling
- **WHEN** a secondary action button is displayed
- **THEN** it SHALL have `background: #fff; color: #000; border: 1px solid #000;`

#### Scenario: Active/selected states use black border
- **WHEN** a card or selection element is active/selected
- **THEN** it SHALL have a black border instead of colored border
- **AND** the background SHALL be light gray (#f5f5f5) instead of colored tint

#### Scenario: Step indicators use monochrome styling
- **WHEN** the step progress indicator is displayed
- **THEN** active step SHALL be black filled circle
- **AND** completed step SHALL be black outline with checkmark
- **AND** pending step SHALL be gray outline

### Requirement: Directory Input Field
The source directory input field SHALL have no default placeholder value and SHALL provide path format guidance.

#### Scenario: No default placeholder
- **WHEN** the directory input field is displayed
- **THEN** it SHALL NOT have a pre-filled default value like `/path/to/corpus/files`
- **AND** the placeholder SHALL be empty or a simple prompt

#### Scenario: Path format hint displayed
- **WHEN** the directory input field is displayed
- **THEN** a hint text SHALL appear below the field
- **AND** the hint SHALL indicate format for relative paths (./data) and absolute paths (/home/user/data)

### Requirement: Font Consistency
The Corpus Wizard SHALL use the same typography as the main application.

#### Scenario: Times New Roman font applied
- **WHEN** the Corpus Wizard is displayed
- **THEN** all text SHALL use the Times New Roman serif font family consistent with the main UI
