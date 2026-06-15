from fastapi import APIRouter

from expense_App.api.v1.endpoints.auth import router as auth_router
from expense_App.api.v1.endpoints.groups import router as groups_router
from expense_App.api.v1.endpoints.health import router as health_router
from expense_App.api.v1.endpoints.imports import router as imports_router


router = APIRouter()
router.include_router(auth_router, prefix="/auth", tags=["Auth"])
router.include_router(groups_router, tags=["Groups"])
router.include_router(imports_router, prefix="/groups", tags=["Imports"])
router.include_router(health_router, prefix="/health", tags=["Health"])
