# The following endpoints are removed since we'll use Phoenix Arize for data export
# @router.get("/diagnostics/span", response_model=Dict[str, Any])
# async def span_registry_diagnostics(session_id: Optional[str] = None, qa_id: Optional[str] = None):
#     """
#     Diagnostic endpoint for span registry status.
#     Used for testing the Redis connection and span registry functionality.
#     """
#     # This endpoint is no longer needed since we use Phoenix Arize for data export
#     pass
# 
# @router.get("/diagnostics/session/{session_id}/spans", response_model=Dict[str, Any])
# async def get_session_spans(session_id: str):
#     """
#     Get all spans associated with a specific session.
#     This endpoint allows analysis of telemetry data on a per-session basis.
#     """
#     # This endpoint is no longer needed since we use Phoenix Arize for data export
#     pass 