# feedback (delta)

## ADDED Requirements

### Requirement: Tooltip Rendering Mechanism
The ⓘ tooltips required by "Feedback Form Evaluation Rubric" and "Feedback Form
Fault Tags" SHALL be rendered by the application rather than delegated to the
browser's native `title` attribute behaviour, so that their appearance on hover
is determined by the application and can be verified.

The tooltip SHALL appear on hover in every supported browser, SHALL present its
full definition text without truncation, and SHALL remain within the viewport.

The hover target SHALL be large enough to acquire without precision pointing,
and SHALL be at least 16×16 CSS pixels.

#### Scenario: Definitions appear on hover in Chrome
- **GIVEN** a reviewer viewing the extended feedback form in Chrome
- **WHEN** the pointer hovers the ⓘ icon beside a rubric category
- **THEN** that category's definition SHALL be displayed
- **AND** the definition SHALL match the text specified in "Feedback Form Evaluation Rubric"

#### Scenario: Definitions appear on hover in every supported browser
- **GIVEN** a reviewer viewing the extended feedback form
- **WHEN** the pointer hovers any rubric or fault ⓘ icon in Chrome, Firefox or Safari
- **THEN** the corresponding definition SHALL be displayed in each browser

#### Scenario: Tooltip is not clipped at the viewport edge
- **GIVEN** an ⓘ icon positioned near an edge of the viewport
- **WHEN** its tooltip is displayed
- **THEN** the full definition text SHALL remain visible within the viewport

#### Scenario: Native title attribute is not the display mechanism
- **GIVEN** the rendered feedback form
- **WHEN** a rubric or fault ⓘ element is inspected
- **THEN** its definition SHALL NOT depend on a `title` attribute for display
