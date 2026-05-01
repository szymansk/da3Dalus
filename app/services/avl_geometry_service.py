"""Service layer for AVL geometry file CRUD and on-the-fly generation (gh-381).

Extended in gh-384 with a pure-Python AVL geometry builder that replaces
Aerosandbox's ``asb.AVL.write_avl()`` and adds ``inject_cdcl`` for
NeuralFoil profile-drag integration.
"""

from __future__ import annotations

import logging
import re as _re

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.avl.geometry import (
    AvlAfile,
    AvlCdcl,
    AvlControl,
    AvlGeometryFile,
    AvlNaca,
    AvlReference,
    AvlSection,
    AvlSurface,
    AvlSymmetry,
)
from app.avl.spacing import optimise_surface_spacing
from app.core.exceptions import InternalError, NotFoundError
from app.models.aeroplanemodel import AeroplaneModel
from app.models.avl_geometry_file import AvlGeometryFileModel
from app.schemas.aeroanalysisschema import CdclConfig, SpacingConfig
from app.schemas.aeroplaneschema import AeroplaneSchema, AsbWingSchema, WingXSecSchema
from app.schemas.avl_geometry import AvlGeometryResponse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Regex for detecting NACA 4/5-digit airfoil names
# ---------------------------------------------------------------------------
_NACA_RE = _re.compile(r"^naca\s*(\d{4,5})$", _re.IGNORECASE)


# ---------------------------------------------------------------------------
# AVL Geometry Builder (gh-384)
# ---------------------------------------------------------------------------


def _build_airfoil_node(airfoil_ref: str) -> AvlNaca | AvlAfile:
    """Convert an airfoil reference string to an AVL airfoil node.

    - ``"naca2412"`` → ``AvlNaca("2412")``
    - File path → ``AvlAfile(resolved_path)``
    - Fallback → ``AvlNaca("0012")``
    """
    ref = str(airfoil_ref).strip()
    m = _NACA_RE.match(ref)
    if m:
        return AvlNaca(digits=m.group(1))

    # Try resolving as a file via the central resolver
    try:
        from app.services.create_wing_configuration import _resolve_airfoil_reference

        resolved = _resolve_airfoil_reference(ref)
        import os

        if os.path.isfile(resolved):
            return AvlAfile(filepath=resolved)
    except Exception:
        logger.debug("Could not resolve airfoil '%s' as file, falling back to NACA 0012", ref)

    return AvlNaca(digits="0012")


def _build_section(
    xsec: WingXSecSchema,
    controls: list[AvlControl],
) -> AvlSection:
    """Build an AvlSection from a WingXSecSchema."""
    airfoil_node = _build_airfoil_node(str(xsec.airfoil))

    # Compute claf = 1 + 0.77 * max_thickness
    claf = 1.0
    try:
        import aerosandbox as asb

        from app.converters.model_schema_converters import _build_asb_airfoil

        asb_airfoil = _build_asb_airfoil(xsec.airfoil)
        claf = 1.0 + 0.77 * asb_airfoil.max_thickness()
    except Exception:
        logger.debug("Could not compute CLAF for airfoil '%s', using default 1.0", xsec.airfoil)

    return AvlSection(
        xyz_le=tuple(xsec.xyz_le),
        chord=xsec.chord,
        ainc=xsec.twist,
        airfoil=airfoil_node,
        claf=claf,
        cdcl=AvlCdcl.zeros(),
        controls=list(controls),
    )


def _build_controls_for_wing(wing: AsbWingSchema) -> list[list[AvlControl]]:
    """Build per-section control lists replicating ASB's CONTROL duplication.

    For each xsec[i] with a control surface, the CONTROL command is added to
    both section i and section i+1 so AVL interpolates the deflection across
    the panel strip.
    """
    from app.converters.model_schema_converters import _control_surface_for_xsec

    n = len(wing.x_secs)
    controls_per_section: list[list[AvlControl]] = [[] for _ in range(n)]

    for i, xsec in enumerate(wing.x_secs):
        cs = _control_surface_for_xsec(xsec)
        if cs is None:
            continue

        ctrl = AvlControl(
            name=cs.name,
            gain=1.0,
            xhinge=cs.hinge_point,
            xyz_hvec=(0.0, 0.0, 0.0),
            sgn_dup=1.0 if cs.symmetric else -1.0,
        )
        controls_per_section[i].append(ctrl)
        if i + 1 < n:
            controls_per_section[i + 1].append(ctrl)

    return controls_per_section


def _build_surface(
    wing_name: str,
    wing: AsbWingSchema,
    spacing_config: SpacingConfig,
) -> AvlSurface:
    """Build an AvlSurface from a wing schema."""
    controls_per_section = _build_controls_for_wing(wing)

    sections = [_build_section(xsec, controls_per_section[i]) for i, xsec in enumerate(wing.x_secs)]

    surface = AvlSurface(
        name=wing_name,
        n_chord=spacing_config.n_chord,
        c_space=spacing_config.c_space,
        sections=sections,
        yduplicate=0.0 if wing.symmetric else None,
    )

    return optimise_surface_spacing(surface, spacing_config)


def build_avl_geometry_file(
    plane_schema: AeroplaneSchema,
    spacing_config: SpacingConfig | None = None,
) -> AvlGeometryFile:
    """Build a complete AvlGeometryFile from an AeroplaneSchema.

    Uses ``aeroplane_schema_to_asb_airplane_async`` to obtain reference
    quantities (s_ref, c_ref, b_ref).
    """
    from app.converters.model_schema_converters import aeroplane_schema_to_asb_airplane_async

    if spacing_config is None:
        spacing_config = SpacingConfig()

    asb_airplane = aeroplane_schema_to_asb_airplane_async(plane_schema=plane_schema)

    xyz_ref = tuple(plane_schema.xyz_ref) if plane_schema.xyz_ref else (0.0, 0.0, 0.0)

    reference = AvlReference(
        s_ref=asb_airplane.s_ref,
        c_ref=asb_airplane.c_ref,
        b_ref=asb_airplane.b_ref,
        xyz_ref=xyz_ref,
    )

    surfaces: list[AvlSurface] = []
    if plane_schema.wings:
        for wing_name, wing in plane_schema.wings.items():
            surfaces.append(_build_surface(wing_name, wing, spacing_config))

    return AvlGeometryFile(
        title=plane_schema.name,
        mach=0.0,
        symmetry=AvlSymmetry(),
        reference=reference,
        surfaces=surfaces,
    )


def generate_avl_content_from_schema(
    plane_schema: AeroplaneSchema,
    spacing_config: SpacingConfig | None = None,
) -> str:
    """Generate AVL geometry file content from an AeroplaneSchema."""
    return repr(build_avl_geometry_file(plane_schema, spacing_config))


def inject_cdcl(
    avl_file: AvlGeometryFile,
    plane_schema: AeroplaneSchema,
    operating_point: "OperatingPointSchema",
    cdcl_config: CdclConfig,
) -> None:
    """Inject NeuralFoil CDCL values in-place. Preserves non-zero (user-edited) CDCLs."""
    from app.converters.model_schema_converters import _build_asb_airfoil
    from app.schemas.aeroanalysisschema import OperatingPointSchema  # noqa: F811
    from app.services.neuralfoil_cdcl_service import NeuralFoilCdclService, compute_reynolds_number

    service = NeuralFoilCdclService()
    wing_list = list(plane_schema.wings.values()) if plane_schema.wings else []

    if len(avl_file.surfaces) != len(wing_list):
        logger.warning(
            "Surface/wing count mismatch: %d surfaces vs %d wings — CDCL injection may be incomplete",
            len(avl_file.surfaces),
            len(wing_list),
        )

    for surf_idx, surface in enumerate(avl_file.surfaces):
        if surf_idx >= len(wing_list):
            break
        wing = wing_list[surf_idx]
        for sec_idx, section in enumerate(surface.sections):
            if section.cdcl is not None and not section.cdcl.is_zero():
                continue  # preserve user-edited values
            if sec_idx >= len(wing.x_secs):
                continue
            xsec = wing.x_secs[sec_idx]
            velocity = float(operating_point.velocity)
            re = compute_reynolds_number(
                velocity=velocity, chord=xsec.chord, altitude=operating_point.altitude
            )
            airfoil = _build_asb_airfoil(xsec.airfoil)
            section.cdcl = service.compute_cdcl(
                airfoil=airfoil, re=re, mach=avl_file.mach, config=cdcl_config
            )


# ---------------------------------------------------------------------------
# CRUD helpers (unchanged from gh-381)
# ---------------------------------------------------------------------------


def _get_aeroplane_or_raise(db: Session, aeroplane_uuid) -> AeroplaneModel:
    try:
        aeroplane = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == aeroplane_uuid).first()
    except SQLAlchemyError as e:
        logger.error("Database error looking up aeroplane: %s", e)
        raise InternalError(message=f"Database error: {e}")
    if aeroplane is None:
        raise NotFoundError(entity="Aeroplane", resource_id=aeroplane_uuid)
    return aeroplane


def generate_avl_content(db: Session, aeroplane_uuid) -> str:
    """Generate AVL geometry content from the current aeroplane state.

    Uses the pure-Python AVL geometry builder (gh-384) instead of
    Aerosandbox's ``asb.AVL.write_avl()``.
    """
    from app.services.analysis_service import get_aeroplane_schema_or_raise

    plane_schema = get_aeroplane_schema_or_raise(db, aeroplane_uuid)
    return generate_avl_content_from_schema(plane_schema)


def get_avl_geometry(db: Session, aeroplane_uuid) -> AvlGeometryResponse:
    """Return the stored AVL geometry file, or generate it on the fly if none exists."""
    aeroplane = _get_aeroplane_or_raise(db, aeroplane_uuid)

    geom = db.query(AvlGeometryFileModel).filter_by(aeroplane_id=aeroplane.id).first()
    if geom is not None:
        return AvlGeometryResponse(
            content=geom.content,
            is_dirty=geom.is_dirty,
            is_user_edited=geom.is_user_edited,
        )

    content = generate_avl_content(db, aeroplane_uuid)
    return AvlGeometryResponse(
        content=content,
        is_dirty=False,
        is_user_edited=False,
    )


def save_avl_geometry(db: Session, aeroplane_uuid, content: str) -> AvlGeometryResponse:
    """Persist user-edited AVL geometry content, creating or updating the record."""
    aeroplane = _get_aeroplane_or_raise(db, aeroplane_uuid)

    geom = db.query(AvlGeometryFileModel).filter_by(aeroplane_id=aeroplane.id).first()
    if geom is None:
        geom = AvlGeometryFileModel(aeroplane_id=aeroplane.id, content=content)
        db.add(geom)
    else:
        geom.content = content

    geom.is_user_edited = True
    geom.is_dirty = False
    db.flush()

    return AvlGeometryResponse(
        content=geom.content,
        is_dirty=geom.is_dirty,
        is_user_edited=geom.is_user_edited,
    )


def regenerate_avl_geometry(db: Session, aeroplane_uuid) -> AvlGeometryResponse:
    """Discard any saved file and regenerate content from the current aeroplane state."""
    aeroplane = _get_aeroplane_or_raise(db, aeroplane_uuid)
    content = generate_avl_content(db, aeroplane_uuid)

    geom = db.query(AvlGeometryFileModel).filter_by(aeroplane_id=aeroplane.id).first()
    if geom is not None:
        db.delete(geom)
        db.flush()

    return AvlGeometryResponse(
        content=content,
        is_dirty=False,
        is_user_edited=False,
    )


def get_user_avl_content(db: Session, aeroplane_uuid) -> str | None:
    """Return saved AVL content if it exists, is user-edited, and is not dirty.

    Returns None when no file is saved, the file was not user-edited, or the
    file is dirty (i.e. the aeroplane geometry changed after the last save).
    In all None cases the caller should fall back to generating fresh content.
    """
    aeroplane = _get_aeroplane_or_raise(db, aeroplane_uuid)
    geom = db.query(AvlGeometryFileModel).filter_by(aeroplane_id=aeroplane.id).first()
    if geom is None or not geom.is_user_edited or geom.is_dirty:
        return None
    return geom.content


def delete_avl_geometry(db: Session, aeroplane_uuid) -> None:
    """Delete the stored AVL geometry file. Raises NotFoundError if none exists."""
    aeroplane = _get_aeroplane_or_raise(db, aeroplane_uuid)

    geom = db.query(AvlGeometryFileModel).filter_by(aeroplane_id=aeroplane.id).first()
    if geom is None:
        raise NotFoundError(entity="AVL geometry file", resource_id=aeroplane_uuid)

    db.delete(geom)
    db.flush()
