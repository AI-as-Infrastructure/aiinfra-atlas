"""
ATLAS API Routers.

This package contains FastAPI routers for different API endpoint groups.
"""

from backend.routers.core import router as core_router
from backend.routers.query import router as query_router
from backend.routers.feedback import router as feedback_router
from backend.routers.validation import router as validation_router
from backend.routers.cache import router as cache_router
from backend.routers.queue import router as queue_router
from backend.routers.inter_rater import router as inter_rater_router
from backend.routers.retriever import router as retriever_router

__all__ = [
    "core_router",
    "query_router",
    "feedback_router",
    "validation_router",
    "cache_router",
    "queue_router",
    "inter_rater_router",
    "retriever_router",
]
