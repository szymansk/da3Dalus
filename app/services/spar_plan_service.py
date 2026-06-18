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

#: gh-1038: Front-spar chord fraction assumed for the torsion-couple spacing
#: when ``front_x_over_chord`` is None (front sits at section max-thickness,
#: typically ~0.30c on common airfoils). Used only to derive the front–rear
#: spar spacing for the rear torsion reaction; the front spar itself still
#: samples the real max-thickness location.
_DEFAULT_FRONT_X_C = 0.30

#: Smallest front–rear spacing fraction we will divide by, so a degenerate
#: layout (front≈rear) cannot produce an infinite torsion reaction.
_MIN_SPAR_SPACING = 0.05


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


def _make_interpolator(ys: list[float], values: list[float]):
    """Build a clamped piecewise-linear interpolator over sorted ``ys``.

    Values outside the sampled range clamp to the nearest endpoint. Shared by
    the front bending driver and the rear torsion driver (gh-1038).
    """

    def interp(y_span: float) -> float:
        if y_span <= ys[0]:
            return values[0]
        if y_span >= ys[-1]:
            return values[-1]
        for i in range(1, len(ys)):
            if y_span <= ys[i]:
                lo_y, hi_y = ys[i - 1], ys[i]
                lo_v, hi_v = values[i - 1], values[i]
                span = hi_y - lo_y
                if span <= 0.0:  # pragma: no cover - defensive: clamps prevent a leading dup hit
                    return hi_v
                t = (y_span - lo_y) / span
                return lo_v + t * (hi_v - lo_v)
        return values[-1]  # pragma: no cover - unreachable given the clamps above

    return interp


def _make_moment_fn(request: SparPlanRequest):
    """Build the FRONT (bending) moment_fn(y_span) -> N·m.

    Linear interpolation over the (sorted) span fractions; clamps outside the
    sampled range to the nearest endpoint. The front spar stays bending-driven
    (gh-1038 keeps this unchanged).
    """
    samples = sorted(request.moments, key=lambda m: m.y_span)
    ys = [s.y_span for s in samples]
    ms = [abs(s.bending_moment_Nm) for s in samples]
    return _make_interpolator(ys, ms)


def _spar_spacing_fraction(request: SparPlanRequest) -> float:
    """Front–rear spar chordwise spacing as a fraction of chord (gh-1038).

    The torsion couple T(y) is reacted by the front+rear pair over this
    spacing, so the rear-spar reaction force ∝ T(y) / spacing. When the front
    spar location is unset (max-thickness), assume :data:`_DEFAULT_FRONT_X_C`.
    Floored at :data:`_MIN_SPAR_SPACING` so a degenerate layout can't blow up.
    """
    front_x = request.front_x_over_chord
    if front_x is None:
        front_x = _DEFAULT_FRONT_X_C
    spacing = request.rear_x_over_chord - front_x
    return max(abs(spacing), _MIN_SPAR_SPACING)


def _make_rear_moment_fn(request: SparPlanRequest):
    """Build the REAR (torsion) sizing-moment fn(y_span) -> N·m (gh-1038).

    The rear spar's real job is to react the wing's torsion couple, NOT the
    primary bending moment. The front+rear pair forms a couple against wing
    twist: the rear member carries a reaction ≈ ``T(y) / spacing`` where
    ``spacing`` is the chordwise front–rear distance (fraction of chord). Any
    genuine secondary bending is added on top
    (``rear_secondary_bending_fraction`` · M(y)).

    Torsion source priority:

    1. ``request.torsion_moments`` — an explicit T(y) about the front spar
       (ideally integrated from the strip pitching moments; #1002 currently
       carries only V/M, so this is supplied by the caller).
    2. Documented proxy — when no T(y) is given, estimate
       T(y) ≈ ``pitching_moment_proxy_ratio`` · M(y). This keeps the rear spar
       torsion-driven (front ≠ rear) rather than silently a bending twin.
       **Follow-up:** extend #1002 to integrate section pitching moments into a
       real T(y) and feed it here, retiring the proxy.
    """
    spacing = _spar_spacing_fraction(request)
    secondary_fraction = request.rear_secondary_bending_fraction
    bending_fn = _make_moment_fn(request)

    if request.torsion_moments:
        samples = sorted(request.torsion_moments, key=lambda t: t.y_span)
        ys = [s.y_span for s in samples]
        ts = [abs(s.torsion_moment_Nm) for s in samples]
        torsion_fn = _make_interpolator(ys, ts)
    else:
        proxy_ratio = request.pitching_moment_proxy_ratio

        def torsion_fn(y_span: float) -> float:
            return proxy_ratio * bending_fn(y_span)

    def rear_moment_fn(y_span: float) -> float:
        reaction = torsion_fn(y_span) / spacing
        secondary = secondary_fraction * bending_fn(y_span)
        return reaction + secondary

    return rear_moment_fn


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
    """Convert a millimetre SparPiece to a metre SparPieceOut.

    gh-1057: expose the piece's spanwise extent (``y_start``/``y_end``, m) so the
    UI can show where each piece runs and where the telescoping joint sits. The
    extent is derived from the piece's own geometry — the root is its
    ``spare_origin`` y, the tip is that plus the piece length along its span
    direction (``spare_vector`` y) — then converted mm->m.
    """
    y_start_mm = piece.spare_origin[1]
    y_end_mm = y_start_mm + piece.length * piece.spare_vector[1]
    return SparPieceOut(
        role=piece.role.value,
        spare_origin=[c * _MM_TO_M for c in piece.spare_origin],
        spare_vector=list(piece.spare_vector),
        outer_d=piece.outer_d * _MM_TO_M,
        inner_d=piece.inner_d * _MM_TO_M,
        wall=piece.wall * _MM_TO_M,
        shape=piece.shape,
        governing_y=piece.governing_y * _MM_TO_M,
        # gh-1072: x/c is a dimensionless chord fraction — pass through unscaled.
        x_over_chord=piece.x_over_chord,
        y_start=y_start_mm * _MM_TO_M,
        y_end=y_end_mm * _MM_TO_M,
        utilisation=piece.utilisation,
        joint_to_next=piece.joint_to_next,
        feasible=piece.feasible,
        infeasibility_reason=piece.infeasibility_reason,
    )


def compute_spar_plan_object(
    db,
    aeroplane_uuid,
    request: SparPlanRequest,
    wing=None,
):
    """Solve the buildable spar plan and return the in-memory ``SparPlan`` (mm).

    Shared core of :func:`compute_spar_plan` (gh-1031) and the spar-insert
    service (gh-1049). Returns the solver's millimetre :class:`SparPlan` so
    callers can either serialise it (mm→m) or map it into ``Spare`` objects.

    Args:
        wing: when supplied, skip wing resolution (the insert service resolves
            the wing itself for unit + segment work). Otherwise resolve via the
            request.

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
    if wing is None:
        wing = _resolve_wing(aeroplane, request)

    sigma_allow = _resolve_sigma_allow(db, request)
    g_limit = _resolve_g_limit(db, aeroplane_uuid)
    # gh-1038: front spar = bending moment; rear spar = torsion couple reacted
    # over the front–rear spar spacing (+ optional secondary bending). The two
    # spars are sized from DIFFERENT load distributions so the rear is no longer
    # a near-twin of the front.
    front_moment_fn = _make_moment_fn(request)
    rear_moment_fn = _make_rear_moment_fn(request)

    # WingConfiguration / SectionGeometry work in millimetres (scale=1000.0).
    wing_config = wing_model_to_wing_config(wing, scale=1000.0)
    geometry = _build_section_geometry(wing_config)

    common = dict(
        sigma_allow_mpa=sigma_allow,
        n_span=request.n_span,
        packing_factor=request.packing_factor,
        safety_factor_j=request.safety_factor_j,
        g_limit=g_limit,
    )

    front_right = build_stations_from_geometry(
        geometry, x_c=request.front_x_over_chord, moment_fn=front_moment_fn, **common
    )
    rear_right = build_stations_from_geometry(
        geometry, x_c=request.rear_x_over_chord, moment_fn=rear_moment_fn, **common
    )

    return solve_spar_plan(
        front_left=_mirror_to_left(front_right),
        front_right=front_right,
        rear_left=_mirror_to_left(rear_right),
        rear_right=rear_right,
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
    plan = compute_spar_plan_object(db, aeroplane_uuid, request)

    return SparPlanResponse(
        front_pieces=[_piece_to_out(p) for p in plan.front_pieces],
        rear_pieces=[_piece_to_out(p) for p in plan.rear_pieces],
        front_joint=plan.front_joint,
        rear_joint=plan.rear_joint,
        reinforcement=_piece_to_out(plan.reinforcement) if plan.reinforcement else None,
        feasible=plan.feasible,
        infeasibility_reason=plan.infeasibility_reason,
    )
