"""OpenVSP WING geom handler (gh-641).

Converts a VSP ``WING`` geom into an :class:`AsbWingSchema` and
attaches it to the in-progress :class:`AeroplaneSchema`. Registered
into the skeleton handler table via :func:`register`.

Container convention (per the review comment on gh-641):

* **Planform parms** (Span, Root_Chord, Tip_Chord, Sweep,
  Sweep_Location, Dihedral, Twist) live on the **WING container**
  in group ``XSec_<i>``, where ``i`` is the section index
  ``1..n_sec``.
* The **first XSec** (index 0) is the root and carries the airfoil
  shape only. Per-segment planform parms anchor at xsec index 1 and
  describe the segment **outboard** of the previous xsec.

Sweep convention:

* OpenVSP stores ``Sweep`` at a user-selectable chord fraction
  ``Sweep_Location`` ∈ [0, 1] (0 = LE, 0.25 = c/4, 1 = TE).
* Our schema exposes geometry through ``xyz_le`` (leading-edge
  coordinates), so we convert the chord-fraction-referenced sweep
  to LE sweep for cumulative LE-X positioning.

Out of scope (per ``feedback_openvsp_import_rc_scope``): blend modes,
WING_BLEND_ANGLES, propulsion, inertia.
"""

from __future__ import annotations

import math
from types import ModuleType

from app.converters import openvsp_airfoil, openvsp_importer
from app.converters.openvsp_importer import AeroplaneSchema, ImportContext
from app.schemas.aeroplaneschema import AsbWingSchema, WingXSecSchema


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sweep_change_reference(
    *,
    sweep_from_deg: float,
    xref_from: float,
    xref_to: float,
    span: float,
    c_root: float,
    c_tip: float,
) -> float:
    """Convert a sweep angle from one chord-fraction reference to another.

    Geometry: a wing section's chord-fraction-f line lies at
        x_f(y) = x_LE(y) + f * c(y)
    where x_LE(y) = y * tan(Λ_LE) and c(y) = c_root - (c_root - c_tip)*y/span.

    The sweep at fraction f satisfies
        tan(Λ_f) = tan(Λ_LE) - f * (c_root - c_tip) / span
    and chaining two references gives
        tan(Λ_to) = tan(Λ_from) - (xref_to - xref_from) * (c_root - c_tip) / span

    Returns ``sweep_from_deg`` unchanged when ``span <= 0``.
    """
    if span <= 0:
        return sweep_from_deg
    delta = (xref_to - xref_from) * (c_root - c_tip) / span
    return math.degrees(math.atan(math.tan(math.radians(sweep_from_deg)) - delta))


def sweep_at_c4(
    *, sweep_xref_deg: float, xref: float, span: float, c_root: float, c_tip: float
) -> float:
    """Convert a sweep angle referenced at ``xref`` to the c/4 reference."""
    return _sweep_change_reference(
        sweep_from_deg=sweep_xref_deg,
        xref_from=xref,
        xref_to=0.25,
        span=span,
        c_root=c_root,
        c_tip=c_tip,
    )


def sweep_at_le(
    *, sweep_xref_deg: float, xref: float, span: float, c_root: float, c_tip: float
) -> float:
    """Convert a sweep at chord-fraction ``xref`` to the LE reference."""
    return _sweep_change_reference(
        sweep_from_deg=sweep_xref_deg,
        xref_from=xref,
        xref_to=0.0,
        span=span,
        c_root=c_root,
        c_tip=c_tip,
    )


def _airfoil_placeholder() -> str:
    """Placeholder airfoil path until #642 (XSecCurve → airfoil) lands.

    Pointing at a known-good NACA 0012 keeps the schema valid; #642
    will replace it with per-section detection.
    """
    return "./components/airfoils/naca0012.dat"


def _read_section_parm(vsp: ModuleType, wing_gid: str, section_idx: int, parm: str) -> float:
    """Best-effort read of a planform parm on the WING container.

    Tries the 1-indexed group first (``XSec_1``..``XSec_N``) — that's
    the convention used by current OpenVSP. Falls back to the
    0-indexed form for forward-compat. Returns 0.0 when the parm is
    absent so the caller can supply sensible defaults.
    """
    for grp in (f"XSec_{section_idx}", f"XSec_{section_idx - 1}"):
        pid = vsp.FindParm(wing_gid, parm, grp)
        if pid:
            return float(vsp.GetParmVal(pid))
    return 0.0


def _read_symmetric(vsp: ModuleType, wing_gid: str) -> bool:
    """Decode the Sym_Planar_Flag bitmask → wing-symmetric boolean.

    Our schema's ``symmetric`` flag means "mirrored about XZ"
    (left/right symmetry of a fixed-wing aircraft). OpenVSP encodes
    this as the SYM_XZ bit (=2) in ``Sym_Planar_Flag``.
    """
    pid = vsp.FindParm(wing_gid, "Sym_Planar_Flag", "Sym")
    if not pid:
        return False
    flag = int(vsp.GetParmVal(pid))
    sym_xz = getattr(vsp, "SYM_XZ", 2)
    return bool(flag & sym_xz)


def _read_xform_parm(vsp: ModuleType, gid: str, name: str) -> float:
    """Read a single XForm parm; 0.0 if not present."""
    pid = vsp.FindParm(gid, name, "XForm")
    if not pid:
        return 0.0
    try:
        return float(vsp.GetParmVal(pid))
    except Exception:
        return 0.0


def _read_geom_xform(
    vsp: ModuleType, gid: str
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    """Read the Geom-level XForm: (translation, rotation_deg).

    Prefers the absolute ``*_Location`` / ``*_Rotation`` parms over the
    relative ``*_Rel_*`` variants. Returns ``((0,0,0), (0,0,0))`` when
    no XForm parms are present (e.g. very old VSP files or stubbed
    test fakes).

    Discovered necessary for gh-698: WING handler previously rendered
    all wings at the origin in the X–Y plane, which broke Cessna 172
    imports (HTP overlapped with main wing, VTP rendered flat).
    """
    translation = (
        _read_xform_parm(vsp, gid, "X_Location"),
        _read_xform_parm(vsp, gid, "Y_Location"),
        _read_xform_parm(vsp, gid, "Z_Location"),
    )
    rotation_deg = (
        _read_xform_parm(vsp, gid, "X_Rotation"),
        _read_xform_parm(vsp, gid, "Y_Rotation"),
        _read_xform_parm(vsp, gid, "Z_Rotation"),
    )
    return translation, rotation_deg


def _apply_xform(
    pt: list[float] | tuple[float, float, float],
    translation: tuple[float, float, float],
    rotation_deg: tuple[float, float, float],
) -> list[float]:
    """Apply OpenVSP's Geom XForm rotation + translation to a 3D point.

    OpenVSP composes the rotation matrix as ``R = Rx · Ry · Rz`` —
    when applied to a vector ``R · v`` that means **Rz is applied to
    the vector first, then Ry, then Rx**. Reverse order would still
    pass the gh-698 StabVer test (single-axis rotation) but breaks
    on any Geom with two combined rotations like Cessna 172's
    MainStrut ``rot=(-30°, 0°, -90°)`` — see gh-717.
    """
    x, y, z = pt
    rx, ry, rz = (math.radians(a) for a in rotation_deg)
    # Rz first
    x, y = x * math.cos(rz) - y * math.sin(rz), x * math.sin(rz) + y * math.cos(rz)
    # Ry
    x, z = x * math.cos(ry) + z * math.sin(ry), -x * math.sin(ry) + z * math.cos(ry)
    # Rx last
    y, z = y * math.cos(rx) - z * math.sin(rx), y * math.sin(rx) + z * math.cos(rx)
    return [x + translation[0], y + translation[1], z + translation[2]]


# ---------------------------------------------------------------------------
# Spanwise xsec augmentation between same-airfoil anchors (gh-753)
# ---------------------------------------------------------------------------
#
# OpenVSP wings with few defined XSecs render polygonal in the
# workbench — the Spitfire's elliptical wing has only 4 anchors in
# the .vsp3, so the planform looks like a pentagon. We augment via
# VSP's ``CompPnt01`` parametric-surface sampling, *but only between
# XSec pairs that share the same airfoil reference*. The user must
# remain able to swap profiles at the anchors for Re-number scaling
# workflows — interpolated cross-airfoil xsecs would be opaque
# morphed-profile blobs the user can't edit cleanly.


# VSP wing surface parametrisation:
#   u ∈ [0, 1] — spanwise (0 = root, 1 = tip)
#   w ∈ [0, 1] — chordwise loop (0/1 = TE, 0.5 = LE — closed surface)
#
# These constants are the chordwise w-values for LE / TE sampling
# under VSP's convention. The convention is verified empirically in
# the unit tests against a stub VSP module; if VSP ever changes
# this, the tests will catch it before users see broken imports.
_W_LE: float = 0.5
_W_TE: float = 0.0

# Number of intermediate xsecs inserted between each same-airfoil
# anchor pair. 4 takes the Spitfire's 4-anchor main wing from
# pentagonal to a smooth 16-station ellipse. A future Phase-2
# ticket will switch to LE-curvature-driven adaptive sampling
# (denser at wingtips, sparser inboard); 4 is the calibrated
# baseline.
_N_INTERP_PER_PAIR: int = 4


def _sample_le_te_at(
    vsp: ModuleType, gid: str, u: float
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    """Return ``(le_xyz, te_xyz)`` for the wing surface at spanwise
    parameter ``u`` via ``CompPnt01``.

    LE and TE are sampled at the canonical chordwise positions
    (``w=0.5`` and ``w=0.0`` under VSP convention). Result is in the
    VSP body frame — the caller applies the Geom XForm later so the
    augmentation slot in the handler stays before the existing
    XForm pass.
    """
    le = vsp.CompPnt01(gid, 0, u, _W_LE)
    te = vsp.CompPnt01(gid, 0, u, _W_TE)
    return (float(le.x()), float(le.y()), float(le.z())), (
        float(te.x()),
        float(te.y()),
        float(te.z()),
    )


def _chord_and_twist_from_le_te(
    le: tuple[float, float, float], te: tuple[float, float, float]
) -> tuple[float, float]:
    """Derive ``(chord_m, twist_deg)`` from a LE/TE point pair.

    Chord is the straight-line distance LE→TE in 3D (the planform
    chord). Twist is positive when the LE sits higher than the TE
    in the wing's local frame (incidence-up). Returns ``(0.0, 0.0)``
    when LE and TE coincide (degenerate xsec).
    """
    dx = te[0] - le[0]
    dy = te[1] - le[1]
    dz = te[2] - le[2]
    chord = math.sqrt(dx * dx + dy * dy + dz * dz)
    if chord < 1e-9:
        return 0.0, 0.0
    twist_rad = math.atan2(le[2] - te[2], te[0] - le[0])
    return chord, math.degrees(twist_rad)


def _augment_same_airfoil_pairs(
    x_secs: list[WingXSecSchema],
    vsp: ModuleType,
    gid: str,
) -> list[WingXSecSchema]:
    """Insert ``_N_INTERP_PER_PAIR`` interpolated xsecs between every
    consecutive pair of anchors that shares the same ``airfoil``
    reference. Pairs with different airfoils are left untouched.

    The interpolated xsecs:
    - sit at evenly spaced ``u`` values between the two anchors
    - inherit the anchor's airfoil name (NACA preserved — no
      ``vsp_imported_*.dat`` generated for same-airfoil paths)
    - carry ``x_sec_type="segment"`` (intermediate, not root/tip)
    - take their xyz_le / chord / twist from VSP's parametric surface
      via ``CompPnt01`` — the "real" Spitfire ellipse, not a
      linear interpolation between the anchors

    The augmentation runs in the VSP body frame (before the Geom
    XForm pass) so the interpolated xsecs are transformed by the
    same pipeline as the anchors.

    If ``vsp.CompPnt01`` is unavailable (very old VSP build or a
    test stub), the original ``x_secs`` list is returned unchanged.
    """
    if not hasattr(vsp, "CompPnt01") or len(x_secs) < 2:
        return x_secs

    n_anchors = len(x_secs)
    out: list[WingXSecSchema] = []

    for i, anchor in enumerate(x_secs):
        out.append(anchor)
        if i == n_anchors - 1:
            break  # last anchor, no next pair
        nxt = x_secs[i + 1]
        if anchor.airfoil != nxt.airfoil:
            continue  # different profiles → skip (user-edit-ability)

        u_lo = i / (n_anchors - 1)
        u_hi = (i + 1) / (n_anchors - 1)
        step = (u_hi - u_lo) / (_N_INTERP_PER_PAIR + 1)

        for k in range(1, _N_INTERP_PER_PAIR + 1):
            u = u_lo + k * step
            try:
                le_xyz, te_xyz = _sample_le_te_at(vsp, gid, u)
            except Exception:
                # CompPnt01 raised — skip this u and continue. A noisy
                # raise here would mask the more common surrounding
                # cases (e.g. one VSP version missing the call); the
                # workbench renderer just sees one fewer xsec.
                continue
            chord, twist_deg = _chord_and_twist_from_le_te(le_xyz, te_xyz)
            if chord <= 0:
                continue
            out.append(
                WingXSecSchema(
                    xyz_le=list(le_xyz),
                    chord=chord,
                    twist=twist_deg,
                    airfoil=anchor.airfoil,
                    x_sec_type="segment",
                )
            )

    return out


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------


def _handle_wing(
    gid: str,
    name: str,
    aeroplane: AeroplaneSchema,
    ctx: ImportContext,
    vsp: ModuleType,
) -> None:
    """Convert one WING geom into an ``AsbWingSchema``.

    The function is intentionally tolerant of missing parms: a
    well-formed VSP file produces a clean schema; an unusual VSP
    file produces a schema plus warnings rather than an exception.
    """
    xsurf = vsp.GetXSecSurf(gid, 0)
    n_xsec = int(vsp.GetNumXSec(xsurf))
    if n_xsec < 2:
        ctx.add_warning(
            component_type="WING",
            component_name=name,
            reason=f"WING {name!r} has only {n_xsec} XSecs (need ≥2); skipped.",
            severity="warning",
        )
        ctx.mark_lossy(gid)
        return

    n_sec = n_xsec - 1
    symmetric = _read_symmetric(vsp, gid)

    def _airfoil_for(xs_index: int) -> str:
        """Resolve airfoil via openvsp_airfoil; fall back to placeholder on error."""
        try:
            xs_id = vsp.GetXSec(xsurf, xs_index)
        except Exception:
            return _airfoil_placeholder()
        try:
            return openvsp_airfoil.import_airfoil_from_xsec(
                xs_id=xs_id,
                geom_id=gid,
                xsurf=xsurf,
                xs_index=xs_index,
                ctx=ctx,
                vsp=vsp,
            )
        except Exception:
            return _airfoil_placeholder()

    # Build the xsec list. Section index i (1..n_sec) describes the
    # segment OUTBOARD of XSec[i-1] and terminating at XSec[i].
    x_secs: list[WingXSecSchema] = []

    # Root xsec at (0, 0, 0) with chord = section_1.Root_Chord.
    root_chord = _read_section_parm(vsp, gid, 1, "Root_Chord")
    if root_chord <= 0:
        ctx.add_warning(
            component_type="WING",
            component_name=name,
            reason=f"WING {name!r} has Root_Chord<=0 on first section; defaulting to 1.0 m.",
            severity="warning",
        )
        root_chord = 1.0

    x_secs.append(
        WingXSecSchema(
            xyz_le=[0.0, 0.0, 0.0],
            chord=root_chord,
            twist=0.0,
            airfoil=_airfoil_for(0),
            x_sec_type="root",
        )
    )

    cum_x = 0.0
    cum_y = 0.0
    cum_z = 0.0
    prev_chord = root_chord

    for i in range(1, n_sec + 1):
        span = _read_section_parm(vsp, gid, i, "Span")
        tip_chord = _read_section_parm(vsp, gid, i, "Tip_Chord")
        sweep_xref = _read_section_parm(vsp, gid, i, "Sweep")
        sweep_loc = _read_section_parm(vsp, gid, i, "Sweep_Location")
        dihedral = _read_section_parm(vsp, gid, i, "Dihedral")
        twist = _read_section_parm(vsp, gid, i, "Twist")

        if span <= 0:
            ctx.add_warning(
                component_type="WING",
                component_name=name,
                reason=(f"WING {name!r} section {i} has Span<=0; skipping section."),
                severity="warning",
            )
            ctx.mark_lossy(gid)
            continue

        # Convert sweep to LE reference so we can advance the LE point.
        # (Internal record uses c/4 if a downstream consumer wants it.)
        le_sweep = sweep_at_le(
            sweep_xref_deg=sweep_xref,
            xref=sweep_loc,
            span=span,
            c_root=prev_chord,
            c_tip=tip_chord,
        )

        cum_x += span * math.tan(math.radians(le_sweep))
        cum_y += span
        cum_z += span * math.tan(math.radians(dihedral))

        # Mark intermediate xsecs as `segment`; final xsec is terminal
        # and must have no segment-specific fields (Pydantic validator
        # enforces this — see AsbWingSchema.validate_last_xsec_has_no_segment_details).
        is_last = i == n_sec
        x_secs.append(
            WingXSecSchema(
                xyz_le=[cum_x, cum_y, cum_z],
                chord=tip_chord if tip_chord > 0 else prev_chord,
                twist=twist,
                airfoil=_airfoil_for(i),
                x_sec_type=None if is_last else "segment",
            )
        )
        prev_chord = tip_chord if tip_chord > 0 else prev_chord

    if len(x_secs) < 2:
        ctx.add_warning(
            component_type="WING",
            component_name=name,
            reason=f"WING {name!r} produced <2 valid xsecs after parsing; skipped.",
            severity="warning",
        )
        ctx.mark_lossy(gid)
        return

    # gh-753: insert interpolated xsecs between consecutive anchors
    # that share the same airfoil reference, so wings with few VSP-
    # defined XSecs (Spitfire 4-anchor elliptical wing → looks
    # pentagonal pre-augmentation) render as smooth splines. Runs in
    # the VSP body frame before XForm so the new xsecs are
    # transformed alongside the anchors.
    x_secs = _augment_same_airfoil_pairs(x_secs, vsp, gid)

    # Apply Geom-level XForm (translation + intrinsic XYZ rotation) to every
    # xyz_le so that wings end up at their world-frame position and orientation.
    # Critical for HTP (aft translation) and VTP (90°-X rotation that stands
    # the wing upright). See gh-698 for the Cessna 172 regression that
    # surfaced this gap.
    translation, rotation_deg = _read_geom_xform(vsp, gid)
    if any(translation) or any(rotation_deg):
        for xs in x_secs:
            xs.xyz_le = _apply_xform(xs.xyz_le, translation, rotation_deg)

    wing = AsbWingSchema(
        name=name,
        symmetric=symmetric,
        x_secs=x_secs,
    )

    if aeroplane.wings is None:
        # OrderedDict preserves insertion order (FindGeoms tree traversal).
        from collections import OrderedDict

        aeroplane.wings = OrderedDict()
    aeroplane.wings[name] = wing
    # Record gid→name so SS_CONTROL post-pass (gh-644) can find this wing.
    ctx.wing_geom_ids[gid] = name


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register() -> None:
    """Register the WING handler with the importer skeleton."""
    openvsp_importer.register_handler("WING", _handle_wing)
