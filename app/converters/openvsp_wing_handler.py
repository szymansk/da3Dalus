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


def _read_relative_flag(vsp: ModuleType, wing_gid: str, parm_name: str) -> bool:
    """gh-755: read a ``Relative*Flag`` parm on the Wing container.

    OpenVSP carries ``RelativeDihedralFlag`` and ``RelativeTwistFlag``
    on the WING container (constructor: ``m_*.Init(name, m_Name, ...)``
    in WingGeom.cpp). Default ``0`` (= ABSOLUTE; per-section parm is
    world-frame). Value ``1`` switches to RELATIVE (per-section parm
    is incremental over the prior section).

    The container's group name has varied across VSP versions, so we
    try a handful of known group strings — the parm name itself is
    stable, so any positive ``FindParm`` hit wins.

    Returns ``False`` when the parm is absent (= old VSP file without
    the flag, or pre-fix import test stub — treat as absolute).
    """
    for grp in ("WingGeom", "Wing"):
        pid = vsp.FindParm(wing_gid, parm_name, grp)
        if pid:
            try:
                return bool(int(vsp.GetParmVal(pid)))
            except Exception:
                return False
    return False


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


def _chord_from_le_te(le: tuple[float, float, float], te: tuple[float, float, float]) -> float:
    """Straight-line distance LE→TE in 3D (= planform chord, in metres).

    Twist is NOT derived from these points — they're in the VSP body
    frame, which mixes dihedral and section-Z stagger into a
    ``atan2(le.z-te.z, te.x-le.x)`` geometric tilt. The PR #754
    review flagged that as wrong for any non-zero-dihedral wing
    (VTPs would get a 90° "twist" from the upright rotation). Twist
    is instead linearly interpolated between the anchor xsecs' own
    ``twist`` parm values — see :func:`_augment_same_airfoil_pairs`.

    Returns ``0.0`` when LE and TE coincide (degenerate xsec).
    """
    dx = te[0] - le[0]
    dy = te[1] - le[1]
    dz = te[2] - le[2]
    chord = math.sqrt(dx * dx + dy * dy + dz * dz)
    if chord < 1e-9:
        return 0.0
    return chord


# gh-758: probe-distance threshold for declaring two CompPnt01 samples
# "distinct". 1e-4 m = 0.1 mm — well below the smallest meaningful wing
# anchor spacing (the Spitfire's anchors are ~1 m apart) but well above
# any floating-point rounding noise in VSP's spline evaluator.
_CAP_PROBE_EPS: float = 1e-4

# gh-758: candidate u-values to probe, walked from highest (just below
# the tip) to lower. Returns the FIRST u whose LE differs from u=1.0 by
# more than _CAP_PROBE_EPS — that's the largest "safe" u (i.e. clear of
# VSP's implicit tip cap which converges to a single point as u → 1).
_CAP_PROBE_US: tuple[float, ...] = (0.99, 0.98, 0.97, 0.95, 0.92, 0.90, 0.85, 0.80, 0.70)


def _find_cap_safe_u_max(vsp: ModuleType, gid: str) -> float:
    """Return the largest spanwise ``u`` for which ``CompPnt01`` on the
    wing main surface still returns a point geometrically distinct from
    the tip (``u = 1.0``).

    VSP wings have an implicit tip cap (round / flat / etc., controlled
    by ``Cap_Tip`` parms) that occupies a small u-range near 1.0. Within
    that range, ``CompPnt01(gid, 0, u, w)`` returns points that converge
    to the cap centerline as u → 1, regardless of the chordwise ``w``.
    Inserting interpolated xsecs into this range produces (a) duplicate
    ``xyz_le`` rows and (b) Z-lifted xsecs that visually break the wing
    render — the gh-758 Cessna 172 + Spitfire reproductions.

    Method: sample LE at ``u = 1.0`` and at the values in
    :data:`_CAP_PROBE_US` (highest first). The first probe whose LE
    distance from the tip exceeds :data:`_CAP_PROBE_EPS` is returned —
    that's our largest "safe" u. If every probe converges (degenerate
    surface) or ``CompPnt01`` is unusable, return ``1.0`` so the caller
    falls back to its existing per-u failure path.
    """
    if not hasattr(vsp, "CompPnt01"):
        return 1.0
    try:
        le_at_tip, _ = _sample_le_te_at(vsp, gid, 1.0)
    except Exception:
        # CompPnt01 raised on the tip probe — no cap detection possible;
        # the augmenter's per-u except will handle individual failures.
        return 1.0

    for u_probe in _CAP_PROBE_US:
        try:
            le_probe, _ = _sample_le_te_at(vsp, gid, u_probe)
        except Exception:
            continue
        dx = le_at_tip[0] - le_probe[0]
        dy = le_at_tip[1] - le_probe[1]
        dz = le_at_tip[2] - le_probe[2]
        if math.sqrt(dx * dx + dy * dy + dz * dz) > _CAP_PROBE_EPS:
            return u_probe
    # Every probe converged (or raised) — wing is degenerate in u.
    # Returning the smallest tried probe is safer than 1.0 because we
    # know u-values up to that point are also converged; clamp inserts
    # well clear of them.
    return _CAP_PROBE_US[-1]


# gh-758: dedup threshold for consecutive output xsecs. 1e-6 m = 1 μm —
# defensively skips inserts whose LE is geometrically identical to the
# previous one. Guards against narrow caps or other VSP edge cases the
# probe might miss. Real wing anchors differ by ≥ millimetres.
_DEDUP_EPS: float = 1e-6


# gh-758: outcomes of attempting a single insert. Splits the previous
# single "cap_truncated" counter into two distinct paths so the user
# can tell whether a slightly-polygonal wing came from the tip-cap
# clamp (expected, harmless) or from the LE-dedup safety net (worth
# investigating if it ever fires on a wing without a cap).
_OUTCOME_INSERTED = "inserted"
_OUTCOME_CAP_CLAMPED = "cap_clamped"  # u > u_max — known cap region
_OUTCOME_DEDUPED = "deduped"  # LE within _DEDUP_EPS of previous xsec
_OUTCOME_FAILED = "failed"  # CompPnt01 raised or chord <= 0


def _try_emit_one_insert(
    vsp: ModuleType,
    gid: str,
    u: float,
    u_max: float,
    twist_deg: float,
    airfoil: object,
    out: list[WingXSecSchema],
) -> str:
    """Attempt to compute and append one interpolated xsec at spanwise
    ``u``. Returns one of the ``_OUTCOME_*`` strings so the caller can
    bookkeep cap-clamps, dedupes, and CompPnt01 failures separately.

    Extracted from :func:`_augment_same_airfoil_pairs` to keep the
    outer loop's cognitive complexity below SonarQube's ``python:S3776``
    threshold (= 15). Each early-return represents one decision branch
    that would otherwise have lived in the loop body.
    """
    # gh-758 #1: clamp u against the cap boundary. u_max is verified
    # distinct from the tip by _find_cap_safe_u_max, so `u > u_max` is
    # tighter than `u >= u_max` while remaining safe.
    if u > u_max:
        return _OUTCOME_CAP_CLAMPED

    # gh-753: CompPnt01 may raise on a specific u (one VSP version
    # with a known edge-case bug). Skip just this u — the renderer
    # sees one fewer xsec, and the count diff is surfaced as a warning
    # by the caller.
    try:
        le_xyz, te_xyz = _sample_le_te_at(vsp, gid, u)
    except Exception:
        return _OUTCOME_FAILED

    chord = _chord_from_le_te(le_xyz, te_xyz)
    if chord <= 0:
        return _OUTCOME_FAILED

    # gh-758 #2: defensive LE-dedup. The cap-probe in
    # _find_cap_safe_u_max can miss narrow / non-monotonic caps; if
    # the augmenter ever produces a duplicate LE despite the clamp,
    # drop it here so the DB never has consecutive identical xyz_le
    # rows (the Spitfire 8/9/10 evidence in the issue body).
    prev_le = out[-1].xyz_le
    ddx = le_xyz[0] - prev_le[0]
    ddy = le_xyz[1] - prev_le[1]
    ddz = le_xyz[2] - prev_le[2]
    if math.sqrt(ddx * ddx + ddy * ddy + ddz * ddz) < _DEDUP_EPS:
        return _OUTCOME_DEDUPED

    out.append(
        WingXSecSchema(
            xyz_le=list(le_xyz),
            chord=chord,
            twist=twist_deg,
            airfoil=airfoil,
            x_sec_type="segment",
        )
    )
    return _OUTCOME_INSERTED


def _augment_same_airfoil_pairs(
    x_secs: list[WingXSecSchema],
    vsp: ModuleType,
    gid: str,
    ctx: ImportContext,
    geom_name: str,
) -> list[WingXSecSchema]:
    """Insert ``_N_INTERP_PER_PAIR`` interpolated xsecs between every
    consecutive pair of anchors that shares the same ``airfoil``
    reference. Pairs with different airfoils are left untouched.

    The interpolated xsecs:
    - sit at evenly spaced ``u`` values between the two anchors
    - inherit the anchor's airfoil name (NACA preserved — no
      ``vsp_imported_*.dat`` generated for same-airfoil paths)
    - carry ``x_sec_type="segment"`` (intermediate, not root/tip)
    - take their ``xyz_le`` and ``chord`` from VSP's parametric
      surface via ``CompPnt01`` — the "real" Spitfire ellipse, not
      a linear interpolation between the anchors
    - get ``twist`` from a **linear interpolation between the
      bracketing anchor twists**, NOT from the body-frame LE/TE
      geometry. The body-frame ``atan2(le.z-te.z, te.x-le.x)``
      mixes dihedral into twist (PR #754 review finding #1).

    The augmenter operates in the **world frame**: anchors must
    already be XForm-applied at call time. CompPnt01 returns
    world-frame coordinates (the Geom XForm is baked into the VSP
    surface), so the inserts naturally compose with post-XForm
    anchors. The caller (``_handle_wing``) applies XForm BEFORE
    this function (gh-758 #2) — the previous order (augment first,
    XForm second) silently double-transformed every insert.

    gh-758: inserts are clamped to stay clear of VSP's implicit tip
    cap (see :func:`_find_cap_safe_u_max`). A defensive xyz_le-dedup
    guards against narrow caps or u-mapping edge cases the probe
    misses — duplicate xyz_le rows in the DB are the smoking gun the
    issue body cites for the Spitfire / Cessna 172 breakage.

    If ``vsp.CompPnt01`` is unavailable (very old VSP build or a
    test stub), the original ``x_secs`` list is returned unchanged.

    Emits ``ctx.add_warning`` (severity=info) for three distinct cases
    — split per review on PR #759 so the user can tell the causes
    apart in the import report:
    - gh-758 "tip-cap clamp" — inserts skipped because u > u_max
      (expected on any wing with a round / flat cap)
    - gh-758 "LE dedup" — inserts skipped because LE clustered to the
      previous xsec (worth investigating; means probe missed a cap)
    - gh-753 "CompPnt01 failure" — inserts skipped because CompPnt01
      raised or returned a degenerate chord
    """
    if not hasattr(vsp, "CompPnt01") or len(x_secs) < 2:
        return x_secs

    u_max = _find_cap_safe_u_max(vsp, gid)

    n_anchors = len(x_secs)
    out: list[WingXSecSchema] = []
    expected_inserts = 0
    counts: dict[str, int] = {
        _OUTCOME_INSERTED: 0,
        _OUTCOME_CAP_CLAMPED: 0,
        _OUTCOME_DEDUPED: 0,
        _OUTCOME_FAILED: 0,
    }

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
        twist_lo = float(anchor.twist or 0.0)
        twist_hi = float(nxt.twist or 0.0)
        expected_inserts += _N_INTERP_PER_PAIR

        for k in range(1, _N_INTERP_PER_PAIR + 1):
            u = u_lo + k * step
            # Linear interpolation of twist between the bracketing
            # anchors at fractional position t = k / (N_INTERP + 1).
            t = k / float(_N_INTERP_PER_PAIR + 1)
            twist_deg = twist_lo + (twist_hi - twist_lo) * t
            outcome = _try_emit_one_insert(
                vsp=vsp,
                gid=gid,
                u=u,
                u_max=u_max,
                twist_deg=twist_deg,
                airfoil=anchor.airfoil,
                out=out,
            )
            counts[outcome] += 1

    _emit_augmentation_warnings(
        ctx=ctx,
        geom_name=geom_name,
        u_max=u_max,
        expected_inserts=expected_inserts,
        counts=counts,
    )

    return out


def _emit_augmentation_warnings(
    *,
    ctx: ImportContext,
    geom_name: str,
    u_max: float,
    expected_inserts: int,
    counts: dict[str, int],
) -> None:
    """Surface per-outcome counts as info-warnings on the import context.

    Each cause gets its own warning string so a future debugger can
    tell whether a polygonal wing came from the cap clamp (expected),
    the LE dedup (rare — probe missed a cap), or a true CompPnt01
    failure (worth investigating).
    """
    cap_clamped = counts[_OUTCOME_CAP_CLAMPED]
    deduped = counts[_OUTCOME_DEDUPED]
    inserted = counts[_OUTCOME_INSERTED]
    real_failures = expected_inserts - inserted - cap_clamped - deduped

    if cap_clamped > 0:
        ctx.add_warning(
            component_type="WING",
            component_name=geom_name,
            reason=(
                f"WING {geom_name!r}: gh-758 tip-cap clamp skipped "
                f"{cap_clamped} insert(s) whose u-parameter landed in "
                f"the wing's implicit tip-cap region (u_max={u_max:.3f}). "
                "The outer tip section will be slightly less smooth than "
                "the rest of the wing — this is expected behaviour for "
                "VSP wings with a round / flat tip cap."
            ),
            severity="info",
        )

    if deduped > 0:
        ctx.add_warning(
            component_type="WING",
            component_name=geom_name,
            reason=(
                f"WING {geom_name!r}: gh-758 LE-dedup safety net "
                f"skipped {deduped} insert(s) whose LE clustered within "
                f"{_DEDUP_EPS:.0e} m of the previous xsec. The cap-probe "
                "should have caught these — this means the probe table "
                "missed a narrow / non-monotonic cap region. Wing is "
                "rendered correctly, but the probe coverage may need "
                "extending."
            ),
            severity="info",
        )

    if real_failures > 0:
        # PR #754 review finding #2 (gh-753): silently-incomplete
        # augmentation used to look polygonal without explanation.
        # Surface count diff so the user can correlate the visual
        # symptom with a real importer event.
        ctx.add_warning(
            component_type="WING",
            component_name=geom_name,
            reason=(
                f"WING {geom_name!r}: gh-753 xsec augmentation produced "
                f"{inserted}/{expected_inserts} expected inserts. "
                "Some CompPnt01 samples failed or returned a degenerate "
                "chord — the wing will render with fewer intermediate "
                "xsecs than designed."
            ),
            severity="info",
        )


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

    # gh-755: read the per-Wing Relative*Flag parms so we know
    # whether the per-section dihedral/twist parms are absolute
    # (world-frame, VSP default) or relative (incremental over prior
    # section). Pre-fix, both flags were silently ignored —
    # ``RelativeDihedralFlag=1`` profiles (e.g. DG-101G) collapsed
    # the chained dihedral on Section 2+ to flat-horizontal, visible
    # as a kink at the Section 1/2 boundary.
    relative_dihedral = _read_relative_flag(vsp, gid, "RelativeDihedralFlag")
    relative_twist = _read_relative_flag(vsp, gid, "RelativeTwistFlag")

    cum_x = 0.0
    cum_y = 0.0
    cum_z = 0.0
    # Cumulative dihedral / twist in degrees. Tracked alongside the
    # per-section values so the absolute branch can override them
    # cheaply on each iteration.
    cum_dihedral_deg = 0.0
    cum_twist_deg = 0.0
    prev_chord = root_chord

    for i in range(1, n_sec + 1):
        span = _read_section_parm(vsp, gid, i, "Span")
        tip_chord = _read_section_parm(vsp, gid, i, "Tip_Chord")
        sweep_xref = _read_section_parm(vsp, gid, i, "Sweep")
        sweep_loc = _read_section_parm(vsp, gid, i, "Sweep_Location")
        dihedral_parm = _read_section_parm(vsp, gid, i, "Dihedral")
        twist_parm = _read_section_parm(vsp, gid, i, "Twist")

        if span <= 0:
            ctx.add_warning(
                component_type="WING",
                component_name=name,
                reason=(f"WING {name!r} section {i} has Span<=0; skipping section."),
                severity="warning",
            )
            ctx.mark_lossy(gid)
            continue

        # gh-755: resolve absolute dihedral / twist for this section.
        # In RELATIVE mode the parm is added to the carried-over
        # cumulative angle (matching VSP's ``GetSumDihedral(i)``).
        # In ABSOLUTE mode the parm IS the world-frame angle, so it
        # replaces (not adds to) the carried-over value.
        if relative_dihedral:
            cum_dihedral_deg += dihedral_parm
        else:
            cum_dihedral_deg = dihedral_parm
        if relative_twist:
            cum_twist_deg += twist_parm
        else:
            cum_twist_deg = twist_parm

        # Convert sweep to LE reference so we can advance the LE point.
        # (Internal record uses c/4 if a downstream consumer wants it.)
        # Sweep stays absolute per section in VSP — no flag, no
        # accumulation; see WingGeom.cpp line 1111.
        le_sweep = sweep_at_le(
            sweep_xref_deg=sweep_xref,
            xref=sweep_loc,
            span=span,
            c_root=prev_chord,
            c_tip=tip_chord,
        )

        # gh-755: y-step now follows VSP's own formula
        # (``rad*cos(angle)``) rather than the small-angle
        # approximation ``cum_y += span`` — visible on winglets and
        # V-tail surfaces where the dihedral exceeds ~5°.
        cum_x += span * math.tan(math.radians(le_sweep))
        cum_y += span * math.cos(math.radians(cum_dihedral_deg))
        cum_z += span * math.sin(math.radians(cum_dihedral_deg))

        # Mark intermediate xsecs as `segment`; final xsec is terminal
        # and must have no segment-specific fields (Pydantic validator
        # enforces this — see AsbWingSchema.validate_last_xsec_has_no_segment_details).
        is_last = i == n_sec
        x_secs.append(
            WingXSecSchema(
                xyz_le=[cum_x, cum_y, cum_z],
                chord=tip_chord if tip_chord > 0 else prev_chord,
                twist=cum_twist_deg,
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

    # Apply Geom-level XForm (translation + intrinsic XYZ rotation) to every
    # anchor's xyz_le so that wings end up at their world-frame position and
    # orientation. Critical for HTP (aft translation) and VTP (90°-X rotation
    # that stands the wing upright). See gh-698 for the Cessna 172 regression
    # that surfaced this gap.
    #
    # gh-758 #2: XForm MUST happen BEFORE augmentation (was: after). Reason:
    # VSP's CompPnt01 returns coordinates in the WORLD FRAME (XForm already
    # baked into the surface), so for the augmenter's inserts to match the
    # anchors in frame, the anchors need to be world-frame too at that point.
    # The old order (augment first, then XForm) silently DOUBLE-XFORMED every
    # insert — visible on the Cessna 172 as "disconnected wing pieces" with
    # xsec rows showing xyz_le = 2 × translation (e.g. z = 1.42 m when the
    # wing's Z_Location is 0.71 m).
    translation, rotation_deg = _read_geom_xform(vsp, gid)
    if any(translation) or any(rotation_deg):
        for xs in x_secs:
            xs.xyz_le = _apply_xform(xs.xyz_le, translation, rotation_deg)

    # gh-753: insert interpolated xsecs between consecutive anchors that
    # share the same airfoil reference, so wings with few VSP-defined XSecs
    # (Spitfire 4-anchor elliptical wing → looks pentagonal pre-augmentation)
    # render as smooth splines. Runs in WORLD frame post-XForm — CompPnt01
    # returns world-frame coordinates so the inserts compose directly with
    # the post-XForm anchors. No further transform is applied to the inserts.
    x_secs = _augment_same_airfoil_pairs(x_secs, vsp, gid, ctx, name)

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
