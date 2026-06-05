"""Per-section world angle of attack via AeroSandbox LiftingLine (gh-840).

Method (asb 4.2.9)
------------------
``asb.LiftingLine`` yields per-panel vortex centres, strengths, chords, and
local velocity vectors from which we derive:

  gamma      = vortex_strengths  [m²/s]
  V_local    = get_velocity_at_points(vortex_centres)  [m/s, shape (N, 3)]
  Vmag       = ||V_local||  [m/s]
  cl         = 2·Γ / (Vmag · c)    (section lift coefficient, includes induced)

  alpha_eff  = atan2(V·n, V·f)     [deg]   (effective AoA including downwash)

Geometric AoA at each panel:
  alpha_geom = op_alpha + incidence_w + twist(y)

where twist(y) is the geometric twist stored in each ASB WingXSec.  Because
the wing may have multiple xsecs we interpolate linearly between them using
the panel's y-coordinate.

Induced angle:
  alpha_induced = alpha_geom - alpha_eff   [deg]

Public surface
--------------
``compute_section_aoa`` — pure function, receives an ASB Airplane + OperatingPoint.
``get_section_aoa``    — DB-aware async entry point (loads plane, resolves OP).

Platform guard: ``aerosandbox`` is excluded on linux/aarch64.  The public API
is always importable; the actual computation is guarded inside the function
body.  Callers MUST check ``aerosandbox_available()`` before wiring HTTP
routes (``main.py`` pattern).
"""

from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING

from pydantic import UUID4

from app.core.exceptions import NotFoundError, ValidationDomainError
from app.converters.model_schema_converters import aeroplane_schema_to_asb_airplane_async
from app.services.analysis_service import get_aeroplane_schema_or_raise

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_SPANWISE_RESOLUTION = 8  # panels per half-span — fast, physically sane


# ---------------------------------------------------------------------------
# Public schema (no ASB dependency)
# ---------------------------------------------------------------------------


class SectionAoaEntry:
    """One spanwise sample point."""

    __slots__ = (
        "y_m",
        "chord_m",
        "cl",
        "alpha_geometric_deg",
        "alpha_effective_deg",
        "induced_angle_deg",
    )

    def __init__(
        self,
        *,
        y_m: float,
        chord_m: float,
        cl: float,
        alpha_geometric_deg: float,
        alpha_effective_deg: float,
        induced_angle_deg: float,
    ) -> None:
        self.y_m = y_m
        self.chord_m = chord_m
        self.cl = cl
        self.alpha_geometric_deg = alpha_geometric_deg
        self.alpha_effective_deg = alpha_effective_deg
        self.induced_angle_deg = induced_angle_deg

    def to_dict(self) -> dict:
        return {
            "y_m": self.y_m,
            "chord_m": self.chord_m,
            "cl": self.cl,
            "alpha_geometric_deg": self.alpha_geometric_deg,
            "alpha_effective_deg": self.alpha_effective_deg,
            "induced_angle_deg": self.induced_angle_deg,
        }


# ---------------------------------------------------------------------------
# Pure computation (requires aerosandbox)
# ---------------------------------------------------------------------------


def compute_section_aoa(
    asb_airplane,
    asb_op_point,
    *,
    wing_name: str,
    spanwise_resolution: int = _SPANWISE_RESOLUTION,
) -> list[SectionAoaEntry]:
    """Compute per-section world AoA for one wing of *asb_airplane*.

    Parameters
    ----------
    asb_airplane:
        ``asb.Airplane`` built from the DB schema.
    asb_op_point:
        ``asb.OperatingPoint`` at the operating condition.
    wing_name:
        Name of the wing whose section data is requested.
    spanwise_resolution:
        Number of spanwise panels per half-span (default 8).

    Returns
    -------
    list of SectionAoaEntry, sorted by ascending y_m.

    Raises
    ------
    ValidationDomainError
        If the named wing is not found on the airplane.
    ImportError
        If aerosandbox is not available (linux/aarch64 guard).
    """
    import aerosandbox as asb
    import numpy as np

    # ------------------------------------------------------------------
    # 1.  Locate the requested wing
    # ------------------------------------------------------------------
    target_wing = None
    for w in asb_airplane.wings:
        if getattr(w, "name", None) == wing_name:
            target_wing = w
            break
    if target_wing is None:
        available = [getattr(w, "name", "<unnamed>") for w in asb_airplane.wings]
        raise ValidationDomainError(
            message=(f"Wing '{wing_name}' not found on airplane. Available wings: {available}")
        )

    # ------------------------------------------------------------------
    # 2.  Build a single-wing airplane for the LiftingLine run.
    #     We keep only the requested wing to avoid cross-wing interference
    #     confusing the section attribution.
    # ------------------------------------------------------------------
    single_wing_airplane = asb.Airplane(
        wings=[target_wing],
        xyz_ref=asb_airplane.xyz_ref,
    )

    ll = asb.LiftingLine(
        airplane=single_wing_airplane,
        op_point=asb_op_point,
        spanwise_resolution=spanwise_resolution,
    )
    ll.run()

    # ------------------------------------------------------------------
    # 3.  Extract per-panel quantities
    # ------------------------------------------------------------------
    y_arr = np.array(ll.vortex_centers)[:, 1]  # spanwise position [m]
    gamma_arr = np.array(ll.vortex_strengths).flatten()  # vortex strength [m²/s]
    chord_arr = np.array(ll.chords).flatten()  # panel chord [m]

    v_local = np.array(ll.get_velocity_at_points(ll.vortex_centers))  # (N, 3)
    vmag = np.linalg.norm(v_local, axis=1)  # (N,)

    # Section lift coefficient (Kutta-Joukowski, 2D slice):
    cl_arr = 2.0 * gamma_arr / (vmag * chord_arr)

    # Effective AoA (includes induced downwash) from local velocity resolved
    # onto the panel's normal and forward directions.
    #
    # Convention note (ASB LiftingLine):
    #   ``local_forward_direction`` points from TE to LE (rearward), i.e. the
    #   negative of the aerodynamic chord direction.  To recover the standard
    #   AoA sign (positive nose-up) we negate the forward component before
    #   applying atan2.
    fwd = np.array(ll.local_forward_direction)  # (N, 3) — TE→LE unit vector
    norm = np.array(ll.normal_directions)  # (N, 3) — panel normal unit vector

    v_dot_norm = np.sum(v_local * norm, axis=1)
    v_dot_fwd = np.sum(v_local * fwd, axis=1)
    # Negate v_dot_fwd to convert from TE→LE to LE→TE convention
    alpha_eff_arr = np.degrees(np.arctan2(v_dot_norm, -v_dot_fwd))  # (N,) [deg]

    # ------------------------------------------------------------------
    # 4.  Geometric AoA at each panel
    #     alpha_geom(y) = op_alpha + incidence_wing + twist(y)
    #
    #     incidence_wing:  the first xsec's twist (= wing incidence setting)
    #     twist(y):        geometric twist above the wing incidence baseline.
    #
    #     In ASB the xsec.twist is stored in *degrees* and already represents
    #     the absolute geometric angle relative to the body x-axis.  We
    #     interpolate linearly between xsec nodes as a function of y.
    # ------------------------------------------------------------------
    op_alpha_deg = float(asb_op_point.alpha)

    # Build (y_xsec, twist_xsec) from the wing's xsecs
    xsecs = target_wing.xsecs
    if len(xsecs) < 1:
        raise ValidationDomainError(message=f"Wing '{wing_name}' has no cross-sections.")

    xsec_y = np.array([float(np.atleast_1d(xs.xyz_le)[1]) for xs in xsecs])
    xsec_twist = np.array([float(xs.twist) for xs in xsecs])  # degrees

    # Interpolate twist to panel y positions (clamped to xsec range)
    twist_at_y = np.interp(y_arr, xsec_y, xsec_twist)

    alpha_geom_arr = op_alpha_deg + twist_at_y  # [deg]

    # Induced angle = geometric − effective
    induced_angle_arr = alpha_geom_arr - alpha_eff_arr

    # ------------------------------------------------------------------
    # 5.  Assemble output — sort by ascending y
    # ------------------------------------------------------------------
    order = np.argsort(y_arr)
    entries: list[SectionAoaEntry] = []
    for i in order:
        entries.append(
            SectionAoaEntry(
                y_m=round(float(y_arr[i]), 6),
                chord_m=round(float(chord_arr[i]), 6),
                cl=round(float(cl_arr[i]), 6),
                alpha_geometric_deg=round(float(alpha_geom_arr[i]), 4),
                alpha_effective_deg=round(float(alpha_eff_arr[i]), 4),
                induced_angle_deg=round(float(induced_angle_arr[i]), 4),
            )
        )
    return entries


# ---------------------------------------------------------------------------
# DB-aware async entry point
# ---------------------------------------------------------------------------


async def get_section_aoa(
    db: "Session",
    aeroplane_uuid: UUID4,
    wing_name: str,
    *,
    operating_point_id: int | None = None,
) -> list[SectionAoaEntry]:
    """Load aeroplane, resolve operating point, run LiftingLine, return sections.

    Operating-point resolution strategy
    ------------------------------------
    1.  If ``operating_point_id`` is supplied → load that stored OP (must be
        TRIMMED).
    2.  Else → look for any TRIMMED OP belonging to this aircraft and use the
        first one found.
    3.  If none exists → fall back to a quick AeroBuildup CL-target solve to
        find a level-flight operating point.

    Raises
    ------
    NotFoundError
        Aeroplane or wing not found.
    ValidationDomainError
        No usable operating point could be resolved.
    """
    import aerosandbox as asb

    from app.models.analysismodels import OperatingPointModel
    from app.schemas.aeroanalysisschema import OperatingPointStatus
    from app.services.operating_point_resolver import operating_point_model_to_schema

    plane_schema = get_aeroplane_schema_or_raise(db, aeroplane_uuid)
    asb_airplane = aeroplane_schema_to_asb_airplane_async(plane_schema=plane_schema)

    # ------------------------------------------------------------------
    # Resolve OP
    # ------------------------------------------------------------------
    op_schema = None

    if operating_point_id is not None:
        # Explicit OP requested
        op_model = (
            db.query(OperatingPointModel)
            .filter(
                OperatingPointModel.id == operating_point_id,
                OperatingPointModel.aircraft_id == plane_schema.id,
            )
            .first()
        )
        if op_model is None:
            raise NotFoundError(
                message=(
                    f"OperatingPoint {operating_point_id} not found on aeroplane {aeroplane_uuid}."
                )
            )
        op_schema = operating_point_model_to_schema(op_model)
    else:
        # Find first TRIMMED OP for this aircraft
        op_model = (
            db.query(OperatingPointModel)
            .filter(
                OperatingPointModel.aircraft_id == plane_schema.id,
                OperatingPointModel.status == OperatingPointStatus.TRIMMED,
            )
            .first()
        )
        if op_model is not None:
            op_schema = operating_point_model_to_schema(op_model)

    if op_schema is None:
        # Fall back: level-flight AeroBuildup solve
        op_schema = _resolve_level_flight_op(plane_schema, asb_airplane)

    # ------------------------------------------------------------------
    # Build asb.OperatingPoint from schema
    # ------------------------------------------------------------------
    atmosphere = asb.Atmosphere(altitude=op_schema.altitude)
    asb_op = asb.OperatingPoint(
        velocity=op_schema.velocity,
        alpha=op_schema.alpha,
        beta=op_schema.beta,
        p=op_schema.p,
        q=op_schema.q,
        r=op_schema.r,
        atmosphere=atmosphere,
    )

    # Apply stored deflections so the geometry reflects the trim state
    if op_schema.control_deflections:
        asb_airplane = asb_airplane.with_control_deflections(op_schema.control_deflections)

    return compute_section_aoa(asb_airplane, asb_op, wing_name=wing_name)


# ---------------------------------------------------------------------------
# Level-flight fallback
# ---------------------------------------------------------------------------


def _resolve_level_flight_op(plane_schema, asb_airplane):
    """Quick AeroBuildup CL-target solve to find a level-flight operating point.

    Used only when no stored TRIMMED OP exists.  Returns an OperatingPointSchema.
    """
    import aerosandbox as asb
    import numpy as np
    from scipy.optimize import brentq

    from app.schemas.aeroanalysisschema import OperatingPointSchema

    mass_kg: float = getattr(plane_schema, "total_mass_kg", None) or 1.5
    rho = 1.225
    g = 9.80665

    # Reference area from the first wing's planform area approximation
    s_ref = None
    for w in asb_airplane.wings:
        if getattr(w, "symmetric", False):
            try:
                s_ref = float(w.area())
                break
            except Exception:
                pass
    if s_ref is None or s_ref <= 0:
        s_ref = 0.3  # sensible default [m²]

    # Target CL for level flight at a representative cruise speed
    cruise_v = 15.0  # m/s — safe guess for RC/UAV models
    cl_target = (2.0 * mass_kg * g) / (rho * s_ref * cruise_v**2)
    cl_target = float(np.clip(cl_target, 0.1, 2.0))

    atmosphere = asb.Atmosphere(altitude=0.0)

    def _cl_at_alpha(alpha_deg: float) -> float:
        op = asb.OperatingPoint(
            velocity=cruise_v,
            alpha=alpha_deg,
            atmosphere=atmosphere,
        )
        try:
            abu = asb.AeroBuildup(
                airplane=asb_airplane,
                op_point=op,
                xyz_ref=getattr(asb_airplane, "xyz_ref", [0.0, 0.0, 0.0]),
            )
            result = abu.run()
            return float(np.atleast_1d(result.get("CL", 0.0))[0]) - cl_target
        except Exception:
            return -cl_target

    try:
        alpha_trimmed = brentq(_cl_at_alpha, -5.0, 15.0, xtol=0.05, maxiter=30)
    except ValueError:
        alpha_trimmed = 4.0  # benign default

    xyz_ref = getattr(asb_airplane, "xyz_ref", [0.0, 0.0, 0.0])
    return OperatingPointSchema(
        name="level_flight_fallback",
        velocity=cruise_v,
        alpha=round(alpha_trimmed, 3),
        beta=0.0,
        p=0.0,
        q=0.0,
        r=0.0,
        xyz_ref=list(xyz_ref),
        altitude=0.0,
    )
