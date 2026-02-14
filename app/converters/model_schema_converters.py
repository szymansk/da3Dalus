import os
from typing import List

import aerosandbox as asb
from aerosandbox import FuselageXSec

from app import schemas
from app.models import AeroplaneModel, WingModel
from app.schemas import AeroplaneSchema
from cad_designer.airplane.aircraft_topology.wing import WingConfiguration


async def aeroplaneModelToAeroplaneSchema_async(plane: AeroplaneModel) -> AeroplaneSchema:
    plane_dict = plane.__dict__.copy()
    plane_dict["wings"] = {w.name: w for w in plane.wings}
    plane_dict["fuselages"] = {f.name: f for f in plane.fuselages}
    plane_schema: AeroplaneSchema = AeroplaneSchema.model_validate(plane_dict)
    return plane_schema


def _build_asb_airfoil(airfoil_ref) -> asb.Airfoil:
    airfoil_ref_str = str(airfoil_ref)
    absolute_ref = os.path.abspath(airfoil_ref_str) if not os.path.isabs(airfoil_ref_str) else airfoil_ref_str

    if os.path.isfile(absolute_ref):
        # If a local .dat path is available, load coordinates explicitly.
        return asb.Airfoil(
            name=os.path.splitext(os.path.basename(absolute_ref))[0],
            coordinates=absolute_ref,
        )

    # If this looks like a file path but the file is unavailable, try the stem as an airfoil name.
    airfoil_name_from_stem = os.path.splitext(os.path.basename(airfoil_ref_str))[0]
    if airfoil_name_from_stem and airfoil_name_from_stem != airfoil_ref_str:
        return asb.Airfoil(name=airfoil_name_from_stem)

    # Fall back to ASB name-based lookup (e.g. "naca2412", "sd7037", UIUC names).
    return asb.Airfoil(name=airfoil_ref_str)


async def aeroplaneSchemaToAsbAirplane_async(plane_schema: AeroplaneSchema) -> "asb.Airplane":
    """
    Convert an AeroplaneSchema to an Aerosandbox Airplane object.

    Args:
        plane_schema (AeroplaneSchema): The schema to convert.

    Returns:
        asb.Airplane: The converted Aerosandbox Airplane object.
    """
    from aerosandbox import Airplane, Wing, WingXSec, ControlSurface, Fuselage
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
                        airfoil=_build_asb_airfoil(x_sec.airfoil),
                        control_surfaces=[
                            ControlSurface(
                                name=x_sec.control_surface.name,
                                hinge_point=x_sec.control_surface.hinge_point,
                                symmetric=x_sec.control_surface.symmetric,
                                deflection=x_sec.control_surface.deflection
                            )] if x_sec.control_surface else []
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

def wingModelToWingConfig(wing: WingModel) -> WingConfiguration:
    asb_wing: schemas.AsbWingSchema = schemas.AsbWingSchema.model_validate(wing, from_attributes=True)
    # Convert the wing to a WingConfiguration object
    xsecs: List[asb.WingXSec] = [asb.WingXSec(
        xyz_le=xs.xyz_le,
        chord=xs.chord,
        twist=xs.twist,
        airfoil=_build_asb_airfoil(xs.airfoil),
        control_surfaces=
        [asb.ControlSurface(
            name=xs.control_surface.name,
            symmetric=xs.control_surface.symmetric,
            deflection=xs.control_surface.deflection,
            hinge_point=xs.control_surface.hinge_point,
            trailing_edge=True,
        )] if xs.control_surface else []
    ) for xs in asb_wing.x_secs]
    return WingConfiguration.from_asb(xsecs, asb_wing.symmetric)
