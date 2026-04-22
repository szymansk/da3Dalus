from sqlalchemy.orm import joinedload

from app.converters.model_schema_converters import aeroplane_model_to_aeroplane_schema_async
from app.db.exceptions import NotFoundInDbException
from app.models import AeroplaneModel, WingModel, WingXSecModel
from app.models.aeroplanemodel import (
    FuselageModel,
    WingXSecDetailModel,
    WingXSecTrailingEdgeDeviceModel,
)
from app.schemas import AeroplaneSchema, AsbWingSchema


async def get_aeroplane_by_id(aeroplane_id, db) -> AeroplaneSchema:
    plane: AeroplaneModel = (
        db.query(AeroplaneModel)
        .options(
            joinedload(AeroplaneModel.wings)
            .joinedload(WingModel.x_secs)
            .joinedload(WingXSecModel.detail)
            .joinedload(WingXSecDetailModel.spares)
        )
        .options(
            joinedload(AeroplaneModel.wings)
            .joinedload(WingModel.x_secs)
            .joinedload(WingXSecModel.detail)
            .joinedload(WingXSecDetailModel.trailing_edge_device)
            .joinedload(WingXSecTrailingEdgeDeviceModel.servo_data)
        )
        .options(joinedload(AeroplaneModel.fuselages).joinedload(FuselageModel.x_secs))
        .filter(AeroplaneModel.uuid == aeroplane_id)
        .first()
    )
    if not plane:
        raise NotFoundInDbException(f"Aeroplane with the given ID ({aeroplane_id}) not found.")
    plane_schema: AeroplaneSchema = aeroplane_model_to_aeroplane_schema_async(plane)
    return plane_schema


async def get_wing_by_name_and_aeroplane_id(aeroplane_id, wing_name, db):
    # Load the parent aeroplane
    plane_schema = await get_aeroplane_by_id(aeroplane_id, db)
    # Find the wing belonging to this aeroplane
    wing: AsbWingSchema = next(
        (w for w in plane_schema.wings.values() if w.name == wing_name), None
    )
    if not wing:
        raise NotFoundInDbException(f"Wing '{wing_name}' not found")
    return plane_schema
