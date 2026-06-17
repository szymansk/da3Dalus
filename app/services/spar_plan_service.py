"""Service for the spar-plan endpoint (gh-1031).

Resolve an aeroplane id -> its wing -> a ``WingConfiguration`` (mm), build the
:class:`cad_designer.airplane.geometry.section_geometry.SectionGeometry`
primitive, sample it into solver stations (front + rear spar, both halves) via
:func:`cad_designer.airplane.geometry.spar_solver.build_stations_from_geometry`,
solve the layout with :func:`solve_spar_plan`, and convert the millimetre plan
to metres for the API.

The ``SectionGeometry`` construction needs cadquery (excluded on
``linux/aarch64``). When unavailable it raises
``SectionGeometryUnavailableError``; we translate that into a ``ValidationError``
so the endpoint returns a clean 422 instead of crashing.
"""

from __future__ import annotations

import logging

from app.converters.model_schema_converters import wing_model_to_wing_config
from app.core.exceptions import NotFoundError, ValidationError
from app.schemas.spar_plan import (
    SparPieceOut,
    SparPlanRequest,
    SparPlanResponse,
)
from app.services.wing_service import get_aeroplane_or_raise, get_wing_or_raise

logger = logging.getLogger(__name__)

_MM_TO_M = 0.001

#: Default manoeuvre load factor when no design assumption is set (mirrors
#: analysis_service._G_LIMIT_DEFAULT).
_G_LIMIT_DEFAULT = 3.0


def _resolve_wing(aeroplane, request: SparPlanRequest):
    """Pick the requested wing (by name) or the aeroplane's first wing."""
    if request.wing_name is not None:
        return get_wing_or_raise(aeroplane, request.wing_name)
    if not aeroplane.wings:
        raise NotFoundError(
            message="Aeroplane has no wings to plan a spar for",
            details={"aeroplane_id": str(getattr(aeroplane, "uuid", ""))},
        )
    return aeroplane.wings[0]


def _resolve_sigma_allow(db, request: SparPlanRequest) -> float:
    """Resolve the allowable bending stress (MPa) from the override or material.

    Raises ValidationError (-> 422) when the material is missing or has no
    positive allowable stress.
    """
    if request.sigma_allow_mpa_override is not None:
        return float(request.sigma_allow_mpa_override)

    from app.models.component import ComponentModel

    material = (
        db.query(ComponentModel)
        .filter(
            ComponentModel.id == request.material_id,
            ComponentModel.component_type == "material",
        )
        .first()
    )
    if material is None:
        raise ValidationError(
            message=f"Material component ID={request.material_id} not found.",
            details={"material_id": request.material_id},
        )
    specs = material.specs or {}
    sigma_allow = specs.get("allowable_bending_stress_mpa")
    if sigma_allow is None or sigma_allow <= 0:
        raise ValidationError(
            message=(
                f"Material '{material.name}' has no positive allowable_bending_stress_mpa "
                f"(got {sigma_allow}). Provide a positive sigma_allow_mpa_override or choose "
                "a structural material."
            ),
            details={"material_id": request.material_id, "name": material.name},
        )
    return float(sigma_allow)


def _resolve_g_limit(db, aeroplane_uuid) -> float:
    """Resolve g_limit from design assumptions, falling back to the default."""
    from app.services.design_assumptions_service import get_effective_assumption

    g_limit_raw = get_effective_assumption(db, aeroplane_uuid, "g_limit")
    if g_limit_raw is None:
        logger.warning(
            "No g_limit assumption for aeroplane %s — using default %.1f",
            aeroplane_uuid,
            _G_LIMIT_DEFAULT,
        )
        return _G_LIMIT_DEFAULT
    return float(g_limit_raw)


def _make_moment_fn(request: SparPlanRequest):
    """Build a moment_fn(y_span) -> N·m from the supplied distribution.

    Linear interpolation over the (sorted) span fractions; clamps outside the
    sampled range to the nearest endpoint.
    """
    samples = sorted(request.moments, key=lambda m: m.y_span)
    ys = [s.y_span for s in samples]
    ms = [abs(s.bending_moment_Nm) for s in samples]

    def moment_fn(y_span: float) -> float:
        if y_span <= ys[0]:
            return ms[0]
        if y_span >= ys[-1]:
            return ms[-1]
        for i in range(1, len(ys)):
            if y_span <= ys[i]:
                lo_y, hi_y = ys[i - 1], ys[i]
                lo_m, hi_m = ms[i - 1], ms[i]
                span = hi_y - lo_y
                if span <= 0.0:  # pragma: no cover - defensive: clamps prevent a leading dup hit
                    return hi_m
                t = (y_span - lo_y) / span
                return lo_m + t * (hi_m - lo_m)
        return ms[-1]  # pragma: no cover - unreachable given the clamps above

    return moment_fn


def _build_section_geometry(wing_config):
    """Construct the SectionGeometry primitive, translating the platform guard.

    Kept as a thin seam so fast tests can monkeypatch the cadquery boundary.
    """
    from cad_designer.airplane.geometry.section_geometry import (
        SectionGeometry,
        SectionGeometryUnavailableError,
    )

    try:
        return SectionGeometry(wing_config)
    except SectionGeometryUnavailableError as exc:
        raise ValidationError(
            message=f"Section geometry is unavailable on this platform: {exc}",
        ) from exc


def _mirror_to_left(stations):
    """Return the port-half mirror of a starboard station list (y_mm negated)."""
    import dataclasses

    return [dataclasses.replace(s, y_mm=-s.y_mm) for s in stations]


def _piece_to_out(piece) -> SparPieceOut:
    """Convert a millimetre SparPiece to a metre SparPieceOut."""
    return SparPieceOut(
        role=piece.role.value,
        spare_origin=[c * _MM_TO_M for c in piece.spare_origin],
        spare_vector=list(piece.spare_vector),
        outer_d=piece.outer_d * _MM_TO_M,
        inner_d=piece.inner_d * _MM_TO_M,
        wall=piece.wall * _MM_TO_M,
        shape=piece.shape,
        governing_y=piece.governing_y * _MM_TO_M,
        utilisation=piece.utilisation,
        joint_to_next=piece.joint_to_next,
    )


def compute_spar_plan(
    db,
    aeroplane_uuid,
    request: SparPlanRequest,
) -> SparPlanResponse:
    """Solve the buildable spar plan for an aeroplane's wing (gh-1031).

    Raises:
        NotFoundError: aeroplane or wing does not exist (-> 404).
        ValidationError: section geometry unavailable, or material/strength
            inputs invalid (-> 422).
    """
    from cad_designer.airplane.geometry.spar_solver import (
        build_stations_from_geometry,
        solve_spar_plan,
    )

    aeroplane = get_aeroplane_or_raise(db, aeroplane_uuid)
    wing = _resolve_wing(aeroplane, request)

    sigma_allow = _resolve_sigma_allow(db, request)
    g_limit = _resolve_g_limit(db, aeroplane_uuid)
    moment_fn = _make_moment_fn(request)

    # WingConfiguration / SectionGeometry work in millimetres (scale=1000.0).
    wing_config = wing_model_to_wing_config(wing, scale=1000.0)
    geometry = _build_section_geometry(wing_config)

    common = dict(
        moment_fn=moment_fn,
        sigma_allow_mpa=sigma_allow,
        n_span=request.n_span,
        packing_factor=request.packing_factor,
        safety_factor_j=request.safety_factor_j,
        g_limit=g_limit,
    )

    front_right = build_stations_from_geometry(geometry, x_c=request.front_x_over_chord, **common)
    rear_right = build_stations_from_geometry(geometry, x_c=request.rear_x_over_chord, **common)

    plan = solve_spar_plan(
        front_left=_mirror_to_left(front_right),
        front_right=front_right,
        rear_left=_mirror_to_left(rear_right),
        rear_right=rear_right,
    )

    return SparPlanResponse(
        front_pieces=[_piece_to_out(p) for p in plan.front_pieces],
        rear_pieces=[_piece_to_out(p) for p in plan.rear_pieces],
        front_joint=plan.front_joint,
        rear_joint=plan.rear_joint,
        reinforcement=_piece_to_out(plan.reinforcement) if plan.reinforcement else None,
    )
