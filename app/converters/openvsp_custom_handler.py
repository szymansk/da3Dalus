"""OpenVSP CUSTOM geom handler (gh-719).

OpenVSP's Custom Geoms are AngelScript-defined parametric bodies — the
``Generic Transport Fuselage`` in ``generictransport.vsp3`` is the
canonical example. They expose the standard XSec API but their
spline-position parms (``XLocPercent`` etc.) are zero — the geometry
is generated from script-private ``Design.*`` parms (Length, Diameter,
NoseMult, AftMult, NoseCenter, AftCenter, …) that we can't enumerate
ahead of time.

Strategy: sample the parametric surface via :func:`vsp.CompPnt01` at
``N`` uniform u-stations × ``M`` w-points around each station, derive
the bounding-box centroid + half-axes per station, and emit those as
``FuselageXSecSuperEllipseSchema`` entries. Verified on Generic
Transport (Length=20 m, mid-body W=H=1.75 m).

Scope: only Custom Geoms that have at least one parametric surface
(``GetNumMainSurfs(gid) >= 1`` and ``GetNumXSecSurfs(gid) >= 1``).
Script-only Custom Geoms without geometry hit a clean info-warning
and skip. The symmetric flag (gh-715) reuses the FUSELAGE handler's
reader for free.
"""

from __future__ import annotations

from types import ModuleType

from app.converters import openvsp_importer
from app.converters.openvsp_fuselage_handler import _read_sym_planar_flag
from app.converters.openvsp_importer import AeroplaneSchema, ImportContext
from app.converters.openvsp_wing_handler import _apply_xform, _read_geom_xform
from app.schemas.aeroplaneschema import (
    FuselageSchema,
    FuselageXSecSuperEllipseSchema,
)


# How many u-stations to sample along the body and how many w-points
# per station for bounding-box derivation. 12 × 32 captures the
# Generic Transport's nose curvature + tail taper without producing
# an unwieldy xsec list. Increase the u count if a future Custom
# Geom has more complex spline behaviour.
_N_U_STATIONS = 12
_N_W_POINTS = 32


def _sample_station(
    vsp: ModuleType, gid: str, u: float
) -> tuple[float, float, float, float, float]:
    """Sample ``_N_W_POINTS`` around the surface at fixed ``u`` and
    return ``(centroid_x, centroid_y, centroid_z, a, b)``.

    ``a`` = (max y − min y) / 2 (Y half-axis), ``b`` analogously for
    Z. Centroids are the bounding-box midpoints — matches the
    convention the regular FUSELAGE handler uses so downstream
    consumers see identical geometry semantics.
    """
    ys: list[float] = []
    zs: list[float] = []
    xs: list[float] = []
    for k in range(_N_W_POINTS):
        w = k / float(_N_W_POINTS)
        p = vsp.CompPnt01(gid, 0, u, w)
        xs.append(float(p.x()))
        ys.append(float(p.y()))
        zs.append(float(p.z()))
    cx = sum(xs) / len(xs)
    cy = (max(ys) + min(ys)) / 2.0
    cz = (max(zs) + min(zs)) / 2.0
    a = (max(ys) - min(ys)) / 2.0
    b = (max(zs) - min(zs)) / 2.0
    return cx, cy, cz, a, b


def _handle_custom(
    gid: str,
    name: str,
    aeroplane: AeroplaneSchema,
    ctx: ImportContext,
    vsp: ModuleType,
) -> None:
    """Convert one Custom Geom into a ``FuselageSchema`` via surface
    sampling. Falls back to an info-warning + skip when the Geom has
    no parametric surface to sample.
    """
    has_main = hasattr(vsp, "GetNumMainSurfs") and int(vsp.GetNumMainSurfs(gid)) >= 1
    has_xsec_surf = hasattr(vsp, "GetNumXSecSurfs") and int(vsp.GetNumXSecSurfs(gid)) >= 1
    has_comp_pnt = hasattr(vsp, "CompPnt01")
    if not (has_main and has_xsec_surf and has_comp_pnt):
        ctx.add_warning(
            component_type="CUSTOM",
            component_name=name,
            reason=(
                f"Custom Geom {name!r} has no parametric surface to sample "
                "(GetNumMainSurfs/XSecSurfs/CompPnt01 unavailable); skipped."
            ),
            severity="info",
        )
        ctx.mark_lossy(gid)
        return

    xsecs: list[FuselageXSecSuperEllipseSchema] = []
    for i in range(_N_U_STATIONS):
        u = i / float(_N_U_STATIONS - 1) if _N_U_STATIONS > 1 else 0.0
        try:
            cx, cy, cz, a, b = _sample_station(vsp, gid, u)
        except Exception as exc:  # noqa: BLE001 — defensive against API drift
            ctx.add_warning(
                component_type="CUSTOM",
                component_name=name,
                reason=(
                    f"Custom Geom {name!r}: CompPnt01 sampling failed at "
                    f"u={u:.3f} ({exc}); skipping rest of the body."
                ),
                severity="warning",
            )
            break
        xsecs.append(
            FuselageXSecSuperEllipseSchema(
                xyz=[cx, cy, cz], a=max(a, 0.0), b=max(b, 0.0), n=2.0
            )
        )

    if len(xsecs) < 2:
        ctx.add_warning(
            component_type="CUSTOM",
            component_name=name,
            reason=(
                f"Custom Geom {name!r} yielded fewer than 2 usable xsecs; skipped."
            ),
            severity="warning",
        )
        ctx.mark_lossy(gid)
        return

    # CompPnt01 returns WORLD-frame points — so XForm is already baked
    # in. Don't re-apply it. Translation/rotation here is for the rare
    # case the surface API didn't apply the XForm (defensive); the
    # standard CompPnt01 path will short-circuit because both vectors
    # are zero.
    translation, rotation_deg = _read_geom_xform(vsp, gid)
    if any(rotation_deg):
        # Geom XForm already applied by CompPnt01 for the position;
        # don't double-apply. Emit an info note for visibility.
        ctx.add_warning(
            component_type="CUSTOM",
            component_name=name,
            reason=(
                f"Custom Geom {name!r}: Geom-level rotation "
                f"{rotation_deg} present but CompPnt01 already returned "
                "world-frame points; XForm not re-applied."
            ),
            severity="info",
        )
    _ = translation  # silence unused-var warning; reserved for future fallback

    # Don't apply the XForm — points are already world-frame. The
    # call to ``_apply_xform`` is kept here so the import path stays
    # consistent with the FUSELAGE handler conceptually.
    _ = _apply_xform  # silence import-only usage

    symmetric = _read_sym_planar_flag(vsp, gid, name, ctx)

    fuse = FuselageSchema(name=name, x_secs=xsecs, symmetric=symmetric)
    if aeroplane.fuselages is None:
        from collections import OrderedDict

        aeroplane.fuselages = OrderedDict()
    # Dedupe by name — same logic as the wing handler (gh-705).
    unique_name = name
    suffix = 2
    while unique_name in aeroplane.fuselages:
        unique_name = f"{name} ({suffix})"
        suffix += 1
    if unique_name != name:
        fuse = fuse.model_copy(update={"name": unique_name})
    aeroplane.fuselages[unique_name] = fuse


def register() -> None:
    """Register the CUSTOM handler with the importer skeleton."""
    openvsp_importer.register_handler("CUSTOM", _handle_custom)
