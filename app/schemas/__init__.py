from app.schemas.aeroplaneschema import AeroplaneSchema
from app.schemas.aeroplaneschema import ControlSurfaceRole
from app.schemas.aeroplaneschema import ControlSurfaceSchema
from app.schemas.aeroplaneschema import ControlSurfacePatchSchema
from app.schemas.aeroplaneschema import ControlSurfaceCadDetailsSchema
from app.schemas.aeroplaneschema import ControlSurfaceCadDetailsPatchSchema
from app.schemas.aeroplaneschema import AsbWingSchema
from app.schemas.aeroplaneschema import AsbWingReadSchema
from app.schemas.aeroplaneschema import AsbWingGeometryWriteSchema
from app.schemas.aeroplaneschema import WingXSecSchema
from app.schemas.aeroplaneschema import WingXSecReadSchema
from app.schemas.aeroplaneschema import WingXSecGeometryWriteSchema
from app.schemas.aeroplaneschema import WingUnitsSchema
from app.schemas.aeroplaneschema import SpareDetailSchema
from app.schemas.aeroplaneschema import TrailingEdgeDeviceDetailSchema
from app.schemas.aeroplaneschema import TrailingEdgeDevicePatchSchema
from app.schemas.aeroplaneschema import TrailingEdgeServoSchema
from app.schemas.aeroplaneschema import TrailingEdgeServoPatchSchema
from app.schemas.aeroplaneschema import ControlSurfaceServoDetailsSchema
from app.schemas.aeroplaneschema import ControlSurfaceServoDetailsPatchSchema
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
    AirplaneConfigurationResponse,
)
from app.schemas.strip_forces import (
    StripForceEntry,
    SurfaceStripForces,
    StripForcesResponse,
)
