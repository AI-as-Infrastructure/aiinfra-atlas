"""
Feedback router — REMOVED (duplicate).

POST /api/feedback is served by the telemetry router (backend/telemetry/api.py).
This file previously contained a duplicate route that was never reached because
the telemetry router was registered first in app.py.

Kept as an empty module to avoid import errors in any stale references.
"""
