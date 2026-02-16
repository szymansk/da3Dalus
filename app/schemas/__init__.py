from app.schemas.aeroplaneschema import AeroplaneSchema
from app.schemas.aeroplaneschema import ControlSurfaceSchema
from app.schemas.aeroplaneschema import AsbWingSchema
from app.schemas.aeroplaneschema import WingXSecSchema
from app.schemas.aeroplaneschema import WingUnitsSchema
from app.schemas.aeroplaneschema import SpareDetailSchema
from app.schemas.aeroplaneschema import TrailingEdgeDeviceDetailSchema
from app.schemas.aeroplaneschema import FuselageSchema
from app.schemas.aeroplaneschema import FuselageXSecSuperEllipseSchema
from app.schemas.flight_profile import (
    AircraftFlightProfileAssignmentRead,
    RCFlightProfileCreate,
    RCFlightProfileRead,
    RCFlightProfileUpdate,
)
from app.schemas.api_responses import (
    CreateAeroplaneResponse,
    OperationStatusResponse,
    StaticUrlResponse,
    CadTaskAcceptedResponse,
    CadTaskStatusResponse,
    ZipAssetResponse,
)
