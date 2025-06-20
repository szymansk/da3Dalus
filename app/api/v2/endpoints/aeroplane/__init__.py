# Import and re-export the router from the individual endpoint files
from fastapi import APIRouter

# Create a single router that combines all the aeroplane-related endpoints
router = APIRouter()

# Import and include the routers from the individual endpoint files
from .base import router as base_router
from .wings import router as wings_router
from .fuselages import router as fuselages_router

# Include the routers
router.include_router(base_router)
router.include_router(wings_router)
router.include_router(fuselages_router)