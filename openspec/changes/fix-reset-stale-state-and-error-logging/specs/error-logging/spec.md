## MODIFIED Requirements

### Requirement: Streaming Error Logging MUST Include Full Traceback

All streaming error log statements in `response.py` MUST include `exc_info=True` to capture the full Python traceback. Both the telemetry-enabled and non-telemetry code paths MUST log tracebacks consistently.

#### Scenario: Non-telemetry streaming error includes traceback

- **GIVEN** a streaming error occurs on the non-telemetry code path at `response.py:138`
- **WHEN** the error is logged
- **THEN** the log entry MUST include the full Python traceback via `exc_info=True`
- **AND** the log format MUST match the telemetry-enabled path at `response.py:335`
