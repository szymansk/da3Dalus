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
import math

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


# ---------------------------------------------------------------------------
# gh-1080: Stock snapping — select lightest adequate real stock
# ---------------------------------------------------------------------------

#: Float-equality tolerance (mm³) for W_stock ≥ erf_W comparisons.
#: Avoids rejecting stock whose W equals erf_W up to floating-point rounding.
_W_EQ_TOL = 1e-9


def _w_stock(outer_d_mm: float, inner_d_mm: float | None) -> float:
    """Section modulus (mm³) of a real stock item.

    Tube:  W = π·(Da⁴ − Di⁴) / (32·Da)   [Sadraey eq. 10.x / Anderson ch.5]
    Rod:   W = d³ / 10   (solid round, Di=0)

    The formula unifies because a solid rod is a tube with Di=0:
      π·(Da⁴ − 0) / (32·Da) = π·Da³/32 ≠ Da³/10.
    For a rod the standard formula (solid circular) W = π·d³/32 ≈ d³/10.05 ≈
    d³/10 (the 1/10 approximation is from d³·π/32 with π/32≈0.0982≈1/10.18 but
    the solver uses d³/10 throughout; we stay consistent with that convention).
    """
    di = inner_d_mm if inner_d_mm is not None else 0.0
    if di <= 0.0:
        # Solid rod: use the same formula the solver uses for required OD sizing.
        return outer_d_mm**3 / 10.0
    # Hollow tube: exact section-modulus formula.
    return math.pi * (outer_d_mm**4 - di**4) / (32.0 * outer_d_mm)


def _linear_mass(outer_d_mm: float, inner_d_mm: float | None, density_kg_m3: float) -> float:
    """Linear mass ρ·A (kg/m) of a stock cross-section.

    A = π/4·(Da² − Di²)  [mm²], converted to m² before multiplying by density.
    Used as the ranking objective: minimum ρ·A = lightest per unit length.
    """
    di = inner_d_mm if inner_d_mm is not None else 0.0
    area_mm2 = math.pi / 4.0 * (outer_d_mm**2 - max(0.0, di) ** 2)
    area_m2 = area_mm2 * 1e-6
    return density_kg_m3 * area_m2


def snap_piece_to_stock(db, piece, *, erf_w: float, max_od_mm: float | None = None):
    """Snap a ``SparPiece`` to the lightest adequate stock from the Component Library.

    Queries all ``spar_tube`` rows where ``role_use='spar'`` and
    ``geometry_complete=True``, then selects the stock item with the smallest
    linear mass (ρ·A per unit length) that passes three hard filters:

    1. **Solid/hollow match**: a solid piece (``inner_d == 0``) only snaps to
       solid stock (``inner_d_mm == 0``); a hollow piece only snaps to hollow
       stock.  Mixing would produce a rod piece with inner_d > 0 — structurally
       inconsistent.
    2. **Containment-band fit**: the stock OD must fit inside the airfoil
       channel at the governing station: ``Da ≤ max_od_mm`` (the band depth at
       that station minus print-clearance, pre-computed by the caller).  When
       ``max_od_mm`` is None the band filter is skipped (backwards-compatible
       for callers that can't provide the band).
    3. **Strength**: ``W_stock(Da, Di) ≥ erf_w``.

    Section-modulus comparison (gh-1080 spec validation):
    - Tube stock:  W = π·(Da⁴ − Di⁴) / (32·Da)
    - Rod stock:   W = d³ / 10   (Di = 0; same formula as upstream sizing)

    Args:
        db: SQLAlchemy session (real or in-memory test session).
        piece: A ``SparPiece`` instance to snap (mutated in-place).
        erf_w: Required section modulus (mm³) the chosen stock must satisfy.
        max_od_mm: Maximum allowable outer diameter (mm) from the governing
            station's containment band.  Stock whose OD exceeds this is
            rejected as geometrically infeasible (won't fit the printed channel).

    Returns:
        The original ``piece`` mutated in-place with snapped dimensions
        (outer_d, inner_d updated to the selected stock values), or with
        feasible=False and an infeasibility_reason when no stock fits.
    """
    from app.models.component import ComponentModel

    rows = db.query(ComponentModel).filter(ComponentModel.component_type == "spar_tube").all()

    # Determine whether this piece is solid (rod) or hollow (tube).
    piece_is_solid = piece.inner_d <= 0.0

    # Filter: spar-eligible + geometry-complete + solid/hollow match.
    candidates = [
        r
        for r in rows
        if r.specs.get("role_use") == "spar"
        and r.specs.get("geometry_complete", False)
        and r.specs.get("outer_d_mm") is not None
        and (
            (piece_is_solid and (r.specs.get("inner_d_mm") or 0.0) <= 0.0)
            or (not piece_is_solid and (r.specs.get("inner_d_mm") or 0.0) > 0.0)
        )
    ]

    # Hard filters: containment band + strength.  Build (linear_mass, Da, Di, name)
    # tuples for adequate candidates.
    adequate = []
    for row in candidates:
        da = float(row.specs["outer_d_mm"])
        di_raw = row.specs.get("inner_d_mm")
        di = float(di_raw) if di_raw is not None else 0.0

        # Containment-band filter (gh-1080 AC): stock OD must fit the printed channel.
        if max_od_mm is not None and da > max_od_mm + _W_EQ_TOL:
            continue

        w = _w_stock(da, di)
        if w >= erf_w - _W_EQ_TOL:
            density = float(row.specs.get("density_kg_m3", 1550.0))
            lm = _linear_mass(da, di, density)
            adequate.append((lm, da, di, row.name))

    if not adequate:
        # Distinguish the infeasibility mode for better diagnostics.
        if max_od_mm is not None:
            # Check whether any stock would fit the band (ignoring strength).
            band_fits = [
                r for r in candidates if float(r.specs["outer_d_mm"]) <= max_od_mm + _W_EQ_TOL
            ]
            if not band_fits:
                piece.feasible = False
                piece.infeasibility_reason = (
                    f"no stock fits band: all available spar_tube stock ODs exceed "
                    f"the containment band max_od={max_od_mm:.1f} mm at the governing "
                    "station; increase chord/thickness or choose a narrower spar type"
                )
                return piece

        piece.feasible = False
        piece.infeasibility_reason = (
            f"no stock: strongest available spar_tube stock (W_max) is below the "
            f"required section modulus erf_W={erf_w:.1f} mm³; "
            "add stronger/larger stock to the Component Library or reduce design load"
        )
        return piece

    # Pick lightest (minimum ρ·A); tie-break by smallest OD, then by name for
    # determinism in tests.
    adequate.sort(key=lambda t: (t[0], t[1], t[3]))
    best_lm, best_da, best_di, best_name = adequate[0]

    piece.outer_d = best_da
    piece.inner_d = best_di
    piece.feasible = True
    piece.infeasibility_reason = None
    logger.debug(
        "snap_piece_to_stock: snapped to %s (OD=%.1f ID=%.1f W=%.1f mm³ ≥ erf_W=%.1f)",
        best_name,
        best_da,
        best_di,
        _w_stock(best_da, best_di),
        erf_w,
    )
    return piece


def _erf_w_for_piece(piece) -> float:
    """Infer the required section modulus (mm³) for a SparPiece.

    The solver recorded required_od indirectly in outer_d (the
    strength-required OD before any stock snap).  We reconstruct
    erf_W = outer_d³/10 — the same solid-rod formula used in
    build_stations_from_geometry.  This is ~1.8 % conservative vs the exact
    solid-circular W = π·d³/32; the upstream sizing intentionally uses d³/10
    throughout, so staying consistent here avoids a unit inconsistency.
    """
    return piece.outer_d**3 / 10.0


def _max_od_from_stations(stations, governing_y_mm: float) -> float | None:
    """Return the containment-band half-depth (mm) at the governing station.

    The governing station is the one whose ``y_mm`` is closest to
    ``governing_y_mm``.  The band half-depth ``(band_hi - band_lo) / 2``
    is the maximum OD a spar centred on ``center_z`` can have without
    breaching the packing clearance — i.e. the hard upper bound on OD.

    Returns None when the station list is empty (band filter disabled).
    """
    if not stations:
        return None
    closest = min(stations, key=lambda s: abs(s.y_mm - governing_y_mm))
    return max(0.0, closest.band_hi - closest.band_lo)


def apply_stock_snap_to_plan(db, plan, stations=None) -> None:
    """Apply stock snapping in-place to every piece in ``plan`` (gh-1080).

    Iterates all front + rear + reinforcement pieces and calls
    :func:`snap_piece_to_stock` for each. Infeasibility roll-up is refreshed
    afterwards so ``plan.feasible`` reflects the post-snap state.

    Args:
        db: SQLAlchemy session.
        plan: ``SparPlan`` instance to snap in-place.
        stations: Optional combined station list (front_right + rear_right) used
            to derive the containment-band ``max_od_mm`` for each piece.  When
            provided, stock whose OD exceeds the governing station's band depth is
            rejected as geometrically infeasible (won't fit the printed channel).
            When None the band filter is skipped (backwards-compatible).

    Mutates ``plan`` in-place; returns None.
    """
    all_pieces = list(plan.front_pieces) + list(plan.rear_pieces)
    if plan.reinforcement is not None:
        all_pieces.append(plan.reinforcement)

    for piece in all_pieces:
        erf_w = _erf_w_for_piece(piece)
        max_od = _max_od_from_stations(stations, piece.governing_y) if stations else None
        snap_piece_to_stock(db, piece, erf_w=erf_w, max_od_mm=max_od)

    # Refresh feasibility roll-up.
    infeasible = [p for p in all_pieces if not p.feasible]
    if infeasible:
        plan.feasible = False
        plan.infeasibility_reason = infeasible[0].infeasibility_reason
    else:
        plan.feasible = True
        plan.infeasibility_reason = None


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
        # gh-1080: extended dims for rectangular/capped; None for tube/rod.
        width=piece.width * _MM_TO_M if piece.width is not None else None,
        height=piece.height * _MM_TO_M if piece.height is not None else None,
        cap_width=piece.cap_width * _MM_TO_M if piece.cap_width is not None else None,
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
        SparRole,
        SparSpec,
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

    # gh-1080: shape chosen by the user flows into both spar specs so the
    # solver produces the right cross-section (rod → solid, no bore; tube →
    # hollow, telescoping-capable; etc.).
    front_spec = SparSpec(role=SparRole.FRONT, shape=request.shape)
    rear_spec = SparSpec(role=SparRole.REAR, shape=request.shape)

    plan = solve_spar_plan(
        front_left=_mirror_to_left(front_right),
        front_right=front_right,
        rear_left=_mirror_to_left(rear_right),
        rear_right=rear_right,
        front_spec=front_spec,
        rear_spec=rear_spec,
    )

    # gh-1080: snap every piece to the lightest adequate real stock from the
    # Component Library (W_stock(Da,Di) ≥ erf_W; minimum ρ·A objective).
    # Pass the combined station list so the band filter can reject stock that
    # won't fit the printed channel at the governing station.
    # Only when a real DB session is provided (fast tests patch the solver
    # boundary and may pass db=None to skip).
    if db is not None:
        # Merge front + rear starboard stations for band lookup (both halves
        # have the same band depths; starboard is the canonical list).
        all_stations = list(front_right) + list(rear_right)
        apply_stock_snap_to_plan(db, plan, stations=all_stations)

    return plan


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
        front_no_spar_from_y=(
            plan.front_no_spar_from_y * _MM_TO_M if plan.front_no_spar_from_y is not None else None
        ),
        rear_no_spar_from_y=(
            plan.rear_no_spar_from_y * _MM_TO_M if plan.rear_no_spar_from_y is not None else None
        ),
    )
