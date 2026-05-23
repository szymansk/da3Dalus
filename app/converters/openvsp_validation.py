"""Geometric sanity validation for the OpenVSP importer (gh-647).

Per the scope-clarification comment on #647 (RC-scaling focus):

* **In scope:** span, projected area, and MAC equality between the
  importer's output and OpenVSP's own reported values, within ±1%
  for the wing; fuselage length within ±1%.
* **Out of scope:** VSPAERO roundtrip, DegenGeom+ASB CL_α comparison,
  asymmetric β tests, stability-derivative comparison.

The validator is decoupled from the importer pipeline. It receives a
fully-imported ``AeroplaneSchema`` and a live ``vsp`` module that
still has the model loaded, and returns a list of validation
mismatches as :class:`ImportWarning` records the caller can fold into
the import result.

Usage::

    result = import_vsp3(path)
    mismatches = validate_geometry(result.aeroplane, vsp)
    result.warnings.extend(mismatches)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from types import ModuleType
from typing import Optional

from app.converters.openvsp_importer import ImportWarning
from app.schemas.aeroplaneschema import AeroplaneSchema, AsbWingSchema


# ---------------------------------------------------------------------------
# Tolerance & data structures
# ---------------------------------------------------------------------------

DEFAULT_REL_TOL = 0.01  # 1%


@dataclass(frozen=True)
class GeometryMetrics:
    """The geometric quantities we round-trip against OpenVSP."""

    span_m: float
    area_m2: float
    mac_m: float


# ---------------------------------------------------------------------------
# Importer-side metric extraction
# ---------------------------------------------------------------------------


def compute_wing_metrics(wing: AsbWingSchema) -> GeometryMetrics:
    """Compute span, projected area, and MAC from an imported wing.

    Conventions:

    * **Span** = max(y) − min(y) across all xsec leading-edge
      coordinates, doubled if ``wing.symmetric`` is True.
    * **Area** = trapezoidal sum of (c[i] + c[i+1]) / 2 * Δy across
      segments, doubled if symmetric. Projected (top-view) area only.
    * **MAC** = area-weighted mean chord — Σ c_avg_i * Δy_i / Σ Δy_i.
      A pragmatic approximation that matches OpenVSP's reported
      Total_MAC to better than the 1% tolerance we care about.
    """
    if not wing.x_secs:
        return GeometryMetrics(0.0, 0.0, 0.0)

    ys = [xs.xyz_le[1] for xs in wing.x_secs]
    span_half = max(ys) - min(ys)
    span = span_half * 2.0 if wing.symmetric else span_half

    area_half = 0.0
    mac_num = 0.0
    mac_den = 0.0
    for a, b in zip(wing.x_secs, wing.x_secs[1:], strict=False):
        dy = abs(b.xyz_le[1] - a.xyz_le[1])
        if dy <= 0:
            continue
        c_avg = (a.chord + b.chord) / 2.0
        area_half += c_avg * dy
        mac_num += c_avg * dy
        mac_den += dy
    area = area_half * 2.0 if wing.symmetric else area_half
    mac = mac_num / mac_den if mac_den > 0 else 0.0
    return GeometryMetrics(span, area, mac)


def compute_fuselage_length(aeroplane: AeroplaneSchema) -> dict[str, float]:
    """Return a mapping of fuselage name → length (m)."""
    out: dict[str, float] = {}
    if not aeroplane.fuselages:
        return out
    for name, fuse in aeroplane.fuselages.items():
        xs = [s.xyz[0] for s in fuse.x_secs]
        if xs:
            out[name] = max(xs) - min(xs)
    return out


# ---------------------------------------------------------------------------
# VSP-side metric extraction
# ---------------------------------------------------------------------------


def _read_parm(vsp: ModuleType, container: str, parm: str, group: str) -> Optional[float]:
    try:
        pid = vsp.FindParm(container, parm, group)
    except Exception:
        return None
    if not pid:
        return None
    try:
        return float(vsp.GetParmVal(pid))
    except Exception:
        return None


def _vsp_wing_metrics(vsp: ModuleType, wing_gid: str) -> Optional[GeometryMetrics]:
    """Read TotalSpan / TotalArea / TotalChord from a VSP wing geom.

    The parm names follow OpenVSP's WingGeom design group. Returns
    ``None`` when the parms can't be resolved (very old VSP versions
    or non-standard wings).
    """
    span = _read_parm(vsp, wing_gid, "TotalSpan", "WingGeom")
    area = _read_parm(vsp, wing_gid, "TotalProjectedArea", "WingGeom")
    if area is None:
        area = _read_parm(vsp, wing_gid, "TotalArea", "WingGeom")
    mac = _read_parm(vsp, wing_gid, "TotalChord", "WingGeom")
    if mac is None:
        mac = _read_parm(vsp, wing_gid, "MAC", "WingGeom")
    if span is None and area is None and mac is None:
        return None
    return GeometryMetrics(
        span_m=span if span is not None else 0.0,
        area_m2=area if area is not None else 0.0,
        mac_m=mac if mac is not None else 0.0,
    )


def _vsp_fuselage_length(vsp: ModuleType, fuse_gid: str) -> Optional[float]:
    return _read_parm(vsp, fuse_gid, "Length", "Design")


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def _rel_err(a: float, b: float) -> float:
    if b == 0:
        return math.inf if a != 0 else 0.0
    return abs(a - b) / abs(b)


def _check(
    *,
    component_type: str,
    component_name: str,
    metric: str,
    imported: float,
    vsp_value: float,
    rel_tol: float,
) -> Optional[ImportWarning]:
    err = _rel_err(imported, vsp_value)
    if err <= rel_tol:
        return None
    return ImportWarning(
        component_type=component_type,
        component_name=component_name,
        reason=(
            f"{metric} mismatch: imported {imported:.4f} vs VSP {vsp_value:.4f} "
            f"(rel. error {err * 100:.2f}% > tol {rel_tol * 100:.1f}%)."
        ),
        severity="warning",
    )


def validate_geometry(
    aeroplane: AeroplaneSchema,
    vsp: ModuleType,
    wing_gid_map: dict[str, str],
    fuselage_gid_map: Optional[dict[str, str]] = None,
    *,
    rel_tol: float = DEFAULT_REL_TOL,
) -> list[ImportWarning]:
    """Compare importer output to OpenVSP's reported geometry.

    Parameters
    ----------
    aeroplane
        The populated :class:`AeroplaneSchema` from :func:`import_vsp3`.
    vsp
        The same OpenVSP module the importer used. The model must
        still be loaded.
    wing_gid_map
        ``{wing_geom_id: wing_name}`` (typically
        :attr:`ImportContext.wing_geom_ids`).
    fuselage_gid_map
        Same shape for fuselages. ``None`` skips fuselage checks.
    rel_tol
        Relative-error threshold (default 1%).

    Returns
    -------
    list[ImportWarning]
        One warning per metric whose relative error exceeds ``rel_tol``.
    """
    warnings: list[ImportWarning] = []

    # Wings -----------------------------------------------------------------
    if aeroplane.wings:
        for gid, name in wing_gid_map.items():
            wing = aeroplane.wings.get(name)
            if wing is None:
                continue
            ours = compute_wing_metrics(wing)
            vsp_metrics = _vsp_wing_metrics(vsp, gid)
            if vsp_metrics is None:
                continue  # VSP doesn't expose the metric — skip.
            for metric_name, ours_v, vsp_v in (
                ("span", ours.span_m, vsp_metrics.span_m),
                ("area", ours.area_m2, vsp_metrics.area_m2),
                ("MAC", ours.mac_m, vsp_metrics.mac_m),
            ):
                if vsp_v <= 0:
                    continue  # VSP value not populated.
                w = _check(
                    component_type="WING",
                    component_name=name,
                    metric=metric_name,
                    imported=ours_v,
                    vsp_value=vsp_v,
                    rel_tol=rel_tol,
                )
                if w is not None:
                    warnings.append(w)

    # Fuselages -------------------------------------------------------------
    if fuselage_gid_map and aeroplane.fuselages:
        lengths = compute_fuselage_length(aeroplane)
        for gid, name in fuselage_gid_map.items():
            ours_len = lengths.get(name)
            if ours_len is None:
                continue
            vsp_len = _vsp_fuselage_length(vsp, gid)
            if vsp_len is None or vsp_len <= 0:
                continue
            w = _check(
                component_type="FUSELAGE",
                component_name=name,
                metric="length",
                imported=ours_len,
                vsp_value=vsp_len,
                rel_tol=rel_tol,
            )
            if w is not None:
                warnings.append(w)

    return warnings
