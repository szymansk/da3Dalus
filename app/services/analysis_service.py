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
from typing import List, Optional, Tuple, Any
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


def _extract_alpha_sweep_arrays(result: Any, sweep_request: AlphaSweepRequest) -> tuple[np.ndarray, Optional[np.ndarray], Optional[np.ndarray], Optional[np.ndarray]]:
    alpha_values = None
    if getattr(result, "flight_condition", None) is not None:
        alpha_values = getattr(result.flight_condition, "alpha", None)
    if alpha_values is None:
        alpha_values = np.linspace(
            start=sweep_request.alpha_start,
            stop=sweep_request.alpha_end,
            num=sweep_request.alpha_num
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
            cl = cl_values[:n]
            cd = cd_values[:n]
            alpha = alpha_array[:n]

            with np.errstate(divide="ignore", invalid="ignore"):
                ld = np.where(np.abs(cd) > 1e-12, cl / cd, np.nan)
            if np.isfinite(ld).any():
                i = int(np.nanargmax(ld))
                points["maximum_lift_to_drag_ratio_point"] = {
                    "index": i, "alpha_deg": float(alpha[i]), "CL": float(cl[i]), "CD": float(cd[i]), "Cm": None,
                    "lift_to_drag_ratio": float(ld[i]),
                }

            i = int(np.argmin(cd))
            points["minimum_drag_coefficient_point"] = {
                "index": i, "alpha_deg": float(alpha[i]), "CL": float(cl[i]), "CD": float(cd[i]), "Cm": None,
            }

            i = int(np.argmax(cl))
            points["maximum_lift_coefficient_point"] = {
                "index": i, "alpha_deg": float(alpha[i]), "CL": float(cl[i]), "CD": float(cd[i]), "Cm": None,
            }

            cross = np.where(np.sign(cl[:-1]) != np.sign(cl[1:]))[0]
            if len(cross) > 0:
                i = int(cross[0])
                cl0, cl1 = cl[i], cl[i + 1]
                cd0, cd1 = cd[i], cd[i + 1]
                a0, a1 = alpha[i], alpha[i + 1]
                t = 0.0 if abs(cl1 - cl0) <= 1e-12 else -cl0 / (cl1 - cl0)
                points["drag_at_zero_lift_point"] = {
                    "index": None,
                    "alpha_deg": float(a0 + t * (a1 - a0)),
                    "CL": 0.0,
                    "CD": float(cd0 + t * (cd1 - cd0)),
                    "Cm": None,
                }
            else:
                i = int(np.argmin(np.abs(cl)))
                points["drag_at_zero_lift_point"] = {
                    "index": i, "alpha_deg": float(alpha[i]), "CL": float(cl[i]), "CD": float(cd[i]), "Cm": None,
                }

            i_clmax = int(np.argmax(cl))
            i_stall = i_clmax
            if i_clmax < n - 1:
                for i in range(i_clmax + 1, n):
                    if cl[i] < cl[i - 1] and cd[i] > cd[i - 1]:
                        i_stall = i
                        break
                else:
                    i_stall = min(i_clmax + 1, n - 1)
            points["stall_point"] = {
                "index": i_stall, "alpha_deg": float(alpha[i_stall]), "CL": float(cl[i_stall]), "CD": float(cd[i_stall]), "Cm": None,
            }

    if cl_values is not None and cm_values is not None:
        n = min(len(cl_values), len(cm_values), len(alpha_array))
        if n > 0:
            cl = cl_values[:n]
            cm = cm_values[:n]
            alpha = alpha_array[:n]

            cross = np.where(np.sign(cm[:-1]) != np.sign(cm[1:]))[0]
            if len(cross) > 0:
                i = int(cross[0])
                cm0, cm1 = cm[i], cm[i + 1]
                cl0, cl1 = cl[i], cl[i + 1]
                a0, a1 = alpha[i], alpha[i + 1]
                t = 0.0 if abs(cm1 - cm0) <= 1e-12 else -cm0 / (cm1 - cm0)
                cl_trim = cl0 + t * (cl1 - cl0)
                alpha_trim = a0 + t * (a1 - a0)
                cd_trim = None
                if cd_values is not None and len(cd_values) > i + 1:
                    cd0, cd1 = cd_values[i], cd_values[i + 1]
                    cd_trim = cd0 + t * (cd1 - cd0)
                points["trim_point_cm_equals_zero"] = {
                    "index": None,
                    "alpha_deg": float(alpha_trim),
                    "CL": float(cl_trim),
                    "CD": float(cd_trim) if cd_trim is not None else None,
                    "Cm": 0.0,
                }
            else:
                i = int(np.argmin(np.abs(cm)))
                points["trim_point_cm_equals_zero"] = {
                    "index": i,
                    "alpha_deg": float(alpha[i]),
                    "CL": float(cl[i]),
                    "CD": float(cd_values[i]) if cd_values is not None and len(cd_values) > i else None,
                    "Cm": float(cm[i]),
                }

    return points


async def get_aeroplane_schema_or_raise(db: Session, aeroplane_uuid) -> AeroplaneSchema:
    """
    Get an aeroplane schema by UUID.
    
    Raises:
        NotFoundError: If the aeroplane does not exist.
        InternalError: If a database error occurs.
    """
    try:
        return await get_aeroplane_by_id(aeroplane_uuid, db)
    except NotFoundInDbException as e:
        raise NotFoundError(
            message=str(e),
            details={"aeroplane_id": str(aeroplane_uuid)}
        )
    except SQLAlchemyError as e:
        logger.error(f"Database error when getting aeroplane: {e}")
        raise InternalError(message=f"Database error: {e}")


async def get_wing_schema_or_raise(
    db: Session,
    aeroplane_uuid,
    wing_name: str
) -> AeroplaneSchema:
    """
    Get an aeroplane schema with only the specified wing.
    
    Raises:
        NotFoundError: If the aeroplane or wing does not exist.
        InternalError: If a database error occurs.
    """
    try:
        return await get_wing_by_name_and_aeroplane_id(aeroplane_uuid, wing_name, db)
    except NotFoundInDbException as e:
        raise NotFoundError(
            message=str(e),
            details={"aeroplane_id": str(aeroplane_uuid), "wing_name": wing_name}
        )
    except SQLAlchemyError as e:
        logger.error(f"Database error when getting wing: {e}")
        raise InternalError(message=f"Database error: {e}")


async def analyze_wing(
    db: Session,
    aeroplane_uuid,
    wing_name: str,
    operating_point: OperatingPointSchema,
    analysis_tool: AnalysisToolUrlType
) -> Any:
    """
    Analyze a single wing using the specified analysis tool.
    
    Raises:
        NotFoundError: If the aeroplane or wing does not exist.
        InternalError: If an analysis error occurs.
    """
    plane_schema = await get_wing_schema_or_raise(db, aeroplane_uuid, wing_name)
    
    try:
        asb_airplane: Airplane = await aeroplane_schema_to_asb_airplane_async(plane_schema=plane_schema)
        asb_airplane.xyz_ref = operating_point.xyz_ref
        asb_airplane.wings = [w for w in asb_airplane.wings if w.name == wing_name]
        asb_airplane.fuselages = []
        
        result, _ = await analyse_aerodynamics(analysis_tool, operating_point, asb_airplane)
        return result
    except Exception as e:
        logger.error(f"Error analyzing wing: {e}")
        raise InternalError(message=f"Analysis error: {e}")


async def analyze_airplane(
    db: Session,
    aeroplane_uuid,
    operating_point: OperatingPointSchema,
    analysis_tool: AnalysisToolUrlType
) -> Any:
    """
    Analyze a complete airplane using the specified analysis tool.
    
    Raises:
        NotFoundError: If the aeroplane does not exist.
        InternalError: If an analysis error occurs.
    """
    plane_schema = await get_aeroplane_schema_or_raise(db, aeroplane_uuid)
    
    try:
        asb_airplane: Airplane = await aeroplane_schema_to_asb_airplane_async(plane_schema=plane_schema)
        result, _ = await analyse_aerodynamics(analysis_tool, operating_point, asb_airplane)
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

    plane_schema = await get_aeroplane_schema_or_raise(db, aeroplane_uuid)

    try:
        asb_airplane: Airplane = await aeroplane_schema_to_asb_airplane_async(plane_schema=plane_schema)
        _, figure = await analyse_aerodynamics(
            AnalysisToolUrlType.VORTEX_LATTICE,
            operating_point,
            asb_airplane,
            draw_streamlines=True,
        )
        return _json.loads(figure.to_json())
    except Exception as e:
        logger.error("Error calculating streamlines: %s", e)
        raise InternalError(message=f"Analysis error: {e}")


async def analyze_alpha_sweep(
    db: Session,
    aeroplane_uuid,
    sweep_request: AlphaSweepRequest
) -> Any:
    """
    Perform an angle of attack sweep.
    
    Raises:
        NotFoundError: If the aeroplane does not exist.
        InternalError: If an analysis error occurs.
    """
    plane_schema = await get_aeroplane_schema_or_raise(db, aeroplane_uuid)
    
    try:
        asb_airplane: Airplane = await aeroplane_schema_to_asb_airplane_async(plane_schema=plane_schema)
        
        operating_point = OperatingPointSchema(
            altitude=sweep_request.altitude,
            velocity=sweep_request.velocity,
            alpha=np.linspace(
                start=sweep_request.alpha_start,
                stop=sweep_request.alpha_end,
                num=sweep_request.alpha_num
            ),
            beta=sweep_request.beta,
            p=sweep_request.p,
            q=sweep_request.q,
            r=sweep_request.r,
            xyz_ref=sweep_request.xyz_ref
        )
        
        result, _ = await analyse_aerodynamics(
            AnalysisToolUrlType.AEROBUILDUP, operating_point, asb_airplane
        )
        alpha_array, cl_values, cd_values, cm_values = _extract_alpha_sweep_arrays(result, sweep_request)
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


async def get_alpha_sweep_diagram_url(
    db: Session,
    aeroplane_uuid,
    sweep_request: AlphaSweepRequest,
    base_url: str
) -> str:
    """
    Generate an alpha sweep diagram as PNG, save it under tmp, and return its static URL.
    """
    try:
        sweep_data = await analyze_alpha_sweep(db, aeroplane_uuid, sweep_request)
        result = sweep_data["analysis"]
        characteristic_points = sweep_data["characteristic_points"]
        aircraft_name = sweep_data.get("aircraft_name", str(aeroplane_uuid))
        alpha_array, cl_values, cd_values, cm_values = _extract_alpha_sweep_arrays(result, sweep_request)

        fig, axes = plt.subplots(3, 2, figsize=(18, 16))
        axes = axes.flatten()
        ax_coeff = axes[0]
        ax_polar = axes[1]
        ax_cm = axes[2]
        ax_ld = axes[3]
        ax_neutral_combined = axes[4]
        ax_summary = axes[5]

        def annotate_with_collision_avoidance(ax, points_with_labels):
            used = []
            for x, y, label, color in points_with_labels:
                candidate_offsets = [(12, 12), (12, -14), (-70, 14), (-70, -14), (36, 26), (36, -26), (-96, 26), (-96, -26)]
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
                    bbox=dict(boxstyle="round,pad=0.25", facecolor="white", edgecolor=color, linewidth=0.8, alpha=0.9),
                    arrowprops=dict(arrowstyle="-", linestyle=":", color=color, linewidth=0.9),
                )

        def add_trend_strip(ax, x_vals: np.ndarray, color_vals: list[str], strip_label: str):
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
            strip_ax.text(0.0, 0.5, strip_label, transform=strip_ax.transAxes, va="center", ha="left", fontsize=8)

        plotted = False
        alpha_point_labels = []
        polar_point_labels = []
        cm_point_labels = []
        ld_point_labels = []
        neutral_combined_labels = []

        xnp_values = None
        if getattr(result, "reference", None) is not None and getattr(result.reference, "Xnp", None) is not None:
            xnp_values = np.atleast_1d(np.asarray(result.reference.Xnp, dtype=float))
        xnp_lat_values = None
        if getattr(result, "reference", None) is not None and getattr(result.reference, "Xnp_lat", None) is not None:
            xnp_lat_values = np.atleast_1d(np.asarray(result.reference.Xnp_lat, dtype=float))

        lift_values = drag_values = None
        if getattr(result, "forces", None) is not None:
            if getattr(result.forces, "L", None) is not None:
                lift_values = np.atleast_1d(np.asarray(result.forces.L, dtype=float))
            if getattr(result.forces, "D", None) is not None:
                drag_values = np.atleast_1d(np.asarray(result.forces.D, dtype=float))

        if cl_values is not None:
            length = min(len(alpha_array), len(cl_values))
            if length > 0:
                ax_coeff.plot(alpha_array[:length], cl_values[:length], label="CL", linewidth=2)
                plotted = True
        if cd_values is not None:
            length = min(len(alpha_array), len(cd_values))
            if length > 0:
                ax_coeff.plot(alpha_array[:length], cd_values[:length], label="CD", linewidth=2)
                plotted = True
        if cm_values is not None:
            length = min(len(alpha_array), len(cm_values))
            if length > 0:
                ax_coeff.plot(alpha_array[:length], cm_values[:length], label="Cm", linewidth=2)
                plotted = True

        if cl_values is not None and cd_values is not None:
            length = min(len(cl_values), len(cd_values))
            if length > 0:
                cl_polar = cl_values[:length]
                cd_polar = cd_values[:length]
                alpha_polar = alpha_array[:min(len(alpha_array), length)]

                ax_polar.plot(cd_polar, cl_polar, linewidth=2, label="Polar Curve")
                plotted = True

                marker_style = {
                    "maximum_lift_to_drag_ratio_point": "tab:green",
                    "minimum_drag_coefficient_point": "tab:blue",
                    "maximum_lift_coefficient_point": "tab:red",
                    "drag_at_zero_lift_point": "tab:purple",
                    "stall_point": "tab:orange",
                    "trim_point_cm_equals_zero": "tab:brown",
                }
                label_name = {
                    "maximum_lift_to_drag_ratio_point": "(CL/CD)max",
                    "minimum_drag_coefficient_point": "CDmin",
                    "maximum_lift_coefficient_point": "CLmax",
                    "drag_at_zero_lift_point": "CD0",
                    "stall_point": "Stall",
                    "trim_point_cm_equals_zero": "Trim (Cm=0)",
                }
                for key, point in characteristic_points.items():
                    if point is None or point.get("CD") is None or point.get("CL") is None:
                        continue
                    x_val = point["CD"]
                    y_val = point["CL"]
                    ax_polar.scatter(x_val, y_val, color=marker_style[key], s=35, zorder=5)
                    if key == "maximum_lift_to_drag_ratio_point" and point.get("lift_to_drag_ratio") is not None:
                        label = f"{label_name[key]}={point['lift_to_drag_ratio']:.2f}\nCD={x_val:.3f}, CL={y_val:.3f}"
                    elif key == "minimum_drag_coefficient_point":
                        label = f"{label_name[key]}={x_val:.3f}\nCL={y_val:.3f}"
                    elif key == "maximum_lift_coefficient_point":
                        label = f"{label_name[key]}={y_val:.3f}\nCD={x_val:.3f}"
                    elif key == "drag_at_zero_lift_point":
                        label = f"{label_name[key]}={x_val:.3f}"
                    else:
                        label = f"{label_name[key]}\nCD={x_val:.3f}, CL={y_val:.3f}"
                    polar_point_labels.append((x_val, y_val, label, marker_style[key]))

                ldmax = characteristic_points.get("maximum_lift_to_drag_ratio_point")
                if ldmax and ldmax.get("CD") is not None and ldmax.get("CL") is not None:
                    ax_polar.plot(
                        [0.0, ldmax["CD"]],
                        [0.0, ldmax["CL"]],
                        linestyle="--",
                        linewidth=1.2,
                        color="gray",
                        alpha=0.8
                    )

                if len(alpha_polar) > 0:
                    alpha_len = len(alpha_polar)
                    for key, color, text in [
                        ("minimum_drag_coefficient_point", "tab:blue", "CDmin"),
                        ("maximum_lift_coefficient_point", "tab:red", "CLmax"),
                        ("stall_point", "tab:orange", "Stall"),
                    ]:
                        point = characteristic_points.get(key)
                        if not point:
                            continue
                        idx = point.get("index")
                        if idx is None or idx >= alpha_len:
                            continue
                        alpha_val = alpha_polar[idx]
                        if key == "minimum_drag_coefficient_point":
                            y_val = point.get("CD")
                            if y_val is None:
                                continue
                            ax_coeff.scatter(alpha_val, y_val, color=color, s=25, zorder=5)
                            alpha_point_labels.append((alpha_val, y_val, f"{text}={y_val:.3f} @ a={alpha_val:.2f}", color))
                        else:
                            y_val = point.get("CL")
                            if y_val is None:
                                continue
                            ax_coeff.scatter(alpha_val, y_val, color=color, s=25, zorder=5)
                            alpha_point_labels.append((alpha_val, y_val, f"{text} @ a={alpha_val:.2f}, CL={y_val:.3f}", color))

        if cl_values is not None and cm_values is not None:
            length = min(len(cl_values), len(cm_values))
            if length > 0:
                cm_curve = cm_values[:length]
                cl_curve = cl_values[:length]
                plotted = True

                alpha_cm = alpha_array[:length]
                with np.errstate(divide="ignore", invalid="ignore"):
                    cm_grad = np.gradient(cm_curve, alpha_cm) if length > 1 else np.array([np.nan])

                cm_strip_colors = []
                for g in cm_grad:
                    if not np.isfinite(g):
                        cm_strip_colors.append("lightgray")
                    elif g < -0.01:
                        cm_strip_colors.append("#4caf50")  # stable
                    elif g <= 0.01:
                        cm_strip_colors.append("#ffb74d")  # marginal
                    else:
                        cm_strip_colors.append("#e57373")  # unstable

                # Render CL-Cm as alpha-ordered colored path segments.
                if length > 1:
                    points = np.column_stack((cm_curve, cl_curve))
                    segments = np.stack([points[:-1], points[1:]], axis=1)
                    segment_colors = cm_strip_colors[1:] if len(cm_strip_colors) > 1 else ["#4caf50"]
                    lc = LineCollection(segments, colors=segment_colors, linewidths=2.2, alpha=0.95)
                    ax_cm.add_collection(lc)
                    ax_cm.autoscale_view()
                else:
                    ax_cm.plot(cm_curve, cl_curve, linewidth=2, color="#4caf50")

                trim_point = characteristic_points.get("trim_point_cm_equals_zero")
                if trim_point and trim_point.get("CL") is not None:
                    cm_trim = trim_point.get("Cm") if trim_point.get("Cm") is not None else 0.0
                    cl_trim = trim_point["CL"]
                    alpha_trim = trim_point.get("alpha_deg")
                    cd_trim = trim_point.get("CD")

                    ax_cm.scatter(cm_trim, cl_trim, color="tab:brown", s=35, zorder=5)
                    cm_label = f"Trim (Cm=0): CL={cl_trim:.3f}"
                    if alpha_trim is not None:
                        cm_label += f", a={alpha_trim:.2f}"
                    cm_point_labels.append((cm_trim, cl_trim, cm_label, "tab:brown"))

                    if alpha_trim is not None:
                        ax_coeff.scatter(alpha_trim, 0.0, color="tab:brown", s=25, zorder=5)
                        alpha_point_labels.append((alpha_trim, 0.0, f"Trim (Cm=0) @ a={alpha_trim:.2f}", "tab:brown"))

                    if cd_trim is not None:
                        ax_polar.scatter(cd_trim, cl_trim, color="tab:brown", s=35, zorder=5)
                        polar_point_labels.append((cd_trim, cl_trim, f"Trim (Cm=0)\nCD={cd_trim:.3f}, CL={cl_trim:.3f}", "tab:brown"))

                # Trend strip for longitudinal stability regime based on dCm/dalpha.
                add_trend_strip(ax_coeff, alpha_cm, cm_strip_colors, "Cm trend")
                add_trend_strip(ax_cm, alpha_cm, cm_strip_colors, "Cm path trend")

        if xnp_values is not None and len(xnp_values) > 0:
            x_len = min(len(alpha_array), len(xnp_values))
            if x_len > 0:
                idx = np.arange(x_len)
                xnp_curve = xnp_values[:x_len]
                median_xnp = float(np.nanmedian(xnp_curve))
                deviation = np.abs(xnp_curve - median_xnp)
                if np.isfinite(deviation).any():
                    outlier_idx = int(np.nanargmax(deviation))
                    outlier_alpha = alpha_array[min(outlier_idx, len(alpha_array) - 1)]
                    neutral_combined_labels.append((
                        outlier_alpha,
                        xnp_curve[outlier_idx],
                        f"Xnp Ausreißer?\na={outlier_alpha:.2f}, Xnp={xnp_curve[outlier_idx]:.3f}",
                        "tab:red"
                    ))

        if lift_values is not None and drag_values is not None:
            ld_len = min(len(alpha_array), len(lift_values), len(drag_values))
            if ld_len > 0:
                alpha_ld = alpha_array[:ld_len]
                lift_curve = lift_values[:ld_len]
                drag_curve = drag_values[:ld_len]
                with np.errstate(divide="ignore", invalid="ignore"):
                    ld_curve = np.where(np.abs(drag_curve) > 1e-12, lift_curve / drag_curve, np.nan)

                ax_ld.plot(alpha_ld, ld_curve, linewidth=2, color="tab:green", label="L/D")
                plotted = True

                if np.isfinite(ld_curve).any():
                    i_ldmax = int(np.nanargmax(ld_curve))
                    ax_ld.scatter(alpha_ld[i_ldmax], ld_curve[i_ldmax], color="tab:green", s=35, zorder=5)
                    ld_point_labels.append((
                        alpha_ld[i_ldmax],
                        ld_curve[i_ldmax],
                        f"Sweet Spot\na={alpha_ld[i_ldmax]:.2f}, L/D={ld_curve[i_ldmax]:.2f}",
                        "tab:green"
                    ))

        if xnp_lat_values is not None and len(xnp_lat_values) > 0:
            lat_len = min(len(alpha_array), len(xnp_lat_values))
            if lat_len > 0:
                x_axis = alpha_array[:lat_len]
                ax_neutral_combined.plot(x_axis, xnp_lat_values[:lat_len], linewidth=2, color="tab:pink", label="Xnp_lat")
                plotted = True

                median_lat = float(np.nanmedian(xnp_lat_values[:lat_len]))
                deviation_lat = np.abs(xnp_lat_values[:lat_len] - median_lat)
                if np.isfinite(deviation_lat).any():
                    outlier_idx = int(np.nanargmax(deviation_lat))
                    outlier_x = x_axis[outlier_idx]
                    outlier_y = xnp_lat_values[outlier_idx]
                    neutral_combined_labels.append((
                        outlier_x,
                        outlier_y,
                        f"Xnp_lat Ausreißer?\na={outlier_x:.2f}, Xnp_lat={outlier_y:.3f}",
                        "tab:red"
                    ))

                if lat_len > 1:
                    jumps = np.abs(np.diff(xnp_lat_values[:lat_len]))
                    if np.isfinite(jumps).any():
                        jump_idx = int(np.nanargmax(jumps)) + 1
                        jump_x = x_axis[jump_idx]
                        jump_y = xnp_lat_values[jump_idx]
                        neutral_combined_labels.append((
                            jump_x,
                            jump_y,
                            f"Xnp_lat Sprung\na={jump_x:.2f}",
                            "tab:orange"
                        ))

        if xnp_values is not None and xnp_lat_values is not None:
            comb_len = min(len(alpha_array), len(xnp_values), len(xnp_lat_values))
            if comb_len > 0:
                x_axis = alpha_array[:comb_len]
                xnp_curve = xnp_values[:comb_len]
                ax_neutral_combined.plot(x_axis, xnp_curve, linewidth=2, color="tab:cyan", label="Xnp")
                plotted = True
                for x, y, _, color in neutral_combined_labels:
                    ax_neutral_combined.scatter(x, y, color=color, s=30, zorder=5)

                xnp_lat_curve = xnp_lat_values[:comb_len]
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
                neutral_strip_colors = []
                for m in combined_metric:
                    if not np.isfinite(m):
                        neutral_strip_colors.append("lightgray")
                    elif m <= low_thr:
                        neutral_strip_colors.append("#4caf50")  # robust
                    elif m <= high_thr:
                        neutral_strip_colors.append("#ffb74d")  # moderate
                    else:
                        neutral_strip_colors.append("#e57373")  # critical
                add_trend_strip(ax_neutral_combined, x_axis, neutral_strip_colors, "Neutral trend")

        if not plotted:
            plt.close(fig)
            raise InternalError(message="Alpha sweep results did not contain plottable coefficient data.")

        ax_coeff.set_xlabel("Alpha [deg]")
        ax_coeff.set_ylabel("Coefficient [-]")
        ax_coeff.set_title("Coefficients vs Alpha")
        ax_coeff.grid(True, alpha=0.3)
        ax_coeff.legend()
        annotate_with_collision_avoidance(ax_coeff, alpha_point_labels)

        ax_polar.set_xlabel("CD [-]")
        ax_polar.set_ylabel("CL [-]")
        ax_polar.set_title("CL vs CD")
        ax_polar.grid(True, alpha=0.3)
        ax_polar.legend()
        annotate_with_collision_avoidance(ax_polar, polar_point_labels)

        ax_cm.set_xlabel("Cm [-]")
        ax_cm.set_ylabel("CL [-]")
        ax_cm.set_title("CL vs Cm")
        ax_cm.grid(True, alpha=0.3)
        annotate_with_collision_avoidance(ax_cm, cm_point_labels)

        ax_ld.set_xlabel("Alpha [deg]")
        ax_ld.set_ylabel("L/D [-]")
        ax_ld.set_title("Glide Ratio: L/D vs Alpha")
        ax_ld.grid(True, alpha=0.3)
        ax_ld.legend()
        annotate_with_collision_avoidance(ax_ld, ld_point_labels)

        ax_neutral_combined.set_xlabel("Alpha [deg]")
        ax_neutral_combined.set_ylabel("Neutral Point [m]")
        ax_neutral_combined.set_title("Combined: Xnp and Xnp_lat vs Alpha")
        ax_neutral_combined.grid(True, alpha=0.3)
        ax_neutral_combined.legend()
        annotate_with_collision_avoidance(ax_neutral_combined, neutral_combined_labels)

        def classify_longitudinal_stability(cm_vals: Optional[np.ndarray], alpha_vals: np.ndarray) -> tuple[str, str]:
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
                return f"Stable (dCm/da={slope:.4f})", "tab:green"
            if slope <= 0.01:
                return f"Neutral (dCm/da={slope:.4f})", "tab:orange"
            return f"Unstable (dCm/da={slope:.4f})", "tab:red"

        def classify_variation(series: Optional[np.ndarray], label: str) -> tuple[str, str]:
            if series is None or len(series) < 2:
                return f"{label}: N/A", "gray"
            values = np.asarray(series, dtype=float)
            values = values[np.isfinite(values)]
            if len(values) < 2:
                return f"{label}: N/A", "gray"
            span = float(np.max(values) - np.min(values))
            if span < 0.5:
                return f"{label}: robust (span={span:.3f})", "tab:green"
            if span < 2.0:
                return f"{label}: moderate (span={span:.3f})", "tab:orange"
            return f"{label}: volatile (span={span:.3f})", "tab:red"

        summary_lines: list[tuple[str, str]] = []
        generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        summary_lines.append((f"Aircraft: {aircraft_name}", "black"))
        summary_lines.append((f"Generated: {generated_at}", "black"))
        summary_lines.append((
            f"OpPoint: V={sweep_request.velocity:.2f} m/s, h={sweep_request.altitude:.1f} m, "
            f"beta={sweep_request.beta:.2f} deg",
            "black",
        ))
        summary_lines.append((
            f"Rates: p={sweep_request.p:.3f}, q={sweep_request.q:.3f}, r={sweep_request.r:.3f} rad/s | "
            f"xyz_ref={sweep_request.xyz_ref}",
            "black",
        ))
        ldmax = characteristic_points.get("maximum_lift_to_drag_ratio_point")
        cdmin = characteristic_points.get("minimum_drag_coefficient_point")
        clmax = characteristic_points.get("maximum_lift_coefficient_point")
        trim = characteristic_points.get("trim_point_cm_equals_zero")
        stall = characteristic_points.get("stall_point")

        if ldmax and ldmax.get("lift_to_drag_ratio") is not None and ldmax.get("alpha_deg") is not None:
            summary_lines.append((f"L/D max: {ldmax['lift_to_drag_ratio']:.2f} @ a={ldmax['alpha_deg']:.2f}", "tab:green"))
        if cdmin and cdmin.get("CD") is not None and cdmin.get("alpha_deg") is not None:
            summary_lines.append((f"CD min: {cdmin['CD']:.3f} @ a={cdmin['alpha_deg']:.2f}", "tab:blue"))
        if clmax and clmax.get("CL") is not None and clmax.get("alpha_deg") is not None:
            summary_lines.append((f"CL max: {clmax['CL']:.3f} @ a={clmax['alpha_deg']:.2f}", "tab:red"))
        if trim and trim.get("alpha_deg") is not None and trim.get("CL") is not None:
            summary_lines.append((f"Trim (Cm=0): a={trim['alpha_deg']:.2f}, CL={trim['CL']:.3f}", "tab:brown"))
        if stall and stall.get("alpha_deg") is not None and stall.get("CL") is not None:
            summary_lines.append((f"Stall-Indiz: a={stall['alpha_deg']:.2f}, CL={stall['CL']:.3f}", "tab:orange"))

        long_text, long_color = classify_longitudinal_stability(cm_values, alpha_array)
        xnp_text, xnp_color = classify_variation(xnp_values, "Xnp trend")
        xnplat_text, xnplat_color = classify_variation(xnp_lat_values, "Xnp_lat trend")
        summary_lines.append((f"Longitudinal: {long_text}", long_color))
        summary_lines.append((xnp_text, xnp_color))
        summary_lines.append((xnplat_text, xnplat_color))

        ax_summary.set_title("Summary & Stability Tendencies")
        ax_summary.set_xlim(0, 1)
        ax_summary.set_ylim(0, 1)
        ax_summary.axis("off")

        y = 0.95
        step = 0.095
        for text, color in summary_lines:
            if y < 0.05:
                break
            ax_summary.scatter([0.03], [y], s=35, color=color, marker="o")
            ax_summary.text(0.07, y, text, fontsize=9, va="center", ha="left", color="black")
            y -= step

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
    db: Session,
    aeroplane_uuid,
    sweep_request: SimpleSweepRequest
) -> Any:
    """
    Perform a parameter sweep.
    
    Raises:
        NotFoundError: If the aeroplane does not exist.
        InternalError: If an analysis error occurs.
    """
    plane_schema = await get_aeroplane_schema_or_raise(db, aeroplane_uuid)
    
    try:
        asb_airplane: Airplane = await aeroplane_schema_to_asb_airplane_async(plane_schema=plane_schema)
        
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
            xyz_ref=sweep_request.xyz_ref
        )
        
        def vary_index(
            values: List[float],
            index: int,
            start: float,
            stop: float,
            num: int
        ) -> List[List[float]]:
            return [
                [val if i != index else v for i, val in enumerate(values)]
                for v in np.linspace(start, stop, num)
            ]
        
        if sweep_request.sweep_var in ['alpha', 'velocity', 'beta', 'p', 'q', 'r', 'altitude']:
            current_val = operating_point.__dict__[sweep_request.sweep_var]
            operating_point.__dict__[sweep_request.sweep_var] = np.linspace(
                start=current_val,
                stop=current_val + sweep_request.step_size * sweep_request.num,
                num=sweep_request.num
            )
        elif sweep_request.sweep_var == 'x':
            operating_point.xyz_ref = vary_index(
                operating_point.xyz_ref, 0,
                start=operating_point.xyz_ref[0],
                stop=operating_point.xyz_ref[0] + sweep_request.step_size * sweep_request.num,
                num=sweep_request.num
            )
        elif sweep_request.sweep_var == 'y':
            operating_point.xyz_ref = vary_index(
                operating_point.xyz_ref, 1,
                start=operating_point.xyz_ref[1],
                stop=operating_point.xyz_ref[1] + sweep_request.step_size * sweep_request.num,
                num=sweep_request.num
            )
        elif sweep_request.sweep_var == 'z':
            operating_point.xyz_ref = vary_index(
                operating_point.xyz_ref, 2,
                start=operating_point.xyz_ref[2],
                stop=operating_point.xyz_ref[2] + sweep_request.step_size * sweep_request.num,
                num=sweep_request.num
            )
        else:
            from app.core.exceptions import ValidationError
            raise ValidationError(
                message=f"Invalid sweep variable: {sweep_request.sweep_var}",
                details={"valid_vars": ['alpha', 'velocity', 'beta', 'p', 'q', 'r', 'altitude', 'x', 'y', 'z']}
            )
        
        result, _ = await analyse_aerodynamics(
            AnalysisToolUrlType.AEROBUILDUP, operating_point, asb_airplane
        )
        return result
    except Exception as e:
        logger.error(f"Error in simple sweep: {e}")
        raise InternalError(message=f"Analysis error: {e}")


async def get_streamlines_three_view_image(
    db: Session,
    aeroplane_uuid,
    operating_point: OperatingPointSchema
) -> bytes:
    """
    Generate a four-view diagram with streamlines as PNG.
    
    Returns:
        bytes: PNG image data.
    
    Raises:
        NotFoundError: If the aeroplane does not exist.
        InternalError: If an analysis error occurs.
    """
    plane_schema = await get_aeroplane_schema_or_raise(db, aeroplane_uuid)
    
    try:
        asb_airplane: Airplane = await aeroplane_schema_to_asb_airplane_async(plane_schema=plane_schema)
        
        _, figure = await analyse_aerodynamics(
            AnalysisToolUrlType.VORTEX_LATTICE,
            operating_point,
            asb_airplane,
            draw_streamlines=True,
            backend='plotly'
        )
        
        fig = await compile_four_view_figure(figure)
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
    plane_schema = await get_aeroplane_schema_or_raise(db, aeroplane_uuid)
    
    try:
        asb_airplane: Airplane = await aeroplane_schema_to_asb_airplane_async(plane_schema=plane_schema)
        
        fig = plt.figure(figsize=(10, 10))
        asb_airplane.draw_three_view(show=False)
        
        img_bytes = io.BytesIO()
        plt.savefig(img_bytes, format='png', dpi=300, bbox_inches='tight')
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

    plane_schema = await get_aeroplane_schema_or_raise(db, aeroplane_uuid)

    try:
        asb_airplane: Airplane = await aeroplane_schema_to_asb_airplane_async(plane_schema=plane_schema)
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

        avl_command = str(
            _Path(__file__).resolve().parents[2] / "exports" / "avl"
        )

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
            surfaces.append(SurfaceStripForces(
                surface_name=sf["surface_name"],
                surface_number=sf["surface_number"],
                n_chordwise=sf["n_chordwise"],
                n_spanwise=sf["n_spanwise"],
                surface_area=sf["surface_area"],
                strips=strips,
            ))

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

    plane_schema = await get_wing_schema_or_raise(db, aeroplane_uuid, wing_name)

    try:
        asb_airplane: Airplane = await aeroplane_schema_to_asb_airplane_async(plane_schema=plane_schema)
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

        avl_command = str(
            _Path(__file__).resolve().parents[2] / "exports" / "avl"
        )

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
            surfaces.append(SurfaceStripForces(
                surface_name=sf["surface_name"],
                surface_number=sf["surface_number"],
                n_chordwise=sf["n_chordwise"],
                n_spanwise=sf["n_spanwise"],
                surface_area=sf["surface_area"],
                strips=strips,
            ))

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
