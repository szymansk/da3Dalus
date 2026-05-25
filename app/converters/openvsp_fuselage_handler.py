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

Container convention (corrected after gh-702 — earlier docstring was
wrong; OpenVSP 3.50 keeps these on the XSec itself, not the parent
fuselage):

* Length lives on the FUSELAGE container, group ``Design``, parm
  ``Length``.
* Per-XSec **position** parms live on the **XSec container** in
  group ``XSec``: ``XLocPercent``, ``YLocPercent``, ``ZLocPercent``
  (no per-index suffix). Values are fractions of the fuselage length.
* XSec-curve shape parms (Circle_Diameter, Ellipse_Width, etc.) live
  on the XSec curve container, accessed via
  ``vsp.GetXSecParm(xs_id, "Circle_Diameter")``.

Geom-level XForm (translation + intrinsic XYZ rotation) is applied
after the local-frame loop, identical pattern to the wing handler
(``openvsp_wing_handler._apply_xform``). Parent-chain traversal for
child-of-BLANK geoms (NoseFairing etc.) is out of scope here — a
separate ticket.
"""

from __future__ import annotations

from types import ModuleType

from app.converters import openvsp_importer
from app.converters.openvsp_importer import AeroplaneSchema, ImportContext
from app.converters.openvsp_wing_handler import (
    _apply_xform,
    _read_geom_xform,
)
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


def _read_xsec_bounding(vsp: ModuleType, xs_id: str) -> tuple[float, float]:
    """Return the (Y-half-axis, Z-half-axis) of an XSec via the
    shape-agnostic OpenVSP accessors (gh-709).

    ``GetXSecWidth`` / ``GetXSecHeight`` work for **every** XSec shape
    in OpenVSP 3.50 — CIRCLE, ELLIPSE, SUPER_ELLIPSE, ROUNDED_RECT,
    GENERAL_FUSE, FILE_FUSE, SHIFT_LE/MID/TE, POINT — returning the
    bounding-box width/height of the cross-section in metres.

    Returns half-axes (W/2, H/2) ready for the super-ellipse schema.
    """
    w = float(vsp.GetXSecWidth(xs_id))
    h = float(vsp.GetXSecHeight(xs_id))
    return w / 2.0, h / 2.0


def _shape_to_super_ellipse(
    vsp: ModuleType, xs_id: str, shape: int, ctx: ImportContext
) -> tuple[float, float, float]:
    """Map an XSec shape to (a, b, n) for a super-ellipse representation.

    Width/Height come from ``GetXSecWidth``/``GetXSecHeight`` which
    work for **every** XSec shape. Only the super-ellipse exponent
    ``n`` is shape-specific:

    * ``XS_SUPER_ELLIPSE`` — average of the ``Super_M`` / ``Super_N``
      parms (with a warning when asymmetric).
    * ``XS_ROUNDED_RECTANGLE`` — derived from the corner radius via
      :func:`_rounded_rect_to_n` (with a warning that the corner
      detail is approximated).
    * ``XS_GENERAL_FUSE``, ``XS_FILE_FUSE``, ``XS_SHIFT_LE/MID/TE``
      — defaulted to ``n=2`` (bounding ellipse). An info-warning
      surfaces the approximation so the user knows the exact outline
      was lost.
    * Everything else — ``n=2`` silently. CIRCLE/ELLIPSE/POINT are
      true ellipses anyway.
    """
    a, b = _read_xsec_bounding(vsp, xs_id)

    if shape == getattr(vsp, "XS_SUPER_ELLIPSE", -1):
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
        return a, b, (m + n_exp) / 2.0

    if shape == getattr(vsp, "XS_ROUNDED_RECTANGLE", -1):
        r = _get_xsec_parm(vsp, xs_id, "RoundedRect_Radius")
        n = _rounded_rect_to_n(width=2.0 * a, height=2.0 * b, radius=r)
        ctx.add_warning(
            component_type="FUSELAGE_XSEC",
            component_name=xs_id,
            reason=(
                f"ROUNDED_RECTANGLE approximated as super-ellipse with "
                f"n={n:.2f}; corner radius={r:.3f}."
            ),
            severity="info",
        )
        return a, b, n

    # Shapes whose outline can't be captured by a super-ellipse
    # (GENERAL_FUSE = box-with-rounded-corners, FILE_FUSE = arbitrary
    # spline, SHIFT_LE/MID/TE = loft-control markers). For RC scaling
    # and ASB drag the bounding ellipse is plenty; surface the
    # approximation so the user knows.
    _APPROXIMATED = {
        getattr(vsp, "XS_GENERAL_FUSE", -2),
        getattr(vsp, "XS_FILE_FUSE", -3),
        getattr(vsp, "XS_SHIFT_LE", -4),
        getattr(vsp, "XS_SHIFT_MID", -5),
        getattr(vsp, "XS_SHIFT_TE", -6),
    }
    if shape in _APPROXIMATED and (a > 0.0 or b > 0.0):
        ctx.add_warning(
            component_type="FUSELAGE_XSEC",
            component_name=xs_id,
            reason=(
                f"XSec shape id={shape} (non-super-ellipse curve) "
                f"approximated as bounding ellipse a={a:.3f}, b={b:.3f}, n=2."
            ),
            severity="info",
        )

    return a, b, 2.0


def _read_length(vsp: ModuleType, fuse_gid: str) -> float:
    pid = vsp.FindParm(fuse_gid, "Length", "Design")
    if not pid:
        return 0.0
    return float(vsp.GetParmVal(pid))


def _read_loc_pct(
    vsp: ModuleType, xs_id: str, axis: str, i: int, n_xsec: int
) -> float:
    """Read ``{X,Y,Z}LocPercent`` from an XSec container.

    These parms live on the XSec itself in group ``XSec`` (OpenVSP
    3.50 convention) — NOT on the parent fuselage with an index
    suffix. Fallback when missing: an evenly-spaced fraction
    ``i / (n_xsec - 1)`` so we at least lay xsecs out along the
    spine for X and produce 0 for Y/Z.
    """
    pid = vsp.FindParm(xs_id, f"{axis}LocPercent", "XSec")
    if not pid:
        if axis == "X" and n_xsec > 1:
            return i / (n_xsec - 1)
        return 0.0
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
        x_pct = _read_loc_pct(vsp, xs_id, "X", i, n_xsec)
        y_pct = _read_loc_pct(vsp, xs_id, "Y", i, n_xsec)
        z_pct = _read_loc_pct(vsp, xs_id, "Z", i, n_xsec)
        a, b, n = _shape_to_super_ellipse(vsp, xs_id, shape, ctx)
        xsecs.append(
            FuselageXSecSuperEllipseSchema(
                xyz=[x_pct * length, y_pct * length, z_pct * length],
                a=max(a, 0.0),
                b=max(b, 0.0),
                n=max(n, 1.0),
            )
        )

    # Apply Geom-level XForm (translation + intrinsic XYZ rotation) to
    # every xsec position — same pattern as the wing handler post-gh-698.
    # Critical for Cessna 172 sub-fuselages (Struts rotated 90° about Z,
    # MainStrut rotated -90°/MainFairing/etc.).
    translation, rotation_deg = _read_geom_xform(vsp, gid)
    if any(translation) or any(rotation_deg):
        for xs in xsecs:
            xs.xyz = _apply_xform(xs.xyz, translation, rotation_deg)

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
