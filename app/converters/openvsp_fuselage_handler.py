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


def _fit_n_from_xsec_points(
    points_yz: list[tuple[float, float]], a: float, b: float
) -> float:
    """Fit the super-ellipse exponent ``n`` against sampled outline points.

    Super-ellipse: ``|y/a|^n + |z/b|^n = 1``. Given a sample of (y, z)
    points on the outline plus the bounding-box half-axes (a, b), pick
    the ``n ∈ [1, 50]`` that minimises the sum of squared implicit
    residuals. Returns ``2.0`` (plain ellipse) for degenerate inputs:
    a or b ≤ 0, no usable off-axis points.

    Used by the OpenVSP fuselage handler (gh-713) for shapes whose
    outline isn't analytically known — GENERAL_FUSE, FILE_FUSE,
    SHIFT_LE/MID/TE. The bounding box (a, b) is trusted (it comes
    from ``GetXSecWidth``/``GetXSecHeight``); only the squareness
    exponent is fitted.
    """
    if a <= 0.0 or b <= 0.0:
        return 2.0

    # Keep only points that contribute information about the exponent:
    # near-axis samples (|u| or |v| ≈ 0) are dominated by the other
    # term and don't help discriminate between candidate n values.
    valid = [
        (abs(y) / a, abs(z) / b)
        for y, z in points_yz
        if abs(y) / a > 0.1 and abs(z) / b > 0.1
    ]
    if len(valid) < 3:
        return 2.0

    # scipy is already a transitive dep via aerosandbox, so no new
    # runtime cost. ``bounded`` minimisation needs no initial guess
    # and clamps automatically — perfect for a constrained 1-D fit.
    from scipy.optimize import minimize_scalar

    def _residual_sum(n: float) -> float:
        return sum((u**n + v**n - 1.0) ** 2 for u, v in valid)

    res = minimize_scalar(_residual_sum, bounds=(1.0, 50.0), method="bounded")
    return float(res.x)


def _sample_xsec_yz(
    vsp: ModuleType, xs_id: str, n_points: int = 24
) -> list[tuple[float, float]]:
    """Sample (y, z) points around an XSec outline via ``ComputeXSecPnt``.

    Returns world-frame (y, z) tuples relative to the XSec's own
    centre. Returns ``[]`` when the API is unavailable on the running
    OpenVSP build or any sample call fails — caller falls back to the
    safe default ``n=2``.
    """
    if not hasattr(vsp, "ComputeXSecPnt"):
        return []
    pts: list[tuple[float, float]] = []
    for k in range(n_points):
        fract = k / float(n_points)
        try:
            p = vsp.ComputeXSecPnt(xs_id, fract)
        except Exception:  # noqa: BLE001 — defensive against any API drift
            return []
        try:
            y = float(p.y())
            z = float(p.z())
        except Exception:  # noqa: BLE001
            return []
        pts.append((y, z))
    if not pts:
        return []
    # ComputeXSecPnt returns world-frame coords — subtract the
    # bounding-box centre so the sample is centred on the origin,
    # matching the super-ellipse equation's frame.
    y_mid = (max(y for y, _ in pts) + min(y for y, _ in pts)) / 2.0
    z_mid = (max(z for _, z in pts) + min(z for _, z in pts)) / 2.0
    return [(y - y_mid, z - z_mid) for y, z in pts]


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

    # Shapes whose outline isn't analytically known — GENERAL_FUSE
    # (box-with-rounded-corners), FILE_FUSE (arbitrary spline),
    # SHIFT_LE/MID/TE (loft-control markers). Sample the outline via
    # ``ComputeXSecPnt`` and fit the super-ellipse exponent so the
    # shape isn't forced to be a plain ellipse (gh-713). For a typical
    # Cessna-style Mansardendach this drops the radial residual from
    # ~26 cm (n=2) to <5 cm (n≈3–4).
    _FIT_SHAPES = {
        getattr(vsp, "XS_GENERAL_FUSE", -2),
        getattr(vsp, "XS_FILE_FUSE", -3),
        getattr(vsp, "XS_SHIFT_LE", -4),
        getattr(vsp, "XS_SHIFT_MID", -5),
        getattr(vsp, "XS_SHIFT_TE", -6),
    }
    if shape in _FIT_SHAPES and (a > 0.0 or b > 0.0):
        sampled = _sample_xsec_yz(vsp, xs_id)
        n_fit = _fit_n_from_xsec_points(sampled, a, b) if sampled else 2.0
        ctx.add_warning(
            component_type="FUSELAGE_XSEC",
            component_name=xs_id,
            reason=(
                f"XSec shape id={shape} (non-super-ellipse curve) "
                f"approximated as super-ellipse a={a:.3f}, b={b:.3f}, "
                f"n={n_fit:.2f} {'(fitted)' if sampled else '(default — sampling unavailable)'}."
            ),
            severity="info",
        )
        return a, b, n_fit

    return a, b, 2.0


def _read_length(vsp: ModuleType, fuse_gid: str) -> float:
    pid = vsp.FindParm(fuse_gid, "Length", "Design")
    if not pid:
        return 0.0
    return float(vsp.GetParmVal(pid))


# Sym_Planar_Flag enum values used by OpenVSP. We only support XZ
# (the typical mirror for left/right paired sub-fuselages); anything
# else falls back to ``symmetric=False`` with an info-warning.
_SYM_XZ = 2


def _read_sym_planar_flag(
    vsp: ModuleType, gid: str, name: str, ctx: ImportContext
) -> bool:
    """Return ``True`` iff the geom is marked XZ-symmetric (gh-715).

    OpenVSP exposes per-geom symmetry via the ``Sym_Planar_Flag`` parm
    in group ``Sym``. Cessna 172 uses ``Sym_Planar_Flag = 2`` (XZ) on
    paired sub-fuselages (Struts, MainFairing, MainStrut) — the GUI
    auto-mirrors them about the XZ plane. Other modes (XY, YZ, multi)
    are extremely rare for fuselages and emit a warning + fall back
    to non-symmetric.
    """
    pid = vsp.FindParm(gid, "Sym_Planar_Flag", "Sym")
    if not pid:
        return False
    val = int(vsp.GetParmVal(pid))
    if val == 0:
        return False
    if val == _SYM_XZ:
        return True
    ctx.add_warning(
        component_type="FUSELAGE",
        component_name=name,
        reason=(
            f"FUSELAGE {name!r} has Sym_Planar_Flag={val} which is not "
            f"the supported XZ mode; importing as non-symmetric."
        ),
        severity="info",
    )
    return False


def _read_loc_pct(
    vsp: ModuleType, xs_id: str, axis: str, i: int, n_xsec: int
) -> float:
    """Read ``{X,Y,Z}LocPercent`` from an XSec container.

    OpenVSP 3.50 convention (gh-711): the position parms live on the
    XSec container in group ``XSec``, but ``FindParm(xs_id, …, "XSec")``
    silently returns ``""`` for XSec containers. The only reliable
    access path is ``GetXSecParm`` — the same family we use for shape
    parms (``Circle_Diameter``, ``Super_Width`` …).

    Fallback when the parm genuinely isn't there (rare — should only
    happen for degenerate stub fuselages): an evenly-spaced fraction
    ``i / (n_xsec - 1)`` for X, ``0`` for Y/Z.
    """
    pid = vsp.GetXSecParm(xs_id, f"{axis}LocPercent")
    if not pid:
        if axis == "X" and n_xsec > 1:
            return i / (n_xsec - 1)
        return 0.0
    return float(vsp.GetParmVal(pid))


# ---------------------------------------------------------------------------
# gh-721: adaptive xsec refinement at high-curvature sections
# ---------------------------------------------------------------------------


# Default hard cap so a pathologically curved body doesn't explode our
# DB-row count. 100 matches real-world OpenVSP Geoms (RV-7 sub-fuselages
# etc.). User-tunable via the import endpoint's ``xsec_max_count`` param
# (gh-721) threaded through ``ImportContext.xsec_max_count``.
_DEFAULT_MAX_XSECS = 100
# Max bisection depth — 4 levels means each original section can grow into
# up to 16 sub-sections before we give up.
_MAX_REFINEMENT_DEPTH = 4


def sample_station_via_comp_pnt(
    vsp: ModuleType, gid: str, u: float, n_w: int = 32
) -> tuple[float, float, float, float, float]:
    """Sample ``n_w`` points around the parametric surface at fixed ``u``
    and return ``(centroid_x, centroid_y, centroid_z, a, b)``.

    Shared by the FUSELAGE handler's refinement pass (gh-721) and the
    CUSTOM handler's primary loop (gh-719). Half-axes ``a`` / ``b`` are
    the Y / Z bounding-box half-widths.
    """
    xs_list: list[float] = []
    ys: list[float] = []
    zs: list[float] = []
    for k in range(n_w):
        w = k / float(n_w)
        p = vsp.CompPnt01(gid, 0, u, w)
        xs_list.append(float(p.x()))
        ys.append(float(p.y()))
        zs.append(float(p.z()))
    cx = sum(xs_list) / len(xs_list)
    cy = (max(ys) + min(ys)) / 2.0
    cz = (max(zs) + min(zs)) / 2.0
    a = (max(ys) - min(ys)) / 2.0
    b = (max(zs) - min(zs)) / 2.0
    return cx, cy, cz, a, b


def _refine_xsecs_adaptive(
    vsp: ModuleType,
    gid: str,
    xsec_us: list[float],
    xsecs: list[FuselageXSecSuperEllipseSchema],
    *,
    tol_m: float,
    ctx: ImportContext,
    component_name: str,
) -> tuple[list[float], list[FuselageXSecSuperEllipseSchema]]:
    """Adaptive bisection refinement (gh-721).

    For each section between consecutive xsecs, sample the VSP-spline
    midpoint and compare against the linear interpolation our schema
    would produce. The worst component (centroid_z, a, or b) is the
    section's "error".

    Priority-by-error (gh-721 follow-up): in each depth iteration we
    rank ALL out-of-tolerance candidate midpoints by their error and
    insert highest-error first, up to the global xsec cap. This keeps
    the budget on the sections that need it — without priority the
    naive left-to-right insertion would starve the most-curved
    sections at the tail (Cessna's "wespentaille" was ending up with
    only 1 insert instead of 16).

    Bails out at ``_MAX_REFINEMENT_DEPTH`` recursions or
    ``cap`` total xsecs. Requires the running
    OpenVSP build to expose ``CompPnt01``; old builds silently fall
    back to the original xsec list.
    """
    if tol_m <= 0.0 or not hasattr(vsp, "CompPnt01"):
        return xsec_us, xsecs

    cap = max(int(getattr(ctx, "xsec_max_count", _DEFAULT_MAX_XSECS)), len(xsecs))
    us = list(xsec_us)
    xs = list(xsecs)
    capped = False

    for _ in range(_MAX_REFINEMENT_DEPTH):
        # Pass 1: gather every out-of-tolerance midpoint with its
        # error and the candidate FuselageXSec it would produce.
        # Candidates carry (error, after_index, u_mid, schema).
        candidates: list[
            tuple[float, int, float, FuselageXSecSuperEllipseSchema]
        ] = []
        for i in range(len(us) - 1):
            u_mid = (us[i] + us[i + 1]) / 2.0
            try:
                _cx, _cy, cz, a, b = sample_station_via_comp_pnt(vsp, gid, u_mid)
            except Exception:  # noqa: BLE001
                continue
            approx_cz = (xs[i].xyz[2] + xs[i + 1].xyz[2]) / 2.0
            approx_a = (xs[i].a + xs[i + 1].a) / 2.0
            approx_b = (xs[i].b + xs[i + 1].b) / 2.0
            err = max(abs(cz - approx_cz), abs(a - approx_a), abs(b - approx_b))
            if err <= tol_m:
                continue
            approx_cx = (xs[i].xyz[0] + xs[i + 1].xyz[0]) / 2.0
            approx_cy = (xs[i].xyz[1] + xs[i + 1].xyz[1]) / 2.0
            candidates.append(
                (
                    err,
                    i,
                    u_mid,
                    FuselageXSecSuperEllipseSchema(
                        # Trust the VSP surface for height-axis values
                        # but keep the linear-interp X/Y centroid so the
                        # spine stays smooth in the schema frame.
                        xyz=[approx_cx, approx_cy, cz],
                        a=max(a, 0.0),
                        b=max(b, 0.0),
                        n=2.0,
                    ),
                )
            )

        if not candidates:
            break

        # Priority order: biggest error first. Then clip to whatever
        # budget the cap allows so the worst-curved sections always
        # land before lesser ones.
        candidates.sort(key=lambda c: c[0], reverse=True)
        budget = cap - len(xs)
        if budget <= 0:
            capped = True
            break
        if len(candidates) > budget:
            capped = True
            candidates = candidates[:budget]

        # Pass 2: splice the selected inserts back into the section
        # order. Sort by after_index so we walk left-to-right and
        # build the new lists in O(n).
        candidates.sort(key=lambda c: c[1])
        new_us: list[float] = []
        new_xs: list[FuselageXSecSuperEllipseSchema] = []
        cand_iter = iter(candidates)
        nxt = next(cand_iter, None)
        for i in range(len(us)):
            new_us.append(us[i])
            new_xs.append(xs[i])
            while nxt is not None and nxt[1] == i:
                _err, _after, u_mid, schema_xs = nxt
                new_us.append(u_mid)
                new_xs.append(schema_xs)
                nxt = next(cand_iter, None)
        us, xs = new_us, new_xs

    if capped:
        ctx.add_warning(
            component_type="FUSELAGE",
            component_name=component_name,
            reason=(
                f"FUSELAGE {component_name!r}: hit the {cap}-xsec cap "
                "during adaptive refinement; some high-curvature sections "
                "may still exceed the tolerance. Raise the cap via the "
                "import endpoint's ``xsec_max_count`` if needed."
            ),
            severity="info",
        )

    return us, xs


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
    xsec_us: list[float] = []
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
        # u parameter for the surface query is the same XLocPercent
        # (OpenVSP's parametric u matches the body fraction).
        xsec_us.append(x_pct)

    # gh-721: optional adaptive refinement at high-curvature sections.
    # Run BEFORE XForm so the CompPnt01-derived points live in the
    # same local frame as ``xsecs`` (the XForm pass below transforms
    # all of them at once).
    tol_rel = ctx.xsec_tolerance_rel
    if tol_rel > 0.0 and length > 0.0:
        _, xsecs = _refine_xsecs_adaptive(
            vsp, gid, xsec_us, xsecs,
            tol_m=length * tol_rel,
            ctx=ctx,
            component_name=name,
        )

    # Apply Geom-level XForm (translation + intrinsic XYZ rotation) to
    # every xsec position — same pattern as the wing handler post-gh-698.
    # Critical for Cessna 172 sub-fuselages (Struts rotated 90° about Z,
    # MainStrut rotated -90°/MainFairing/etc.).
    translation, rotation_deg = _read_geom_xform(vsp, gid)
    if any(translation) or any(rotation_deg):
        for xs in xsecs:
            xs.xyz = _apply_xform(xs.xyz, translation, rotation_deg)

    symmetric = _read_sym_planar_flag(vsp, gid, name, ctx)

    fuse = FuselageSchema(name=name, x_secs=xsecs, symmetric=symmetric)
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
