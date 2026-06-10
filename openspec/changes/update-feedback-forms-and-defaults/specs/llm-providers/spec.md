# llm-providers (delta)

## ADDED Requirements

### Requirement: OpenRouter Provider End-to-End Verified
The system SHALL support OpenRouter as a fully verified LLM provider, exercised through the complete RAG pipeline including streaming, telemetry, and feedback.

#### Scenario: OpenRouter provider routes through ChatOpenAI with correct base URL
- **GIVEN** `LLM_PROVIDER=OPENROUTER` is set in the active test target
- **AND** `OPENROUTER_API_KEY` is present in the environment
- **WHEN** the backend initialises the LLM client
- **THEN** the client SHALL use `ChatOpenAI` with `base_url` set to `https://openrouter.ai/api/v1` (or `OPENROUTER_BASE_URL` if overridden)
- **AND** the backend log SHALL record "Using OpenRouter with API key"

#### Scenario: Streamed response received end-to-end
- **GIVEN** the `k20_openrouter_claude_sonnet` test target is active
- **WHEN** a query is submitted via the frontend
- **THEN** a complete streamed response SHALL be received by the browser
- **AND** citations SHALL be returned alongside the response

#### Scenario: OpenRouter span recorded in Phoenix telemetry
- **GIVEN** a query is processed via the OpenRouter provider
- **WHEN** the resulting span is inspected in Phoenix
- **THEN** token counts SHALL be present
- **AND** no telemetry errors SHALL be logged
