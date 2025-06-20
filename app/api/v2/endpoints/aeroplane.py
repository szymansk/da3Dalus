# This file is kept for backward compatibility
# It creates a new router and includes the routers from the aeroplane package
from fastapi import APIRouter
from app.api.v2.endpoints.aeroplane.base import router as base_router
from app.api.v2.endpoints.aeroplane.wings import router as wings_router
from app.api.v2.endpoints.aeroplane.fuselages import router as fuselages_router

router = APIRouter()
router.include_router(base_router)
router.include_router(wings_router)
router.include_router(fuselages_router)
