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
