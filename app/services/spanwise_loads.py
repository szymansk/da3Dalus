"""Spanwise shear and bending-moment integrator (gh-1002).

Pure post-processing over existing Trefftz-Plane strip forces — no new
aerodynamic model.  Per-strip lift is `L_j = q · Area_j · cl_j`; the
running shear and bending moment are integrated from tip to root:

    V(y) = Σ_{j: y_j > y} L_j
    M(y) = Σ_{j: y_j > y} L_j · (y_j − y)

All inputs come from a `StripForcesResponse`-compatible dict (the same
shape `analysis_service._strip_surfaces_from_result` produces), so this
function is **pure** — unit-testable by mocking the strip-forces boundary
with no aerosandbox dependency (per the CI fast-tier convention).

Reference: Cessna 172N @ V=30 m/s, α=2°, ISA SL → root BM ≈ 4005 N·m/half.
"""

from __future__ import annotations

from typing import Any

from app.schemas.spanwise_loads import (
    SpanwiseLoadEntry,
    SpanwiseLoadsResponse,
    SurfaceSpanwiseLoads,
)


def _integrate_half(
    strips_outboard_first: list[dict[str, Any]],
    q: float,
) -> tuple[list[SpanwiseLoadEntry], float, float]:
    """Discrete spanwise integration from tip to root for one half-span.

    For each station y_j (processed outboard → inboard):
        V(y_j) = Σ_{k: |y_k| ≥ |y_j|} L_k   (shear at this station)
        M(y_j) = Σ_{k: |y_k| ≥ |y_j|} L_k · (|y_k| - |y_j|)

    Root values are evaluated at y=0 (wing centreline), not at the
    innermost strip's own y-position, so M(root) = Σ L_k · |y_k|.

    Args:
        strips_outboard_first: strips sorted from tip inward, each with
            keys ``"Yle"``, ``"Area"``, ``"cl"``, ``"Chord"``.
        q: dynamic pressure (Pa).

    Returns:
        Tuple of:
          - List of `SpanwiseLoadEntry` in outboard-first order.
            At the outermost strip M = 0; shear increases toward root.
          - Root shear (N) = total half-span lift (at y=0).
          - Root bending moment (N·m) = Σ L_k · |y_k| (at y=0).
    """
    if not strips_outboard_first:
        return [], 0.0, 0.0

    # Pre-compute per-strip lift and |y|
    lifts = [q * float(s["Area"]) * float(s["cl"]) for s in strips_outboard_first]
    ys = [abs(float(s["Yle"])) for s in strips_outboard_first]

    entries: list[SpanwiseLoadEntry] = []

    for j, strip in enumerate(strips_outboard_first):
        y_j = ys[j]
        # V(y_j) = sum of lifts for strips k where |y_k| >= |y_j|
        #         = lifts[0..j] (outboard + this strip itself)
        shear = sum(lifts[: j + 1])

        # M(y_j) = sum_{k=0}^{j} L_k * (|y_k| - |y_j|)
        bm = sum(lifts[k] * (ys[k] - y_j) for k in range(j + 1))

        entries.append(
            SpanwiseLoadEntry(
                y_m=y_j,
                chord_m=float(strip["Chord"]),
                shear_N=shear,
                bending_moment_Nm=bm,
            )
        )

    # Root values at y=0 (wing centreline): V(0) = Σ L_k, M(0) = Σ L_k * |y_k|
    root_shear = sum(lifts)
    root_bm = sum(lifts[k] * ys[k] for k in range(len(lifts)))

    return entries, root_shear, root_bm


def compute_spanwise_loads(
    strip_forces_result: dict[str, Any],
    q: float,
) -> SpanwiseLoadsResponse:
    """Integrate strip forces into spanwise shear and bending-moment distributions.

    Args:
        strip_forces_result: A dict compatible with `StripForcesResponse`
            (or the raw dict from `_strip_surfaces_from_result`).  Must
            contain a ``"surfaces"`` key with per-surface strip data.
            Also reads ``"alpha"``, ``"velocity_mps"``, ``"altitude_m"``.
        q: dynamic pressure (Pa) = ½·ρ·V².  The caller must compute this
            from the operating point so the integrator stays pure.

    Returns:
        `SpanwiseLoadsResponse` with per-surface shear/BM distributions.
    """
    raw_surfaces: list[dict[str, Any]] = strip_forces_result.get("surfaces", [])
    alpha = float(strip_forces_result.get("alpha", 0.0))
    velocity_mps = float(strip_forces_result.get("velocity_mps", 0.0))
    altitude_m = float(strip_forces_result.get("altitude_m", 0.0))

    surface_results: list[SurfaceSpanwiseLoads] = []

    for surface in raw_surfaces:
        # Normalise: strips may be either raw dicts or StripForceEntry objects.
        raw_strips: list[Any] = surface.get("strips", [])
        strips: list[dict[str, Any]] = []
        for s in raw_strips:
            if isinstance(s, dict):
                strips.append(s)
            else:
                # Pydantic model — convert to dict via model_dump / __dict__
                try:
                    strips.append(s.model_dump(by_alias=True))
                except AttributeError:
                    strips.append(vars(s))

        # Split into port (y < 0) and starboard (y >= 0) halves
        starboard_strips = [s for s in strips if float(s["Yle"]) >= 0.0]
        port_strips = [s for s in strips if float(s["Yle"]) < 0.0]

        # Sort each half outboard-first (largest |y| first)
        starboard_strips.sort(key=lambda s: -float(s["Yle"]))
        port_strips.sort(key=lambda s: float(s["Yle"]))  # most negative y first

        sb_entries, sb_root_shear, sb_root_bm = _integrate_half(starboard_strips, q)
        pt_entries, pt_root_shear, pt_root_bm = _integrate_half(port_strips, q)

        surface_results.append(
            SurfaceSpanwiseLoads(
                surface_name=str(surface.get("surface_name", "")),
                starboard=sb_entries,
                port=pt_entries,
                root_shear_N_starboard=sb_root_shear,
                root_shear_N_port=pt_root_shear,
                root_bending_moment_Nm_starboard=sb_root_bm,
                root_bending_moment_Nm_port=pt_root_bm,
            )
        )

    return SpanwiseLoadsResponse(
        alpha=alpha,
        velocity_mps=velocity_mps,
        altitude_m=altitude_m,
        dynamic_pressure_Pa=q,
        surfaces=surface_results,
    )
