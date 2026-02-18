## ADDED Requirements

### Requirement: VITE_SITE_TITLE Build Integration
The corpus wizard build process SHALL correctly set `VITE_SITE_TITLE` in the environment file to match the corpus `display_name` from the manifest. Documentation SHALL note that a frontend restart is required for the title change to take effect.

#### Scenario: Site title reflects corpus display name after build
- **WHEN** a corpus build completes and the frontend is restarted
- **THEN** the site title displayed in the browser SHALL match the corpus `display_name`

#### Scenario: Title update requires frontend restart
- **WHEN** a corpus build updates `VITE_SITE_TITLE` in the `.env` file
- **THEN** the change SHALL NOT take effect until the frontend dev server or production build is restarted

### Requirement: Test Target Display Clarity
The Test Target UI box SHALL NOT display the redundant `MULTI_CORPUS_VECTORSTORE` label. The field SHALL either be hidden from display or replaced with a concise label.

#### Scenario: Multi Corpus Vectorstore label removed from Test Target box
- **WHEN** a user views the Test Target box in the sidebar
- **THEN** the `MULTI_CORPUS_VECTORSTORE` field SHALL NOT appear as a separate display row

### Requirement: Export Button Layout Consistency
The Export Config and Export Session buttons in the chat sidebar SHALL be displayed side by side with consistent styling. Both buttons SHALL use plain Bulma button classes without icons.

#### Scenario: Export buttons displayed side by side
- **WHEN** a user views the chat sidebar
- **THEN** the Export Config and Export Session buttons SHALL appear at the same level, side by side
- **AND** both buttons SHALL use the same Bulma `button is-link is-light` styling without icons
