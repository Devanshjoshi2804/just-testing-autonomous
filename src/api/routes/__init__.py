"""
API Routes package
"""

from src.api.routes.documents import router as documents_router
from src.api.routes.tests import router as tests_router
from src.api.routes.metrics import router as metrics_router
from src.api.routes.intelligence import router as intelligence_router

__all__ = ["documents_router", "tests_router", "metrics_router", "intelligence_router"]
