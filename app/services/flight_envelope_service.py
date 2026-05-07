"""Flight envelope service — V-n curve computation, KPI derivation, and DB persistence."""

from __future__ import annotations

import logging
import math

from app.schemas.flight_envelope import (
    PerformanceKPI,
    VnCurve,
    VnMarker,
    VnPoint,
)

logger = logging.getLogger(__name__)

GRAVITY = 9.81


# ---------------------------------------------------------------------------
# Pure computation helpers (no DB)
# ---------------------------------------------------------------------------


def compute_vn_curve(
    mass_kg: float,
    cl_max: float,
    g_limit: float,
    wing_area_m2: float,
    rho: float = 1.225,
    v_max_mps: float = 28.0,
) -> VnCurve:
    """Compute the V-n diagram boundary curves.

    Returns a VnCurve with positive and negative boundary points from
    stall speed to dive speed (1.4 * v_max).
    """
    weight = mass_kg * GRAVITY
    v_stall = math.sqrt(2 * weight / (rho * wing_area_m2 * cl_max))
    v_dive = 1.4 * v_max_mps
    cl_min = -0.8 * cl_max

    n_points = 60  # > 50 as required

    positive: list[VnPoint] = []
    negative: list[VnPoint] = []

    for i in range(n_points):
        v = v_stall + (v_dive - v_stall) * i / (n_points - 1)
        q = 0.5 * rho * v**2

        n_pos = min(q * wing_area_m2 * cl_max / weight, g_limit)
        n_neg = max(q * wing_area_m2 * cl_min / weight, -0.4 * g_limit)

        positive.append(VnPoint(velocity_mps=round(v, 6), load_factor=round(n_pos, 6)))
        negative.append(VnPoint(velocity_mps=round(v, 6), load_factor=round(n_neg, 6)))

    return VnCurve(
        positive=positive,
        negative=negative,
        dive_speed_mps=round(v_dive, 6),
        stall_speed_mps=round(v_stall, 6),
    )


def derive_performance_kpis(
    stall_speed_mps: float,
    v_max_mps: float,
    g_limit: float,
    markers: list[VnMarker],
) -> list[PerformanceKPI]:
    """Derive 6 KPIs from the flight envelope and operating-point markers.

    Always returns exactly 6 KPIs: stall_speed, best_ld_speed,
    min_sink_speed, max_speed, max_load_factor, dive_speed.
    """
    markers_by_label: dict[str, VnMarker] = {m.label: m for m in markers}

    kpis: list[PerformanceKPI] = []

    # 1. stall_speed
    kpis.append(
        PerformanceKPI(
            label="stall_speed",
            display_name="Stall Speed",
            value=round(stall_speed_mps, 4),
            unit="m/s",
            source_op_id=None,
            confidence="limit",
        )
    )

    # 2. best_ld_speed
    best_ld_marker = markers_by_label.get("best_ld")
    if best_ld_marker is not None:
        kpis.append(
            PerformanceKPI(
                label="best_ld_speed",
                display_name="Best L/D Speed",
                value=round(best_ld_marker.velocity_mps, 4),
                unit="m/s",
                source_op_id=best_ld_marker.op_id,
                confidence="trimmed",
            )
        )
    else:
        kpis.append(
            PerformanceKPI(
                label="best_ld_speed",
                display_name="Best L/D Speed",
                value=round(1.4 * stall_speed_mps, 4),
                unit="m/s",
                source_op_id=None,
                confidence="estimated",
            )
        )

    # 3. min_sink_speed
    min_sink_marker = markers_by_label.get("min_sink")
    if min_sink_marker is not None:
        kpis.append(
            PerformanceKPI(
                label="min_sink_speed",
                display_name="Min Sink Speed",
                value=round(min_sink_marker.velocity_mps, 4),
                unit="m/s",
                source_op_id=min_sink_marker.op_id,
                confidence="trimmed",
            )
        )
    else:
        kpis.append(
            PerformanceKPI(
                label="min_sink_speed",
                display_name="Min Sink Speed",
                value=round(1.2 * stall_speed_mps, 4),
                unit="m/s",
                source_op_id=None,
                confidence="estimated",
            )
        )

    # 4. max_speed
    kpis.append(
        PerformanceKPI(
            label="max_speed",
            display_name="Max Speed",
            value=round(v_max_mps, 4),
            unit="m/s",
            source_op_id=None,
            confidence="limit",
        )
    )

    # 5. max_load_factor
    max_turn_marker = markers_by_label.get("max_turn")
    if max_turn_marker is not None:
        kpis.append(
            PerformanceKPI(
                label="max_load_factor",
                display_name="Max Load Factor",
                value=round(max_turn_marker.load_factor, 4),
                unit="g",
                source_op_id=max_turn_marker.op_id,
                confidence="trimmed",
            )
        )
    else:
        kpis.append(
            PerformanceKPI(
                label="max_load_factor",
                display_name="Max Load Factor",
                value=round(g_limit, 4),
                unit="g",
                source_op_id=None,
                confidence="limit",
            )
        )

    # 6. dive_speed
    kpis.append(
        PerformanceKPI(
            label="dive_speed",
            display_name="Dive Speed",
            value=round(1.4 * v_max_mps, 4),
            unit="m/s",
            source_op_id=None,
            confidence="limit",
        )
    )

    return kpis
