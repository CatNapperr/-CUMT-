from fastapi import APIRouter
from app.api.v1 import health
from app.api.v1 import users
from app.api.v1 import meals
from app.api.v1 import media
from app.api.v1 import summary
from app.api.v1 import analytics

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(users.router)
api_router.include_router(meals.router)
api_router.include_router(media.router)
api_router.include_router(summary.router)
api_router.include_router(analytics.router)