"""OpenVSP FUSELAGE geom handler (gh-643).

Maps a VSP ``FUSELAGE`` geom into a :class:`FuselageSchema` whose
cross-sections are ``FuselageXSecSuperEllipseSchema`` entries.

Supported XSec shapes (super-ellipse family):

* ``XS_CIRCLE`` — diameter / 2 → a=b, n=2
* ``XS_ELLIPSE`` — width/2, height/2, n=2
* ``XS_SUPER_ELLIPSE`` — a=Super_Width/2, b=Super_Height/2,
  n=(Super_M + Super_N)/2 (with a warning if M != N)
* ``XS_ROUNDED_RECTANGLE`` — approximated by a super-ellipse with a
  high ``n`` (≈ 2..50 depending on corner radius)
* ``XS_POINT`` — nose/tail cap → a=b=0, n=2

Scope (per ``feedback_openvsp_import_rc_scope``):

* In scope: super-ellipse-family shapes above.
* Out of scope: ``XS_GENERAL_FUSE``, ``XS_FILE_FUSE``,
  ``XS_EDIT_CURVE`` (Phase 2 / B5), POD and BODYOFREVOLUTION as
  fuselages (Phase 2 / B4).

Container convention (verified empirically during implementation —
documented here as the source of truth for downstream handlers):

* Length lives on the FUSELAGE container, group ``Design``, parm
  ``Length``.
* Station positions live on the FUSELAGE container, group ``XSec``,
  parm ``XLocPercent_<i>`` (and ``YLocPercent_<i>``,
  ``ZLocPercent_<i>``).
* XSec-curve shape parms (Circle_Diameter, Ellipse_Width, etc.) live
  on the XSec curve container, accessed via
  ``vsp.GetXSecParm(xs_id, "Circle_Diameter")``.
"""

from __future__ import annotations

from types import ModuleType

from app.converters import openvsp_importer
from app.converters.openvsp_importer import AeroplaneSchema, ImportContext
from app.schemas.aeroplaneschema import (
    FuselageSchema,
    FuselageXSecSuperEllipseSchema,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_xsec_parm(vsp: ModuleType, xs_id: str, name: str) -> float:
    pid = vsp.GetXSecParm(xs_id, name)
    if not pid:
        return 0.0
    return float(vsp.GetParmVal(pid))


def _rounded_rect_to_n(*, width: float, height: float, radius: float) -> float:
    """Approximate a rounded rectangle as a super-ellipse exponent.

    Heuristic: r=0 (sharp corner) → n=50, r=min(w,h)/2 (perfect circle)
    → n=2. Linear interpolation in between. Caller already extracts
    width/height for the a, b axes.
    """
    r_max = min(width, height) / 2.0
    if r_max <= 0:
        return 2.0
    f = max(0.0, min(1.0, radius / r_max))
    n_high = 50.0
    n_low = 2.0
    return n_low + (n_high - n_low) * (1.0 - f)


def _shape_to_super_ellipse(
    vsp: ModuleType, xs_id: str, shape: int, ctx: ImportContext
) -> tuple[float, float, float]:
    """Map an XSec shape to (a, b, n) for a super-ellipse representation.

    Returns ``(0, 0, 2)`` for unsupported shapes (caller can decide
    whether to emit a warning).
    """
    if shape == getattr(vsp, "XS_CIRCLE", -1):
        d = _get_xsec_parm(vsp, xs_id, "Circle_Diameter")
        return d / 2.0, d / 2.0, 2.0

    if shape == getattr(vsp, "XS_ELLIPSE", -1):
        w = _get_xsec_parm(vsp, xs_id, "Ellipse_Width")
        h = _get_xsec_parm(vsp, xs_id, "Ellipse_Height")
        return w / 2.0, h / 2.0, 2.0

    if shape == getattr(vsp, "XS_SUPER_ELLIPSE", -1):
        w = _get_xsec_parm(vsp, xs_id, "Super_Width")
        h = _get_xsec_parm(vsp, xs_id, "Super_Height")
        m = _get_xsec_parm(vsp, xs_id, "Super_M")
        n_exp = _get_xsec_parm(vsp, xs_id, "Super_N")
        if abs(m - n_exp) > 0.01:
            ctx.add_warning(
                component_type="FUSELAGE_XSEC",
                component_name=xs_id,
                reason=(
                    f"SUPER_ELLIPSE has asymmetric M={m} vs N={n_exp}; "
                    f"using arithmetic mean {(m + n_exp) / 2.0:.3f}."
                ),
                severity="info",
            )
        return w / 2.0, h / 2.0, (m + n_exp) / 2.0

    if shape == getattr(vsp, "XS_ROUNDED_RECTANGLE", -1):
        w = _get_xsec_parm(vsp, xs_id, "RoundedRect_Width")
        h = _get_xsec_parm(vsp, xs_id, "RoundedRect_Height")
        r = _get_xsec_parm(vsp, xs_id, "RoundedRect_Radius")
        n = _rounded_rect_to_n(width=w, height=h, radius=r)
        ctx.add_warning(
            component_type="FUSELAGE_XSEC",
            component_name=xs_id,
            reason=(
                f"ROUNDED_RECTANGLE approximated as super-ellipse with "
                f"n={n:.2f}; corner radius={r:.3f}."
            ),
            severity="info",
        )
        return w / 2.0, h / 2.0, n

    if shape == getattr(vsp, "XS_POINT", -1):
        return 0.0, 0.0, 2.0

    # Unsupported shape — emit warning, return a defensible bounding ellipse.
    ctx.add_warning(
        component_type="FUSELAGE_XSEC",
        component_name=xs_id,
        reason=(
            f"XSec shape id={shape} not supported in Phase 1; "
            "falling back to a=b=0.5, n=2 placeholder."
        ),
        severity="warning",
    )
    return 0.5, 0.5, 2.0


def _read_length(vsp: ModuleType, fuse_gid: str) -> float:
    pid = vsp.FindParm(fuse_gid, "Length", "Design")
    if not pid:
        return 0.0
    return float(vsp.GetParmVal(pid))


def _read_x_pct(vsp: ModuleType, fuse_gid: str, i: int) -> float:
    pid = vsp.FindParm(fuse_gid, f"XLocPercent_{i}", "XSec")
    if not pid:
        return float(i)  # fall back to evenly-spaced index proxy
    return float(vsp.GetParmVal(pid))


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------


def _handle_fuselage(
    gid: str,
    name: str,
    aeroplane: AeroplaneSchema,
    ctx: ImportContext,
    vsp: ModuleType,
) -> None:
    """Convert one FUSELAGE geom into a ``FuselageSchema``."""
    xsurf = vsp.GetXSecSurf(gid, 0)
    n_xsec = int(vsp.GetNumXSec(xsurf))
    if n_xsec < 2:
        ctx.add_warning(
            component_type="FUSELAGE",
            component_name=name,
            reason=(f"FUSELAGE {name!r} has only {n_xsec} xsecs (need >=2); skipped."),
            severity="warning",
        )
        ctx.mark_lossy(gid)
        return

    length = _read_length(vsp, gid)
    if length <= 0:
        # Use a sensible default so we don't collapse the X axis.
        length = 1.0

    xsecs: list[FuselageXSecSuperEllipseSchema] = []
    for i in range(n_xsec):
        xs_id = vsp.GetXSec(xsurf, i)
        shape = vsp.GetXSecShape(xs_id)
        x_pct = _read_x_pct(vsp, gid, i)
        a, b, n = _shape_to_super_ellipse(vsp, xs_id, shape, ctx)
        xsecs.append(
            FuselageXSecSuperEllipseSchema(
                xyz=[x_pct * length, 0.0, 0.0],
                a=max(a, 0.0),
                b=max(b, 0.0),
                n=max(n, 1.0),
            )
        )

    fuse = FuselageSchema(name=name, x_secs=xsecs)
    if aeroplane.fuselages is None:
        from collections import OrderedDict

        aeroplane.fuselages = OrderedDict()
    aeroplane.fuselages[name] = fuse


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register() -> None:
    """Register the FUSELAGE handler with the importer skeleton."""
    openvsp_importer.register_handler("FUSELAGE", _handle_fuselage)
