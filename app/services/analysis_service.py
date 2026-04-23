"""
Analysis Service - Business logic for aerodynamic analysis operations.

This module contains the core logic for aerodynamic analysis,
separated from HTTP concerns for better testability and reusability.
"""

import io
import logging
import os
from datetime import datetime
from urllib.parse import urljoin
from typing import Any, List, Optional
from uuid import uuid4

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from aerosandbox import Airplane
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.utils import analyse_aerodynamics, compile_four_view_figure
from app.converters.model_schema_converters import aeroplane_schema_to_asb_airplane_async
from app.core.exceptions import NotFoundError, InternalError
from app.db.exceptions import NotFoundInDbException
from app.db.repository import get_wing_by_name_and_aeroplane_id, get_aeroplane_by_id
from app.schemas import AeroplaneSchema
from app.schemas.AeroplaneRequest import AnalysisToolUrlType, AlphaSweepRequest, SimpleSweepRequest
from app.schemas.aeroanalysisschema import OperatingPointSchema
from app.schemas.strip_forces import StripForcesResponse, SurfaceStripForces, StripForceEntry

logger = logging.getLogger(__name__)

# --- Shared plot color / label constants (S1192) ---
_COLOR_GREEN = "tab:green"
_COLOR_BLUE = "tab:blue"
_COLOR_RED = "tab:red"
_COLOR_ORANGE = "tab:orange"
_COLOR_BROWN = "tab:brown"
_LABEL_ALPHA_DEG = "Alpha [deg]"

# --- Characteristic point marker styles and labels ---
_MARKER_STYLES: dict[str, str] = {
    "maximum_lift_to_drag_ratio_point": _COLOR_GREEN,
    "minimum_drag_coefficient_point": _COLOR_BLUE,
    "maximum_lift_coefficient_point": _COLOR_RED,
    "drag_at_zero_lift_point": "tab:purple",
    "stall_point": _COLOR_ORANGE,
    "trim_point_cm_equals_zero": _COLOR_BROWN,
}
_LABEL_NAMES: dict[str, str] = {
    "maximum_lift_to_drag_ratio_point": "(CL/CD)max",
    "minimum_drag_coefficient_point": "CDmin",
    "maximum_lift_coefficient_point": "CLmax",
    "drag_at_zero_lift_point": "CD0",
    "stall_point": "Stall",
    "trim_point_cm_equals_zero": "Trim (Cm=0)",
}


def _safe_slice(
    *arrays: Optional[np.ndarray],
) -> Optional[tuple[np.ndarray, ...]]:
    """Align arrays to shortest length. Returns None if any input is None or empty."""
    if any(a is None for a in arrays):
        return None
    n = min(len(a) for a in arrays)
    if n == 0:
        return None
    return tuple(a[:n] for a in arrays)


def _extract_alpha_sweep_arrays(
    result: Any, sweep_request: AlphaSweepRequest
) -> tuple[np.ndarray, Optional[np.ndarray], Optional[np.ndarray], Optional[np.ndarray]]:
    alpha_values = None
    if getattr(result, "flight_condition", None) is not None:
        alpha_values = getattr(result.flight_condition, "alpha", None)
    if alpha_values is None:
        alpha_values = np.linspace(
            start=sweep_request.alpha_start,
            stop=sweep_request.alpha_end,
            num=sweep_request.alpha_num,
        )
    alpha_array = np.atleast_1d(np.asarray(alpha_values, dtype=float))

    cl_values = cd_values = cm_values = None
    if getattr(result, "coefficients", None) is not None:
        if getattr(result.coefficients, "CL", None) is not None:
            cl_values = np.atleast_1d(np.asarray(result.coefficients.CL, dtype=float))
        if getattr(result.coefficients, "CD", None) is not None:
            cd_values = np.atleast_1d(np.asarray(result.coefficients.CD, dtype=float))
        if getattr(result.coefficients, "Cm", None) is not None:
            cm_values = np.atleast_1d(np.asarray(result.coefficients.Cm, dtype=float))

    return alpha_array, cl_values, cd_values, cm_values


def _compute_cl_cd_points(alpha: np.ndarray, cl: np.ndarray, cd: np.ndarray, n: int) -> dict:
    """Compute characteristic points from CL and CD arrays."""
    points: dict = {}

    with np.errstate(divide="ignore", invalid="ignore"):
        ld = np.where(np.abs(cd) > 1e-12, cl / cd, np.nan)
    if np.isfinite(ld).any():
        i = int(np.nanargmax(ld))
        points["maximum_lift_to_drag_ratio_point"] = {
            "index": i,
            "alpha_deg": float(alpha[i]),
            "CL": float(cl[i]),
            "CD": float(cd[i]),
            "Cm": None,
            "lift_to_drag_ratio": float(ld[i]),
        }

    i = int(np.argmin(cd))
    points["minimum_drag_coefficient_point"] = {
        "index": i,
        "alpha_deg": float(alpha[i]),
        "CL": float(cl[i]),
        "CD": float(cd[i]),
        "Cm": None,
    }

    i = int(np.argmax(cl))
    points["maximum_lift_coefficient_point"] = {
        "index": i,
        "alpha_deg": float(alpha[i]),
        "CL": float(cl[i]),
        "CD": float(cd[i]),
        "Cm": None,
    }

    points["drag_at_zero_lift_point"] = _interpolate_zero_crossing(alpha, cl, cd)
    points["stall_point"] = _find_stall_point(alpha, cl, cd, n)
    return points


def _interpolate_zero_crossing(alpha, cl, cd) -> dict:
    """Find the drag-at-zero-lift point via interpolation or nearest."""
    cross = np.nonzero(np.sign(cl[:-1]) != np.sign(cl[1:]))[0]
    if len(cross) > 0:
        i = int(cross[0])
        cl0, cl1 = cl[i], cl[i + 1]
        t = 0.0 if abs(cl1 - cl0) <= 1e-12 else -cl0 / (cl1 - cl0)
        return {
            "index": None,
            "alpha_deg": float(alpha[i] + t * (alpha[i + 1] - alpha[i])),
            "CL": 0.0,
            "CD": float(cd[i] + t * (cd[i + 1] - cd[i])),
            "Cm": None,
        }
    i = int(np.argmin(np.abs(cl)))
    return {
        "index": i,
        "alpha_deg": float(alpha[i]),
        "CL": float(cl[i]),
        "CD": float(cd[i]),
        "Cm": None,
    }


def _find_stall_point(alpha, cl, cd, n: int) -> dict:
    """Find the stall point after CLmax."""
    i_clmax = int(np.argmax(cl))
    i_stall = i_clmax
    if i_clmax < n - 1:
        for i in range(i_clmax + 1, n):
            if cl[i] < cl[i - 1] and cd[i] > cd[i - 1]:
                i_stall = i
                break
        else:
            i_stall = min(i_clmax + 1, n - 1)
    return {
        "index": i_stall,
        "alpha_deg": float(alpha[i_stall]),
        "CL": float(cl[i_stall]),
        "CD": float(cd[i_stall]),
        "Cm": None,
    }


def _compute_trim_point(
    alpha: np.ndarray,
    cl: np.ndarray,
    cm: np.ndarray,
    cd_values: Optional[np.ndarray],
) -> dict:
    """Find the trim point where Cm crosses zero."""
    cross = np.nonzero(np.sign(cm[:-1]) != np.sign(cm[1:]))[0]
    if len(cross) > 0:
        i = int(cross[0])
        cm0, cm1 = cm[i], cm[i + 1]
        t = 0.0 if abs(cm1 - cm0) <= 1e-12 else -cm0 / (cm1 - cm0)
        cd_trim = None
        if cd_values is not None and len(cd_values) > i + 1:
            cd_trim = float(cd_values[i] + t * (cd_values[i + 1] - cd_values[i]))
        return {
            "index": None,
            "alpha_deg": float(alpha[i] + t * (alpha[i + 1] - alpha[i])),
            "CL": float(cl[i] + t * (cl[i + 1] - cl[i])),
            "CD": cd_trim,
            "Cm": 0.0,
        }
    i = int(np.argmin(np.abs(cm)))
    return {
        "index": i,
        "alpha_deg": float(alpha[i]),
        "CL": float(cl[i]),
        "CD": float(cd_values[i]) if cd_values is not None and len(cd_values) > i else None,
        "Cm": float(cm[i]),
    }


def _compute_alpha_sweep_characteristic_points(
    alpha_array: np.ndarray,
    cl_values: Optional[np.ndarray],
    cd_values: Optional[np.ndarray],
    cm_values: Optional[np.ndarray],
) -> dict:
    points = {
        "maximum_lift_to_drag_ratio_point": None,
        "minimum_drag_coefficient_point": None,
        "maximum_lift_coefficient_point": None,
        "drag_at_zero_lift_point": None,
        "stall_point": None,
        "trim_point_cm_equals_zero": None,
    }

    if cl_values is not None and cd_values is not None:
        n = min(len(cl_values), len(cd_values), len(alpha_array))
        if n > 0:
            cl_cd_points = _compute_cl_cd_points(alpha_array[:n], cl_values[:n], cd_values[:n], n)
            points.update(cl_cd_points)

    if cl_values is not None and cm_values is not None:
        n = min(len(cl_values), len(cm_values), len(alpha_array))
        if n > 0:
            points["trim_point_cm_equals_zero"] = _compute_trim_point(
                alpha_array[:n],
                cl_values[:n],
                cm_values[:n],
                cd_values,
            )

    return points


def get_aeroplane_schema_or_raise(db: Session, aeroplane_uuid) -> AeroplaneSchema:
    """
    Get an aeroplane schema by UUID.

    Raises:
        NotFoundError: If the aeroplane does not exist.
        InternalError: If a database error occurs.
    """
    try:
        return get_aeroplane_by_id(aeroplane_uuid, db)
    except NotFoundInDbException as e:
        raise NotFoundError(message=str(e), details={"aeroplane_id": str(aeroplane_uuid)})
    except SQLAlchemyError as e:
        logger.error(f"Database error when getting aeroplane: {e}")
        raise InternalError(message=f"Database error: {e}")


def get_wing_schema_or_raise(db: Session, aeroplane_uuid, wing_name: str) -> AeroplaneSchema:
    """
    Get an aeroplane schema with only the specified wing.

    Raises:
        NotFoundError: If the aeroplane or wing does not exist.
        InternalError: If a database error occurs.
    """
    try:
        return get_wing_by_name_and_aeroplane_id(aeroplane_uuid, wing_name, db)
    except NotFoundInDbException as e:
        raise NotFoundError(
            message=str(e), details={"aeroplane_id": str(aeroplane_uuid), "wing_name": wing_name}
        )
    except SQLAlchemyError as e:
        logger.error(f"Database error when getting wing: {e}")
        raise InternalError(message=f"Database error: {e}")


async def analyze_wing(
    db: Session,
    aeroplane_uuid,
    wing_name: str,
    operating_point: OperatingPointSchema,
    analysis_tool: AnalysisToolUrlType,
) -> Any:
    """
    Analyze a single wing using the specified analysis tool.

    Raises:
        NotFoundError: If the aeroplane or wing does not exist.
        InternalError: If an analysis error occurs.
    """
    plane_schema = get_wing_schema_or_raise(db, aeroplane_uuid, wing_name)

    try:
        asb_airplane: Airplane = aeroplane_schema_to_asb_airplane_async(
            plane_schema=plane_schema
        )
        asb_airplane.xyz_ref = operating_point.xyz_ref
        asb_airplane.wings = [w for w in asb_airplane.wings if w.name == wing_name]
        asb_airplane.fuselages = []

        result, _ = analyse_aerodynamics(analysis_tool, operating_point, asb_airplane)
        return result
    except Exception as e:
        logger.error(f"Error analyzing wing: {e}")
        raise InternalError(message=f"Analysis error: {e}")


async def analyze_airplane(
    db: Session,
    aeroplane_uuid,
    operating_point: OperatingPointSchema,
    analysis_tool: AnalysisToolUrlType,
) -> Any:
    """
    Analyze a complete airplane using the specified analysis tool.

    Raises:
        NotFoundError: If the aeroplane does not exist.
        InternalError: If an analysis error occurs.
    """
    plane_schema = get_aeroplane_schema_or_raise(db, aeroplane_uuid)

    try:
        asb_airplane: Airplane = aeroplane_schema_to_asb_airplane_async(
            plane_schema=plane_schema
        )
        result, _ = analyse_aerodynamics(analysis_tool, operating_point, asb_airplane)
        return result
    except Exception as e:
        logger.error(f"Error analyzing airplane: {e}")
        raise InternalError(message=f"Analysis error: {e}")


async def calculate_streamlines_json(
    db: Session,
    aeroplane_uuid,
    operating_point: OperatingPointSchema,
) -> dict:
    """Calculate streamlines and return Plotly figure as JSON dict.

    Returns:
        dict: Plotly figure JSON with 'data' and 'layout' keys.

    Raises:
        NotFoundError: If the aeroplane does not exist.
        InternalError: If an analysis error occurs.
    """
    import json as _json

    plane_schema = get_aeroplane_schema_or_raise(db, aeroplane_uuid)

    try:
        asb_airplane: Airplane = aeroplane_schema_to_asb_airplane_async(
            plane_schema=plane_schema
        )
        _, figure = analyse_aerodynamics(
            AnalysisToolUrlType.VORTEX_LATTICE,
            operating_point,
            asb_airplane,
            draw_streamlines=True,
        )
        return _json.loads(figure.to_json())
    except Exception as e:
        logger.error("Error calculating streamlines: %s", e)
        raise InternalError(message=f"Analysis error: {e}")


async def analyze_alpha_sweep(db: Session, aeroplane_uuid, sweep_request: AlphaSweepRequest) -> Any:
    """
    Perform an angle of attack sweep.

    Raises:
        NotFoundError: If the aeroplane does not exist.
        InternalError: If an analysis error occurs.
    """
    plane_schema = get_aeroplane_schema_or_raise(db, aeroplane_uuid)

    try:
        asb_airplane: Airplane = aeroplane_schema_to_asb_airplane_async(
            plane_schema=plane_schema
        )

        operating_point = OperatingPointSchema(
            altitude=sweep_request.altitude,
            velocity=sweep_request.velocity,
            alpha=np.linspace(
                start=sweep_request.alpha_start,
                stop=sweep_request.alpha_end,
                num=sweep_request.alpha_num,
            ),
            beta=sweep_request.beta,
            p=sweep_request.p,
            q=sweep_request.q,
            r=sweep_request.r,
            xyz_ref=sweep_request.xyz_ref,
        )

        result, _ = analyse_aerodynamics(
            AnalysisToolUrlType.AEROBUILDUP, operating_point, asb_airplane
        )
        alpha_array, cl_values, cd_values, cm_values = _extract_alpha_sweep_arrays(
            result, sweep_request
        )
        characteristic_points = _compute_alpha_sweep_characteristic_points(
            alpha_array, cl_values, cd_values, cm_values
        )
        return {
            "analysis": result,
            "characteristic_points": characteristic_points,
            "aircraft_name": getattr(plane_schema, "name", str(aeroplane_uuid)),
        }
    except Exception as e:
        logger.error(f"Error in alpha sweep: {e}")
        raise InternalError(message=f"Analysis error: {e}")


# ---------------------------------------------------------------------------
# Alpha-sweep diagram: module-level helpers extracted from the monolith
# ---------------------------------------------------------------------------


def _annotate_with_collision_avoidance(
    ax: Any,
    points_with_labels: list[tuple[float, float, str, str]],
) -> None:
    """Place annotations with simple offset-collision heuristic."""
    used: list[tuple[float, float, int, int]] = []
    candidate_offsets = [
        (12, 12),
        (12, -14),
        (-70, 14),
        (-70, -14),
        (36, 26),
        (36, -26),
        (-96, 26),
        (-96, -26),
    ]
    for x, y, label, color in points_with_labels:
        chosen = candidate_offsets[0]
        for ox, oy in candidate_offsets:
            if all(abs(ox - uox) > 20 or abs(oy - uoy) > 12 for _, _, uox, uoy in used):
                chosen = (ox, oy)
                break
        used.append((x, y, chosen[0], chosen[1]))
        ax.annotate(
            label,
            xy=(x, y),
            xytext=chosen,
            textcoords="offset points",
            fontsize=8,
            color=color,
            bbox={
                "boxstyle": "round,pad=0.25",
                "facecolor": "white",
                "edgecolor": color,
                "linewidth": 0.8,
                "alpha": 0.9,
            },
            arrowprops={
                "arrowstyle": "-",
                "linestyle": ":",
                "color": color,
                "linewidth": 0.9,
            },
        )


def _add_trend_strip(
    ax: Any,
    x_vals: np.ndarray,
    color_vals: list[str],
    strip_label: str,
) -> None:
    """Render a thin colour-coded trend strip below *ax*."""
    if len(x_vals) == 0 or len(color_vals) == 0:
        return
    n = min(len(x_vals), len(color_vals))
    x = np.asarray(x_vals[:n], dtype=float)
    if n == 1:
        edges = np.array([x[0] - 0.5, x[0] + 0.5], dtype=float)
    else:
        mids = (x[:-1] + x[1:]) / 2.0
        edges = np.concatenate(([x[0] - (mids[0] - x[0])], mids, [x[-1] + (x[-1] - mids[-1])]))

    strip_ax = ax.inset_axes([0.06, -0.20, 0.88, 0.07])
    for i in range(n):
        strip_ax.axvspan(edges[i], edges[i + 1], color=color_vals[i], ec=None)
    strip_ax.set_xlim(edges[0], edges[-1])
    strip_ax.set_ylim(0, 1)
    strip_ax.set_yticks([])
    strip_ax.set_xticks([])
    for spine in strip_ax.spines.values():
        spine.set_visible(False)
    strip_ax.text(
        0.0,
        0.5,
        strip_label,
        transform=strip_ax.transAxes,
        va="center",
        ha="left",
        fontsize=8,
    )


def _classify_longitudinal_stability(
    cm_vals: Optional[np.ndarray],
    alpha_vals: np.ndarray,
) -> tuple[str, str]:
    """Classify longitudinal stability from dCm/d-alpha slope."""
    if cm_vals is None:
        return "N/A", "gray"
    n = min(len(cm_vals), len(alpha_vals))
    if n < 2:
        return "N/A", "gray"
    x = np.asarray(alpha_vals[:n], dtype=float)
    y = np.asarray(cm_vals[:n], dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    if np.count_nonzero(mask) < 2:
        return "N/A", "gray"
    slope = np.polyfit(x[mask], y[mask], 1)[0]
    if slope < -0.01:
        return f"Stable (dCm/da={slope:.4f})", _COLOR_GREEN
    if slope <= 0.01:
        return f"Neutral (dCm/da={slope:.4f})", _COLOR_ORANGE
    return f"Unstable (dCm/da={slope:.4f})", _COLOR_RED


def _classify_variation(
    series: Optional[np.ndarray],
    label: str,
) -> tuple[str, str]:
    """Classify a series as robust / moderate / volatile."""
    if series is None or len(series) < 2:
        return f"{label}: N/A", "gray"
    values = np.asarray(series, dtype=float)
    values = values[np.isfinite(values)]
    if len(values) < 2:
        return f"{label}: N/A", "gray"
    span = float(np.max(values) - np.min(values))
    if span < 0.5:
        return f"{label}: robust (span={span:.3f})", _COLOR_GREEN
    if span < 2.0:
        return f"{label}: moderate (span={span:.3f})", _COLOR_ORANGE
    return f"{label}: volatile (span={span:.3f})", _COLOR_RED


def _extract_reference_arrays(
    result: Any,
) -> tuple[Optional[np.ndarray], Optional[np.ndarray]]:
    """Extract Xnp and Xnp_lat arrays from *result.reference*."""
    xnp_values = None
    if (
        getattr(result, "reference", None) is not None
        and getattr(result.reference, "Xnp", None) is not None
    ):
        xnp_values = np.atleast_1d(np.asarray(result.reference.Xnp, dtype=float))
    xnp_lat_values = None
    if (
        getattr(result, "reference", None) is not None
        and getattr(result.reference, "Xnp_lat", None) is not None
    ):
        xnp_lat_values = np.atleast_1d(np.asarray(result.reference.Xnp_lat, dtype=float))
    return xnp_values, xnp_lat_values


def _extract_force_arrays(
    result: Any,
) -> tuple[Optional[np.ndarray], Optional[np.ndarray]]:
    """Extract lift and drag force arrays from *result.forces*."""
    lift_values = drag_values = None
    if getattr(result, "forces", None) is not None:
        if getattr(result.forces, "L", None) is not None:
            lift_values = np.atleast_1d(np.asarray(result.forces.L, dtype=float))
        if getattr(result.forces, "D", None) is not None:
            drag_values = np.atleast_1d(np.asarray(result.forces.D, dtype=float))
    return lift_values, drag_values


# --- Panel 1: Coefficients vs Alpha ---


def _plot_coefficient_curves(
    ax: Any,
    alpha_array: np.ndarray,
    cl_values: Optional[np.ndarray],
    cd_values: Optional[np.ndarray],
    cm_values: Optional[np.ndarray],
) -> bool:
    """Plot CL, CD, Cm curves on *ax*. Return True if anything was plotted."""
    plotted = False
    for values, label in [(cl_values, "CL"), (cd_values, "CD"), (cm_values, "Cm")]:
        if values is not None:
            length = min(len(alpha_array), len(values))
            if length > 0:
                ax.plot(alpha_array[:length], values[:length], label=label, linewidth=2)
                plotted = True
    return plotted


# --- Panel 2: CL vs CD polar ---


def _format_polar_label(key: str, point: dict, x_val: float, y_val: float) -> str:
    """Build the annotation string for a characteristic point on the polar."""
    name = _LABEL_NAMES[key]
    if key == "maximum_lift_to_drag_ratio_point" and point.get("lift_to_drag_ratio") is not None:
        return f"{name}={point['lift_to_drag_ratio']:.2f}\nCD={x_val:.3f}, CL={y_val:.3f}"
    if key == "minimum_drag_coefficient_point":
        return f"{name}={x_val:.3f}\nCL={y_val:.3f}"
    if key == "maximum_lift_coefficient_point":
        return f"{name}={y_val:.3f}\nCD={x_val:.3f}"
    if key == "drag_at_zero_lift_point":
        return f"{name}={x_val:.3f}"
    return f"{name}\nCD={x_val:.3f}, CL={y_val:.3f}"


def _scatter_characteristic_points(
    ax: Any,
    characteristic_points: dict,
) -> list[tuple[float, float, str, str]]:
    """Scatter characteristic points on the polar panel and return labels."""
    polar_point_labels: list[tuple[float, float, str, str]] = []
    for key, point in characteristic_points.items():
        if point is None or point.get("CD") is None or point.get("CL") is None:
            continue
        x_val, y_val = point["CD"], point["CL"]
        ax.scatter(x_val, y_val, color=_MARKER_STYLES[key], s=35, zorder=5)
        polar_point_labels.append(
            (x_val, y_val, _format_polar_label(key, point, x_val, y_val), _MARKER_STYLES[key])
        )
    return polar_point_labels


def _resolve_alpha_marker(
    point: dict,
    key: str,
    alpha_val: float,
    text: str,
) -> tuple[float, str] | None:
    """Return (y_value, label) for a characteristic point on the alpha panel, or None."""
    if key == "minimum_drag_coefficient_point":
        y_val = point.get("CD")
        if y_val is None:
            return None
        return y_val, f"{text}={y_val:.3f} @ a={alpha_val:.2f}"
    y_val = point.get("CL")
    if y_val is None:
        return None
    return y_val, f"{text} @ a={alpha_val:.2f}, CL={y_val:.3f}"


def _mirror_markers_to_alpha_panel(
    ax_coeff: Any,
    alpha_polar: np.ndarray,
    characteristic_points: dict,
) -> list[tuple[float, float, str, str]]:
    """Mirror select characteristic-point markers onto the coefficient-vs-alpha panel."""
    alpha_point_labels: list[tuple[float, float, str, str]] = []
    alpha_len = len(alpha_polar)
    if alpha_len == 0:
        return alpha_point_labels

    for key, color, text in [
        ("minimum_drag_coefficient_point", _COLOR_BLUE, "CDmin"),
        ("maximum_lift_coefficient_point", _COLOR_RED, "CLmax"),
        ("stall_point", _COLOR_ORANGE, "Stall"),
    ]:
        point = characteristic_points.get(key)
        if not point:
            continue
        idx = point.get("index")
        if idx is None or idx >= alpha_len:
            continue
        resolved = _resolve_alpha_marker(point, key, alpha_polar[idx], text)
        if resolved is None:
            continue
        y_val, label = resolved
        ax_coeff.scatter(alpha_polar[idx], y_val, color=color, s=25, zorder=5)
        alpha_point_labels.append((alpha_polar[idx], y_val, label, color))
    return alpha_point_labels


def _plot_drag_polar(
    ax: Any,
    ax_coeff: Any,
    alpha_array: np.ndarray,
    cl_values: Optional[np.ndarray],
    cd_values: Optional[np.ndarray],
    characteristic_points: dict,
) -> tuple[bool, list, list]:
    """Plot CL-vs-CD polar with markers. Return (plotted, polar_labels, alpha_labels)."""
    sliced = _safe_slice(cl_values, cd_values)
    if sliced is None:
        return False, [], []

    cl_polar, cd_polar = sliced
    alpha_polar = alpha_array[: len(cl_polar)]

    ax.plot(cd_polar, cl_polar, linewidth=2, label="Polar Curve")

    polar_point_labels = _scatter_characteristic_points(ax, characteristic_points)

    # L/D max tangent line
    ldmax = characteristic_points.get("maximum_lift_to_drag_ratio_point")
    if ldmax and ldmax.get("CD") is not None and ldmax.get("CL") is not None:
        ax.plot(
            [0.0, ldmax["CD"]],
            [0.0, ldmax["CL"]],
            linestyle="--",
            linewidth=1.2,
            color="gray",
            alpha=0.8,
        )

    alpha_point_labels = _mirror_markers_to_alpha_panel(
        ax_coeff, alpha_polar, characteristic_points
    )

    return True, polar_point_labels, alpha_point_labels


# --- Panel 3: CL vs Cm stability ---


def _compute_cm_strip_colors(cm_grad: np.ndarray) -> list[str]:
    """Map dCm/dalpha gradient values to stability colours."""
    colors: list[str] = []
    for g in cm_grad:
        if not np.isfinite(g):
            colors.append("lightgray")
        elif g < -0.01:
            colors.append("#4caf50")  # stable
        elif g <= 0.01:
            colors.append("#ffb74d")  # marginal
        else:
            colors.append("#e57373")  # unstable
    return colors


def _scatter_trim_point(
    ax_cm: Any,
    ax_coeff: Any,
    ax_polar: Any,
    characteristic_points: dict,
) -> tuple[list[tuple[float, float, str, str]], list[tuple[float, float, str, str]], list[tuple[float, float, str, str]]]:
    """Scatter the trim-point marker across the Cm, coefficient, and polar panels."""
    cm_point_labels: list[tuple[float, float, str, str]] = []
    extra_alpha_labels: list[tuple[float, float, str, str]] = []
    extra_polar_labels: list[tuple[float, float, str, str]] = []

    trim_point = characteristic_points.get("trim_point_cm_equals_zero")
    if not trim_point or trim_point.get("CL") is None:
        return cm_point_labels, extra_alpha_labels, extra_polar_labels

    cm_trim = trim_point.get("Cm") if trim_point.get("Cm") is not None else 0.0
    cl_trim = trim_point["CL"]
    alpha_trim = trim_point.get("alpha_deg")
    cd_trim = trim_point.get("CD")

    ax_cm.scatter(cm_trim, cl_trim, color=_COLOR_BROWN, s=35, zorder=5)
    cm_label = f"Trim (Cm=0): CL={cl_trim:.3f}"
    if alpha_trim is not None:
        cm_label += f", a={alpha_trim:.2f}"
    cm_point_labels.append((cm_trim, cl_trim, cm_label, _COLOR_BROWN))

    if alpha_trim is not None:
        ax_coeff.scatter(alpha_trim, 0.0, color=_COLOR_BROWN, s=25, zorder=5)
        extra_alpha_labels.append(
            (alpha_trim, 0.0, f"Trim (Cm=0) @ a={alpha_trim:.2f}", _COLOR_BROWN)
        )

    if cd_trim is not None:
        ax_polar.scatter(cd_trim, cl_trim, color=_COLOR_BROWN, s=35, zorder=5)
        extra_polar_labels.append(
            (cd_trim, cl_trim, f"Trim (Cm=0)\nCD={cd_trim:.3f}, CL={cl_trim:.3f}", _COLOR_BROWN)
        )

    return cm_point_labels, extra_alpha_labels, extra_polar_labels


def _plot_cm_stability(
    ax_cm: Any,
    ax_coeff: Any,
    ax_polar: Any,
    alpha_array: np.ndarray,
    cl_values: Optional[np.ndarray],
    cm_values: Optional[np.ndarray],
    characteristic_points: dict,
) -> tuple[bool, list, list, list]:
    """Plot CL-vs-Cm stability panel. Return (plotted, cm_labels, alpha_labels, polar_labels)."""
    sliced = _safe_slice(cl_values, cm_values)
    if sliced is None:
        return False, [], [], []

    cl_curve, cm_curve = sliced
    alpha_cm = alpha_array[: len(cl_curve)]

    with np.errstate(divide="ignore", invalid="ignore"):
        cm_grad = np.gradient(cm_curve, alpha_cm) if len(cm_curve) > 1 else np.array([np.nan])

    cm_strip_colors = _compute_cm_strip_colors(cm_grad)

    # Render CL-Cm as alpha-ordered colored path segments.
    if len(cm_curve) > 1:
        points = np.column_stack((cm_curve, cl_curve))
        segments = np.stack([points[:-1], points[1:]], axis=1)
        segment_colors = cm_strip_colors[1:] if len(cm_strip_colors) > 1 else ["#4caf50"]
        lc = LineCollection(segments, colors=segment_colors, linewidths=2.2, alpha=0.95)
        ax_cm.add_collection(lc)
        ax_cm.autoscale_view()
    else:
        ax_cm.plot(cm_curve, cl_curve, linewidth=2, color="#4caf50")

    # Trim point annotation
    cm_point_labels, extra_alpha_labels, extra_polar_labels = _scatter_trim_point(
        ax_cm, ax_coeff, ax_polar, characteristic_points
    )

    # Trend strips
    _add_trend_strip(ax_coeff, alpha_cm, cm_strip_colors, "Cm trend")
    _add_trend_strip(ax_cm, alpha_cm, cm_strip_colors, "Cm path trend")

    return True, cm_point_labels, extra_alpha_labels, extra_polar_labels


# --- Panel 4: Glide ratio L/D vs Alpha ---


def _plot_glide_ratio(
    ax: Any,
    alpha_array: np.ndarray,
    lift_values: Optional[np.ndarray],
    drag_values: Optional[np.ndarray],
) -> tuple[bool, list]:
    """Plot L/D vs alpha. Return (plotted, ld_point_labels)."""
    ld_point_labels: list[tuple[float, float, str, str]] = []

    sliced = _safe_slice(alpha_array, lift_values, drag_values)
    if sliced is None:
        return False, ld_point_labels

    alpha_ld, lift_curve, drag_curve = sliced
    with np.errstate(divide="ignore", invalid="ignore"):
        ld_curve = np.where(np.abs(drag_curve) > 1e-12, lift_curve / drag_curve, np.nan)

    ax.plot(alpha_ld, ld_curve, linewidth=2, color=_COLOR_GREEN, label="L/D")

    if np.isfinite(ld_curve).any():
        i_ldmax = int(np.nanargmax(ld_curve))
        ax.scatter(alpha_ld[i_ldmax], ld_curve[i_ldmax], color=_COLOR_GREEN, s=35, zorder=5)
        ld_point_labels.append(
            (
                alpha_ld[i_ldmax],
                ld_curve[i_ldmax],
                f"Sweet Spot\na={alpha_ld[i_ldmax]:.2f}, L/D={ld_curve[i_ldmax]:.2f}",
                _COLOR_GREEN,
            )
        )

    return True, ld_point_labels


# --- Panel 5: Neutral points Xnp / Xnp_lat vs Alpha ---


def _collect_xnp_outlier_labels(
    alpha_array: np.ndarray,
    xnp_values: Optional[np.ndarray],
) -> list[tuple[float, float, str, str]]:
    """Compute outlier labels for Xnp curve."""
    labels: list[tuple[float, float, str, str]] = []
    if xnp_values is None or len(xnp_values) == 0:
        return labels
    x_len = min(len(alpha_array), len(xnp_values))
    if x_len == 0:
        return labels
    xnp_curve = xnp_values[:x_len]
    median_xnp = float(np.nanmedian(xnp_curve))
    deviation = np.abs(xnp_curve - median_xnp)
    if np.isfinite(deviation).any():
        outlier_idx = int(np.nanargmax(deviation))
        outlier_alpha = alpha_array[min(outlier_idx, len(alpha_array) - 1)]
        labels.append(
            (
                outlier_alpha,
                xnp_curve[outlier_idx],
                f"Xnp Ausreißer?\na={outlier_alpha:.2f}, Xnp={xnp_curve[outlier_idx]:.3f}",
                _COLOR_RED,
            )
        )
    return labels


def _collect_xnp_lat_labels(
    ax: Any,
    alpha_array: np.ndarray,
    xnp_lat_values: Optional[np.ndarray],
) -> tuple[bool, list[tuple[float, float, str, str]]]:
    """Plot Xnp_lat curve and collect outlier / jump labels. Return (plotted, labels)."""
    labels: list[tuple[float, float, str, str]] = []
    sliced = _safe_slice(alpha_array, xnp_lat_values)
    if sliced is None:
        return False, labels

    x_axis, lat_curve = sliced
    ax.plot(x_axis, lat_curve, linewidth=2, color="tab:pink", label="Xnp_lat")

    median_lat = float(np.nanmedian(lat_curve))
    deviation_lat = np.abs(lat_curve - median_lat)
    if np.isfinite(deviation_lat).any():
        outlier_idx = int(np.nanargmax(deviation_lat))
        outlier_x = x_axis[outlier_idx]
        outlier_y = lat_curve[outlier_idx]
        labels.append(
            (
                outlier_x,
                outlier_y,
                f"Xnp_lat Ausreißer?\na={outlier_x:.2f}, Xnp_lat={outlier_y:.3f}",
                _COLOR_RED,
            )
        )

    if len(lat_curve) > 1:
        jumps = np.abs(np.diff(lat_curve))
        if np.isfinite(jumps).any():
            jump_idx = int(np.nanargmax(jumps)) + 1
            jump_x = x_axis[jump_idx]
            jump_y = lat_curve[jump_idx]
            labels.append((jump_x, jump_y, f"Xnp_lat Sprung\na={jump_x:.2f}", _COLOR_ORANGE))

    return True, labels


def _compute_neutral_strip_colors(
    xnp_curve: np.ndarray,
    xnp_lat_curve: np.ndarray,
    x_axis: np.ndarray,
    comb_len: int,
) -> list[str]:
    """Compute per-point stability colours for the neutral-point trend strip."""
    with np.errstate(divide="ignore", invalid="ignore"):
        gx = np.abs(np.gradient(xnp_curve, x_axis)) if comb_len > 1 else np.array([np.nan])
        gy = np.abs(np.gradient(xnp_lat_curve, x_axis)) if comb_len > 1 else np.array([np.nan])
    combined_metric = gx + gy
    valid = combined_metric[np.isfinite(combined_metric)]
    if len(valid) > 0:
        low_thr = float(np.percentile(valid, 50))
        high_thr = float(np.percentile(valid, 85))
    else:
        low_thr, high_thr = 0.0, 0.0
    colors: list[str] = []
    for m in combined_metric:
        if not np.isfinite(m):
            colors.append("lightgray")
        elif m <= low_thr:
            colors.append("#4caf50")  # robust
        elif m <= high_thr:
            colors.append("#ffb74d")  # moderate
        else:
            colors.append("#e57373")  # critical
    return colors


def _plot_neutral_points(
    ax: Any,
    alpha_array: np.ndarray,
    xnp_values: Optional[np.ndarray],
    xnp_lat_values: Optional[np.ndarray],
) -> tuple[bool, list]:
    """Plot combined Xnp and Xnp_lat panel. Return (plotted, labels)."""
    neutral_labels: list[tuple[float, float, str, str]] = []
    plotted = False

    # Collect Xnp outlier labels (pre-computed before combined plot)
    neutral_labels.extend(_collect_xnp_outlier_labels(alpha_array, xnp_values))

    # Plot Xnp_lat and collect its labels
    lat_plotted, lat_labels = _collect_xnp_lat_labels(ax, alpha_array, xnp_lat_values)
    if lat_plotted:
        plotted = True
    neutral_labels.extend(lat_labels)

    # Combined Xnp + Xnp_lat overlay with trend strip
    if xnp_values is not None and xnp_lat_values is not None:
        comb_len = min(len(alpha_array), len(xnp_values), len(xnp_lat_values))
        if comb_len > 0:
            x_axis = alpha_array[:comb_len]
            xnp_curve = xnp_values[:comb_len]
            ax.plot(x_axis, xnp_curve, linewidth=2, color="tab:cyan", label="Xnp")
            plotted = True
            for x, y, _, color in neutral_labels:
                ax.scatter(x, y, color=color, s=30, zorder=5)
            neutral_strip_colors = _compute_neutral_strip_colors(
                xnp_curve,
                xnp_lat_values[:comb_len],
                x_axis,
                comb_len,
            )
            _add_trend_strip(ax, x_axis, neutral_strip_colors, "Neutral trend")

    return plotted, neutral_labels


# --- Panel 6: Summary ---


def _render_summary_panel(
    ax: Any,
    aircraft_name: str,
    sweep_request: AlphaSweepRequest,
    characteristic_points: dict,
    cm_values: Optional[np.ndarray],
    alpha_array: np.ndarray,
    xnp_values: Optional[np.ndarray],
    xnp_lat_values: Optional[np.ndarray],
) -> None:
    """Render the text-based summary panel."""
    summary_lines: list[tuple[str, str]] = []
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    summary_lines.append((f"Aircraft: {aircraft_name}", "black"))
    summary_lines.append((f"Generated: {generated_at}", "black"))
    summary_lines.append(
        (
            f"OpPoint: V={sweep_request.velocity:.2f} m/s, h={sweep_request.altitude:.1f} m, "
            f"beta={sweep_request.beta:.2f} deg",
            "black",
        )
    )
    summary_lines.append(
        (
            f"Rates: p={sweep_request.p:.3f}, q={sweep_request.q:.3f}, r={sweep_request.r:.3f} rad/s | "
            f"xyz_ref={sweep_request.xyz_ref}",
            "black",
        )
    )

    ldmax = characteristic_points.get("maximum_lift_to_drag_ratio_point")
    cdmin = characteristic_points.get("minimum_drag_coefficient_point")
    clmax = characteristic_points.get("maximum_lift_coefficient_point")
    trim = characteristic_points.get("trim_point_cm_equals_zero")
    stall = characteristic_points.get("stall_point")

    if ldmax and ldmax.get("lift_to_drag_ratio") is not None and ldmax.get("alpha_deg") is not None:
        summary_lines.append(
            (
                f"L/D max: {ldmax['lift_to_drag_ratio']:.2f} @ a={ldmax['alpha_deg']:.2f}",
                _COLOR_GREEN,
            )
        )
    if cdmin and cdmin.get("CD") is not None and cdmin.get("alpha_deg") is not None:
        summary_lines.append(
            (f"CD min: {cdmin['CD']:.3f} @ a={cdmin['alpha_deg']:.2f}", _COLOR_BLUE)
        )
    if clmax and clmax.get("CL") is not None and clmax.get("alpha_deg") is not None:
        summary_lines.append(
            (f"CL max: {clmax['CL']:.3f} @ a={clmax['alpha_deg']:.2f}", _COLOR_RED)
        )
    if trim and trim.get("alpha_deg") is not None and trim.get("CL") is not None:
        summary_lines.append(
            (f"Trim (Cm=0): a={trim['alpha_deg']:.2f}, CL={trim['CL']:.3f}", _COLOR_BROWN)
        )
    if stall and stall.get("alpha_deg") is not None and stall.get("CL") is not None:
        summary_lines.append(
            (f"Stall-Indiz: a={stall['alpha_deg']:.2f}, CL={stall['CL']:.3f}", _COLOR_ORANGE)
        )

    long_text, long_color = _classify_longitudinal_stability(cm_values, alpha_array)
    xnp_text, xnp_color = _classify_variation(xnp_values, "Xnp trend")
    xnplat_text, xnplat_color = _classify_variation(xnp_lat_values, "Xnp_lat trend")
    summary_lines.append((f"Longitudinal: {long_text}", long_color))
    summary_lines.append((xnp_text, xnp_color))
    summary_lines.append((xnplat_text, xnplat_color))

    ax.set_title("Summary & Stability Tendencies")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    y = 0.95
    step = 0.095
    for text, color in summary_lines:
        if y < 0.05:
            break
        ax.scatter([0.03], [y], s=35, color=color, marker="o")
        ax.text(0.07, y, text, fontsize=9, va="center", ha="left", color="black")
        y -= step


# --- Axes formatting helpers ---

_AXES_CONFIG = [
    # (xlabel, ylabel, title, has_legend)
    (_LABEL_ALPHA_DEG, "Coefficient [-]", "Coefficients vs Alpha", True),
    ("CD [-]", "CL [-]", "CL vs CD", True),
    ("Cm [-]", "CL [-]", "CL vs Cm", False),
    (_LABEL_ALPHA_DEG, "L/D [-]", "Glide Ratio: L/D vs Alpha", True),
    (_LABEL_ALPHA_DEG, "Neutral Point [m]", "Combined: Xnp and Xnp_lat vs Alpha", True),
]


def _format_and_annotate_axes(
    axes: list[Any],
    label_sets: list[list[tuple[float, float, str, str]]],
) -> None:
    """Apply titles, grids, legends, and annotations to the first five axes."""
    for i, (xlabel, ylabel, title, has_legend) in enumerate(_AXES_CONFIG):
        ax = axes[i]
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.grid(True, alpha=0.3)
        if has_legend:
            ax.legend()
        _annotate_with_collision_avoidance(ax, label_sets[i])


# ---------------------------------------------------------------------------
# Main entry point (refactored)
# ---------------------------------------------------------------------------


async def get_alpha_sweep_diagram_url(
    db: Session, aeroplane_uuid, sweep_request: AlphaSweepRequest, base_url: str
) -> str:
    """Generate an alpha sweep diagram as PNG, save it under tmp, and return its static URL."""
    try:
        sweep_data = await analyze_alpha_sweep(db, aeroplane_uuid, sweep_request)
        result = sweep_data["analysis"]
        characteristic_points = sweep_data["characteristic_points"]
        aircraft_name = sweep_data.get("aircraft_name", str(aeroplane_uuid))
        alpha_array, cl_values, cd_values, cm_values = _extract_alpha_sweep_arrays(
            result, sweep_request
        )

        xnp_values, xnp_lat_values = _extract_reference_arrays(result)
        lift_values, drag_values = _extract_force_arrays(result)

        fig, axes = plt.subplots(3, 2, figsize=(18, 16))
        axes = axes.flatten()

        # Panel 1: Coefficients vs Alpha
        coeff_plotted = _plot_coefficient_curves(
            axes[0], alpha_array, cl_values, cd_values, cm_values
        )

        # Panel 2: CL vs CD polar
        polar_plotted, polar_labels, polar_alpha_labels = _plot_drag_polar(
            axes[1],
            axes[0],
            alpha_array,
            cl_values,
            cd_values,
            characteristic_points,
        )

        # Panel 3: CL vs Cm stability
        cm_plotted, cm_labels, cm_alpha_labels, cm_polar_labels = _plot_cm_stability(
            axes[2],
            axes[0],
            axes[1],
            alpha_array,
            cl_values,
            cm_values,
            characteristic_points,
        )

        # Panel 4: Glide ratio
        ld_plotted, ld_labels = _plot_glide_ratio(axes[3], alpha_array, lift_values, drag_values)

        # Panel 5: Neutral points
        np_plotted, neutral_labels = _plot_neutral_points(
            axes[4], alpha_array, xnp_values, xnp_lat_values
        )

        plotted = coeff_plotted or polar_plotted or cm_plotted or ld_plotted or np_plotted
        if not plotted:
            plt.close(fig)
            raise InternalError(
                message="Alpha sweep results did not contain plottable coefficient data."
            )

        # Merge label lists from cross-panel contributions
        alpha_labels = polar_alpha_labels + cm_alpha_labels
        all_polar_labels = polar_labels + cm_polar_labels

        # Format axes and annotate
        _format_and_annotate_axes(
            list(axes),
            [alpha_labels, all_polar_labels, cm_labels, ld_labels, neutral_labels],
        )

        # Panel 6: Summary
        _render_summary_panel(
            axes[5],
            aircraft_name,
            sweep_request,
            characteristic_points,
            cm_values,
            alpha_array,
            xnp_values,
            xnp_lat_values,
        )

        fig.suptitle("Alpha Sweep Results")
        fig.tight_layout()

        content_dir = os.path.join("tmp", str(aeroplane_uuid), "png")
        os.makedirs(content_dir, exist_ok=True)
        filename = f"alpha_sweep_{uuid4().hex}.png"
        file_path = os.path.join(content_dir, filename)

        fig.savefig(file_path, format="png", dpi=200, bbox_inches="tight")
        plt.close(fig)

        return urljoin(base_url, f"/static/{aeroplane_uuid}/png/{filename}")
    except InternalError:
        raise
    except Exception as e:
        logger.error(f"Error generating alpha sweep diagram: {e}")
        raise InternalError(message=f"Error generating alpha sweep diagram: {e}")


async def analyze_simple_sweep(
    db: Session, aeroplane_uuid, sweep_request: SimpleSweepRequest
) -> Any:
    """
    Perform a parameter sweep.

    Raises:
        NotFoundError: If the aeroplane does not exist.
        InternalError: If an analysis error occurs.
    """
    plane_schema = get_aeroplane_schema_or_raise(db, aeroplane_uuid)

    try:
        asb_airplane: Airplane = aeroplane_schema_to_asb_airplane_async(
            plane_schema=plane_schema
        )

        operating_point = OperatingPointSchema(
            name=f"sweep over {sweep_request.sweep_var}",
            description=None,
            altitude=sweep_request.altitude,
            velocity=sweep_request.velocity,
            alpha=sweep_request.alpha,
            beta=sweep_request.beta,
            p=sweep_request.p,
            q=sweep_request.q,
            r=sweep_request.r,
            xyz_ref=sweep_request.xyz_ref,
        )

        def vary_index(
            values: List[float], index: int, start: float, stop: float, num: int
        ) -> List[List[float]]:
            return [
                [val if i != index else v for i, val in enumerate(values)]
                for v in np.linspace(start, stop, num)
            ]

        if sweep_request.sweep_var in ["alpha", "velocity", "beta", "p", "q", "r", "altitude"]:
            current_val = operating_point.__dict__[sweep_request.sweep_var]
            operating_point.__dict__[sweep_request.sweep_var] = np.linspace(
                start=current_val,
                stop=current_val + sweep_request.step_size * sweep_request.num,
                num=sweep_request.num,
            )
        elif sweep_request.sweep_var == "x":
            operating_point.xyz_ref = vary_index(
                operating_point.xyz_ref,
                0,
                start=operating_point.xyz_ref[0],
                stop=operating_point.xyz_ref[0] + sweep_request.step_size * sweep_request.num,
                num=sweep_request.num,
            )
        elif sweep_request.sweep_var == "y":
            operating_point.xyz_ref = vary_index(
                operating_point.xyz_ref,
                1,
                start=operating_point.xyz_ref[1],
                stop=operating_point.xyz_ref[1] + sweep_request.step_size * sweep_request.num,
                num=sweep_request.num,
            )
        elif sweep_request.sweep_var == "z":
            operating_point.xyz_ref = vary_index(
                operating_point.xyz_ref,
                2,
                start=operating_point.xyz_ref[2],
                stop=operating_point.xyz_ref[2] + sweep_request.step_size * sweep_request.num,
                num=sweep_request.num,
            )
        else:
            from app.core.exceptions import ValidationError

            raise ValidationError(
                message=f"Invalid sweep variable: {sweep_request.sweep_var}",
                details={
                    "valid_vars": [
                        "alpha",
                        "velocity",
                        "beta",
                        "p",
                        "q",
                        "r",
                        "altitude",
                        "x",
                        "y",
                        "z",
                    ]
                },
            )

        result, _ = analyse_aerodynamics(
            AnalysisToolUrlType.AEROBUILDUP, operating_point, asb_airplane
        )
        return result
    except Exception as e:
        logger.error(f"Error in simple sweep: {e}")
        raise InternalError(message=f"Analysis error: {e}")


async def get_streamlines_three_view_image(
    db: Session, aeroplane_uuid, operating_point: OperatingPointSchema
) -> bytes:
    """
    Generate a four-view diagram with streamlines as PNG.

    Returns:
        bytes: PNG image data.

    Raises:
        NotFoundError: If the aeroplane does not exist.
        InternalError: If an analysis error occurs.
    """
    plane_schema = get_aeroplane_schema_or_raise(db, aeroplane_uuid)

    try:
        asb_airplane: Airplane = aeroplane_schema_to_asb_airplane_async(
            plane_schema=plane_schema
        )

        _, figure = analyse_aerodynamics(
            AnalysisToolUrlType.VORTEX_LATTICE,
            operating_point,
            asb_airplane,
            draw_streamlines=True,
            backend="plotly",
        )

        fig = compile_four_view_figure(figure)
        img_bytes = fig.to_image(format="png", width=1000, height=1000, scale=2)
        return img_bytes
    except Exception as e:
        logger.error(f"Error generating streamlines view: {e}")
        raise InternalError(message=f"Analysis error: {e}")


async def get_three_view_image(db: Session, aeroplane_uuid) -> bytes:
    """
    Generate a three-view diagram as PNG.

    Returns:
        bytes: PNG image data.

    Raises:
        NotFoundError: If the aeroplane does not exist.
        InternalError: If an error occurs.
    """
    plane_schema = get_aeroplane_schema_or_raise(db, aeroplane_uuid)

    try:
        asb_airplane: Airplane = aeroplane_schema_to_asb_airplane_async(
            plane_schema=plane_schema
        )

        fig = plt.figure(figsize=(10, 10))
        asb_airplane.draw_three_view(show=False)

        img_bytes = io.BytesIO()
        plt.savefig(img_bytes, format="png", dpi=300, bbox_inches="tight")
        img_bytes.seek(0)
        plt.close(fig)

        return img_bytes.getvalue()
    except Exception as e:
        logger.error(f"Error generating three-view: {e}")
        raise InternalError(message=f"Error generating diagram: {e}")


async def analyze_airplane_strip_forces(
    db: Session,
    aeroplane_uuid,
    operating_point: OperatingPointSchema,
) -> StripForcesResponse:
    """Run AVL with strip-force capture for the full airplane (all wings).

    Returns:
        StripForcesResponse with per-surface spanwise strip-force distributions.
    """
    from pathlib import Path as _Path

    import aerosandbox as asb

    from app.services.avl_strip_forces import AVLWithStripForces

    plane_schema = get_aeroplane_schema_or_raise(db, aeroplane_uuid)

    try:
        asb_airplane: Airplane = aeroplane_schema_to_asb_airplane_async(
            plane_schema=plane_schema
        )
        asb_airplane.xyz_ref = operating_point.xyz_ref

        atmosphere = asb.Atmosphere(altitude=operating_point.altitude)
        op_point = asb.OperatingPoint(
            velocity=operating_point.velocity,
            alpha=operating_point.alpha,
            beta=operating_point.beta,
            p=operating_point.p,
            q=operating_point.q,
            r=operating_point.r,
            atmosphere=atmosphere,
        )

        avl_command = str(_Path(__file__).resolve().parents[2] / "exports" / "avl")

        avl = AVLWithStripForces(
            airplane=asb_airplane,
            op_point=op_point,
            xyz_ref=operating_point.xyz_ref,
            avl_command=avl_command,
            timeout=60,
        )
        result = avl.run()

        strip_forces_data = result.get("strip_forces", [])
        surfaces = []
        for sf in strip_forces_data:
            strips = [StripForceEntry.model_validate(s) for s in sf["strips"]]
            surfaces.append(
                SurfaceStripForces(
                    surface_name=sf["surface_name"],
                    surface_number=sf["surface_number"],
                    n_chordwise=sf["n_chordwise"],
                    n_spanwise=sf["n_spanwise"],
                    surface_area=sf["surface_area"],
                    strips=strips,
                )
            )

        return StripForcesResponse(
            alpha=result.get("alpha", operating_point.alpha),
            mach=result.get("mach", 0),
            sref=result.get("Sref", 0),
            cref=result.get("Cref", 0),
            bref=result.get("Bref", 0),
            surfaces=surfaces,
        )
    except Exception as e:
        logger.error(f"Error analyzing airplane strip forces: {e}")
        raise InternalError(message=f"Strip forces analysis error: {e}")


async def analyze_wing_strip_forces(
    db: Session,
    aeroplane_uuid,
    wing_name: str,
    operating_point: OperatingPointSchema,
) -> StripForcesResponse:
    """Run AVL with strip-force capture for a single wing.

    Returns:
        StripForcesResponse with per-surface spanwise strip-force distributions.

    Raises:
        NotFoundError: If the aeroplane or wing does not exist.
        InternalError: If an analysis error occurs.
    """
    from pathlib import Path as _Path

    import aerosandbox as asb

    from app.services.avl_strip_forces import AVLWithStripForces

    plane_schema = get_wing_schema_or_raise(db, aeroplane_uuid, wing_name)

    try:
        asb_airplane: Airplane = aeroplane_schema_to_asb_airplane_async(
            plane_schema=plane_schema
        )
        asb_airplane.xyz_ref = operating_point.xyz_ref
        asb_airplane.wings = [w for w in asb_airplane.wings if w.name == wing_name]
        asb_airplane.fuselages = []

        atmosphere = asb.Atmosphere(altitude=operating_point.altitude)
        op_point = asb.OperatingPoint(
            velocity=operating_point.velocity,
            alpha=operating_point.alpha,
            beta=operating_point.beta,
            p=operating_point.p,
            q=operating_point.q,
            r=operating_point.r,
            atmosphere=atmosphere,
        )

        avl_command = str(_Path(__file__).resolve().parents[2] / "exports" / "avl")

        avl = AVLWithStripForces(
            airplane=asb_airplane,
            op_point=op_point,
            xyz_ref=operating_point.xyz_ref,
            avl_command=avl_command,
            timeout=30,
        )
        result = avl.run()

        strip_forces_data = result.get("strip_forces", [])
        surfaces = []
        for sf in strip_forces_data:
            strips = [StripForceEntry.model_validate(s) for s in sf["strips"]]
            surfaces.append(
                SurfaceStripForces(
                    surface_name=sf["surface_name"],
                    surface_number=sf["surface_number"],
                    n_chordwise=sf["n_chordwise"],
                    n_spanwise=sf["n_spanwise"],
                    surface_area=sf["surface_area"],
                    strips=strips,
                )
            )

        return StripForcesResponse(
            alpha=result.get("alpha", operating_point.alpha),
            mach=result.get("mach", 0),
            sref=result.get("Sref", 0),
            cref=result.get("Cref", 0),
            bref=result.get("Bref", 0),
            surfaces=surfaces,
        )
    except Exception as e:
        logger.error(f"Error analyzing wing strip forces: {e}")
        raise InternalError(message=f"Strip forces analysis error: {e}")
