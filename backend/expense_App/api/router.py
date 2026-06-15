from fastapi import APIRouter

from expense_App.api.v1.router import router as v1_router
from expense_App.config import settings


api_router = APIRouter()
api_router.include_router(v1_router, prefix=settings.api_v1_prefix)
