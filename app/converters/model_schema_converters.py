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


def _normalize_airfoil_reference_for_schema(airfoil_ref: asb.Airfoil | str) -> str:
    """Return a stable airfoil reference string for API/database schemas."""
    raw_reference = str(getattr(airfoil_ref, "name", airfoil_ref) or "")
    if not raw_reference:
        return raw_reference

    # Convert absolute paths inside ".../components/airfoils/..." back to a portable relative path.
    normalized = raw_reference.replace("\\", "/")
    parts = [part for part in normalized.split("/") if part]
    for index in range(len(parts) - 1):
        if parts[index].lower() == "components" and parts[index + 1].lower() == "airfoils":
            relative = "/".join(parts[index:])
            return f"./{relative}"

    return raw_reference


def _wing_configuration_sections(wing_config: WingConfiguration):
    """
    Return wing cross-section descriptors in section order (root first, then each segment tip).
    """
    if not wing_config.segments:
        return []

    sections = [(wing_config.segments[0].root_airfoil, wing_config.segments[0].trailing_edge_device)]
    for segment in wing_config.segments:
        sections.append((segment.tip_airfoil, segment.trailing_edge_device))
    return sections


def _prepare_wing_config_for_asb(wing_config: WingConfiguration) -> None:
    """
    Ensure WingConfiguration values are compatible with WingConfiguration.asb_wing().

    `from_asb()` currently creates segments with rotation_point_rel_chord=0.0, but `asb_wing()`
    requires 0.25. We normalize this before conversion.
    """
    for segment in wing_config.segments or []:
        if segment.root_airfoil.rotation_point_rel_chord != 0.25:
            segment.root_airfoil.rotation_point_rel_chord = 0.25
        if segment.tip_airfoil.rotation_point_rel_chord != 0.25:
            segment.tip_airfoil.rotation_point_rel_chord = 0.25

    # Reset cached ASB representation so the updated geometry is used.
    wing_config._asb_wing = None


def wingConfigToAsbWingSchema(
    wing_config: WingConfiguration,
    wing_name: str,
    scale: float = 1.0,
) -> schemas.AsbWingSchema:
    """
    Convert a WingConfiguration to the v2 ASB wing schema.

    Args:
        wing_config: Source wing configuration.
        wing_name: Name to assign in the resulting schema/model.
        scale: Scaling used when creating the internal ASB wing (e.g. 0.001 for mm->m).
    """
    _prepare_wing_config_for_asb(wing_config)
    asb_wing = wing_config.asb_wing(scale=scale)
    section_data = _wing_configuration_sections(wing_config)
    x_secs = []
    for index, x_sec in enumerate(asb_wing.xsecs):
        control_surface = None
        if x_sec.control_surfaces:
            cs = x_sec.control_surfaces[0]
            control_surface = schemas.ControlSurfaceSchema(
                name=cs.name,
                hinge_point=float(cs.hinge_point),
                symmetric=bool(cs.symmetric),
                deflection=float(cs.deflection),
            )

        if index < len(section_data):
            section_airfoil, _ = section_data[index]
            section_twist = float(section_airfoil.incidence)
            section_airfoil_ref = section_airfoil.airfoil
        else:
            section_twist = float(x_sec.twist)
            section_airfoil_ref = x_sec.airfoil

        x_secs.append(
            schemas.WingXSecSchema(
                xyz_le=[float(value) for value in x_sec.xyz_le],
                chord=float(x_sec.chord),
                twist=section_twist,
                airfoil=_normalize_airfoil_reference_for_schema(section_airfoil_ref),
                control_surface=control_surface,
            )
        )

    return schemas.AsbWingSchema(
        name=wing_name,
        symmetric=bool(asb_wing.symmetric),
        x_secs=x_secs,
    )


def wingConfigToWingModel(
    wing_config: WingConfiguration,
    wing_name: str,
    scale: float = 1.0,
) -> WingModel:
    """
    Convert a WingConfiguration to the persisted WingModel representation.

    Args:
        wing_config: Source wing configuration.
        wing_name: Name to assign to the resulting wing model.
        scale: Scaling used when creating the internal ASB wing (e.g. 0.001 for mm->m).
    """
    asb_wing_schema = wingConfigToAsbWingSchema(
        wing_config=wing_config,
        wing_name=wing_name,
        scale=scale,
    )
    return WingModel.from_dict(name=wing_name, data=asb_wing_schema.model_dump())
