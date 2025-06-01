import os

from aerosandbox import FuselageXSec

from app.models import AeroplaneModel
from app.schemas import AeroplaneSchema


async def aeroplaneModelToAeroplaneSchema(plane: AeroplaneModel) -> AeroplaneSchema:
    plane_dict = plane.__dict__.copy()
    plane_dict["wings"] = {w.name: w for w in plane.wings}
    plane_dict["fuselages"] = {f.name: f for f in plane.fuselages}
    plane_schema: AeroplaneSchema = AeroplaneSchema.model_validate(plane_dict)
    return plane_schema

async def aeroplaneSchemaToAsbAirplane(plane_schema: AeroplaneSchema) -> "asb.Airplane":
    """
    Convert an AeroplaneSchema to an Aerosandbox Airplane object.

    Args:
        plane_schema (AeroplaneSchema): The schema to convert.

    Returns:
        asb.Airplane: The converted Aerosandbox Airplane object.
    """
    from aerosandbox import Airplane, Wing, WingXSec, Airfoil, ControlSurface, Fuselage
    asb_airplane: Airplane = Airplane(
        name=plane_schema.name,
        wings=[
            Wing(
                name=wing_name,
                symmetric=wing.symmetric,
                xsecs=[
                    WingXSec(
                        xyz_le=None,
                        chord=x_sec.chord,
                        twist=x_sec.twist,
                        airfoil=Airfoil(
                            name=os.path.abspath(x_sec.airfoil) if not os.path.isabs(
                                x_sec.airfoil) else x_sec.airfoil,
                        ),
                        control_surface=[
                            ControlSurface(
                                name=x_sec.control_surface.name,
                                hinge_point=x_sec.control_surface.hinge_point,
                                symmetric=x_sec.control_surface.symmetric,
                                deflection=x_sec.control_surface.deflection
                            )] if x_sec.control_surface else None
                    ).translate(x_sec.xyz_le) for x_sec in wing.x_secs
                ] if wing.x_secs else None
            ) for wing_name, wing in plane_schema.wings.items()] if plane_schema.wings else None,
        fuselages=[
            Fuselage(
                name=fuselage_name,
                xsecs=[
                    FuselageXSec(
                        xyz_c=None,
                        xyz_normal=None, #TODO: Implement normal vector handling
                        radius=None,
                        height=x_sec.a,
                        width=x_sec.b,
                        shape=x_sec.n
                    ).translate(x_sec.xyz)
                    for x_sec in fuselage.x_secs
                ] if fuselage.x_secs else None,
            ) for fuselage_name, fuselage in plane_schema.fuselages.items()
        ] if plane_schema.fuselages else None,
        xyz_ref=plane_schema.xyz_ref
    )

    return asb_airplane