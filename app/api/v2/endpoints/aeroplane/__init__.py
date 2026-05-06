# Import and re-export the router from the individual endpoint files
from fastapi import APIRouter

# Create a single router that combines all the aeroplane-related endpoints
router = APIRouter()

# Import and include the routers from the individual endpoint files
from .base import router as base_router
from .wings import router as wings_router
from .fuselages import router as fuselages_router
from .mission_objectives import router as mission_objectives_router
from .weight_items import router as weight_items_router
from .copilot_history import router as copilot_history_router
from .design_versions import router as design_versions_router
from .powertrain_sizing import router as powertrain_sizing_router
from .avl_geometry import router as avl_geometry_router
from .design_assumptions import router as design_assumptions_router

# Include the routers
router.include_router(base_router)
router.include_router(wings_router)
router.include_router(fuselages_router)
router.include_router(mission_objectives_router)
router.include_router(weight_items_router)
router.include_router(copilot_history_router)
router.include_router(design_versions_router)
router.include_router(powertrain_sizing_router)
router.include_router(avl_geometry_router)
router.include_router(design_assumptions_router)
