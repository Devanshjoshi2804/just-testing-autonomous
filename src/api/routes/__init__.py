"""
API Routes package
"""

from src.api.routes.documents import router as documents_router
from src.api.routes.tests import router as tests_router

__all__ = ["documents_router", "tests_router"]
