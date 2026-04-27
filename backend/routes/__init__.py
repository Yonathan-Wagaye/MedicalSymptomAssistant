from fastapi import APIRouter

from backend.routes.feedback import router as feedback_router
from backend.routes.health import router as health_router
from backend.routes.query import router as query_router
from backend.routes.sessions import router as sessions_router
from backend.routes.system import router as system_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(system_router)
api_router.include_router(sessions_router)
api_router.include_router(query_router)
api_router.include_router(feedback_router)
