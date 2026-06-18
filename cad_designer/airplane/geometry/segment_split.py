"""Main-spar segment split (gh-1059).

A telescoping main (front) spar has a varying diameter along the span. VaseMode
construction treats **any** ``spar_index == 0`` spar in a segment as THE main
spar, so a multi-piece (telescoping) main spar cannot live as several index-0
pieces in one segment — each diameter needs its own segment with exactly one
main piece at index 0.

This module splits a host :class:`WingConfiguration` segment at one or more
spanwise fractions into N contiguous sub-segments. The split is **geometrically
transparent**: the built loft is unchanged. That holds because the loft is
*ruled* (``loft(ruled=True)`` — a straight, linear blend between the root and
tip airfoils), so an intermediate section is fully determined by:

* the **linearly interpolated** chord / sweep / length at the split fraction,
* the **dihedral** carried on the last sub-segment (intermediate boundaries get
  zero) so every intermediate origin stays on the original straight ruled line,
* the **twist (incidence)** split so each boundary's chord-weighted twist matches
  the original ruled blend — a plain linear twist split drifts a tapered host's
  section center_z by ~0.7mm (gh-1068), so the per-sub-segment delta is the
  difference of ``_boundary_twist_cumulative`` instead, and
* the **airfoil shape** at the split fraction — the same file when root and tip
  share an airfoil, otherwise a Kulfan/CST morph (gh-796) supplied via the
  injected ``airfoil_morph_fn`` seam.

**Read-only topology.** We never modify the ``Airfoil`` / ``WingSegment`` /
``WingConfiguration`` / ``Spare`` / ``TrailingEdgeDevice`` / ``Turbulator``
classes — we only *construct* new instances and assemble a fresh
``WingConfiguration`` via ``add_segment`` / ``add_tip_segment``.

**Children at a split:**

* **Control surface** (``TrailingEdgeDevice``) spans the whole segment, so it is
  **duplicated** onto every sub-segment over its sub-span: the chordwise hinge
  line and side spacing are linearly interpolated to the sub-span boundaries,
  and the name is disambiguated (the ``[role]`` tag is preserved per the
  gh-772/gh-955 mixing rules; the display part gets a per-sub-segment ordinal so
  the control-variable names stay globally unique and never collapse into one
  AVL DOF). The servo (if any) stays on the sub-segment that contains it.
* **Turbulator** is only a surface bump → carried onto every sub-segment with
  its chordwise position linearly interpolated to the sub-span.
* **Existing/manual spares** are re-homed to the sub-segment whose span contains
  the spare's (segment-local) origin y.
* The **main-spar pieces** for each sub-segment are supplied by the caller
  (``main_pieces_per_subsegment``) and placed at ``spar_list[0]`` — the index-0
  invariant the spar-insert relies on.

Units: **millimetres**, wing-local frame — same as the topology classes.
"""

from __future__ import annotations

import math
from typing import Callable, Optional

from cad_designer.airplane.aircraft_topology.wing.Airfoil import Airfoil
from cad_designer.airplane.aircraft_topology.wing.Spare import Spare
from cad_designer.airplane.aircraft_topology.wing.TrailingEdgeDevice import (
    TrailingEdgeDevice,
)
from cad_designer.airplane.aircraft_topology.wing.Turbulator import Turbulator
from cad_designer.airplane.aircraft_topology.wing.WingConfiguration import (
    WingConfiguration,
)
from cad_designer.airplane.aircraft_topology.wing.WingSegment import WingSegment

#: Signature of the airfoil-morph seam: ``morph(root_file, tip_file, t) -> path``
#: (or ``None`` on failure). Matches ``app.converters.openvsp_airfoil.morph_airfoils``.
AirfoilMorphFn = Callable[[str, str, float], Optional[str]]

_FRACTION_TOL = 1e-9


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _boundary_twist_cumulative(
    boundaries: list[float],
    root_twist_cum: float,
    tip_twist_cum: float,
    root_chord: float,
    tip_chord: float,
) -> list[float]:
    """Cumulative twist (deg) at each split boundary that keeps the built ruled
    loft unchanged for a tapered+twisted host (gh-1068).

    ``root_twist_cum`` / ``tip_twist_cum`` are the host root/tip wires' *absolute*
    cumulative twist (``theta_accum`` in the loft frame — the host root's value
    plus, for the tip, the host's own incidence delta).

    The host loft is a *ruled* (point-wise linear) blend of its root and tip
    wires. A surface point's world-z carries a ``chord · sin(twist)`` term from
    the chordwise offset of the twisted section. Over the span that term blends
    **linearly** between the two end wires:

        z_term(t) ∝ (1 - t) · c_root · sin(θ_root) + t · c_tip · sin(θ_tip)

    where ``c(t) = lerp(c_root, c_tip, t)`` is the (linear) ruled chord. An
    inserted intermediate wire at fraction ``t`` has its own ``c(t) · sin(θ)``,
    so to reproduce the blend exactly its twist must satisfy

        sin(θ(t)) = [ (1-t)·c_root·sin(θ_root) + t·c_tip·sin(θ_tip) ] / c(t)

    For an untapered host this is the blended-up-vector twist (within a sub-0.01°
    sin-arc of the plain linear split); for a tapered host it removes the ~0.7mm
    center_z drift the linear split caused. The per-sub-segment incidence delta
    is the difference of consecutive returned values, so a constant inboard-chain
    twist offset cancels and does not affect the result.
    """
    s_root = root_chord * math.sin(math.radians(root_twist_cum))
    s_tip = tip_chord * math.sin(math.radians(tip_twist_cum))
    out: list[float] = []
    for t in boundaries:
        chord = _lerp(root_chord, tip_chord, t)
        if chord <= 0.0:
            out.append(_lerp(root_twist_cum, tip_twist_cum, t))
            continue
        s = _lerp(s_root, s_tip, t) / chord
        s = max(-1.0, min(1.0, s))
        out.append(math.degrees(math.asin(s)))
    return out


def _validate_fractions(fractions: list[float]) -> None:
    """Reject fractions that are out of (0, 1) or not strictly increasing."""
    prev = 0.0
    for f in fractions:
        if not (_FRACTION_TOL < f < 1.0 - _FRACTION_TOL):
            raise ValueError(
                f"split fraction {f} must be strictly inside (0, 1); 0 and 1 are "
                "the segment's own boundaries and do not create a new section."
            )
        if f <= prev + _FRACTION_TOL:
            raise ValueError(f"split fractions must be strictly increasing; got {fractions}.")
        prev = f


def _interp_airfoil(
    root_af: Airfoil,
    tip_af: Airfoil,
    t: float,
    airfoil_morph_fn: AirfoilMorphFn | None,
) -> Airfoil:
    """Build the intermediate airfoil at fraction ``t`` along the segment.

    Chord / incidence-delta / dihedral-delta are linearly blended (see
    :func:`split_segment` for the delta bookkeeping — this only sets the chord
    and the airfoil *file*; the angle splitting is handled by the caller). When
    the two anchors share an airfoil file the same file is kept (the ruled loft
    of one shape is exact); otherwise the file is a Kulfan/CST morph at ``t``,
    falling back to the inboard anchor's file when morphing is unavailable or
    fails.
    """
    chord = _lerp(root_af.chord, tip_af.chord, t)
    root_file = root_af.airfoil
    tip_file = tip_af.airfoil
    if root_file == tip_file or tip_file is None:
        airfoil_file = root_file
    elif airfoil_morph_fn is not None:
        morphed = airfoil_morph_fn(root_file, tip_file, t)
        airfoil_file = morphed if morphed is not None else root_file
    else:
        # No morph seam supplied for differing anchors: keep the inboard form so
        # the section is still buildable (a faithful, if approximate, capture).
        airfoil_file = root_file
    return Airfoil(airfoil=airfoil_file, chord=chord)


def _split_ted(ted: TrailingEdgeDevice, t0: float, t1: float, ordinal: int) -> TrailingEdgeDevice:
    """Duplicate a control surface over the sub-span ``[t0, t1]``.

    The hinge line (``rel_chord_*``) and side spacing taper linearly along the
    whole original segment, so the sub-span endpoints are the values at ``t0``
    and ``t1``. The name is disambiguated for sub-segments after the first so
    the per-surface control-variable names stay globally unique (gh-955); the
    ``[role]`` tag (gh-772) is preserved so the mixing pipeline still recovers
    the role. The servo only rides the sub-segment that contains it.
    """
    rc_root = ted.rel_chord_root
    rc_tip = ted.rel_chord_tip if ted.rel_chord_tip is not None else ted.rel_chord_root
    new_rc_root = _lerp(rc_root, rc_tip, t0)
    new_rc_tip = _lerp(rc_root, rc_tip, t1)

    ss_root = ted.side_spacing_root
    ss_tip = ted.side_spacing_tip if ted.side_spacing_tip is not None else ted.side_spacing_root
    new_ss_root = (
        _lerp(ss_root, ss_tip, t0) if ss_root is not None and ss_tip is not None else ss_root
    )
    new_ss_tip = (
        _lerp(ss_root, ss_tip, t1) if ss_root is not None and ss_tip is not None else ss_tip
    )

    # Servo placement: keep it only on the sub-span that contains it.
    servo = None
    servo_chord = ted.rel_chord_servo_position
    new_servo_len = ted.rel_length_servo_position
    rel_len = ted.rel_length_servo_position
    if ted._servo is not None and (
        rel_len is None or t0 - _FRACTION_TOL <= rel_len <= t1 + _FRACTION_TOL
    ):
        servo = ted._servo
        # re-express the servo's spanwise position within the sub-span.
        if rel_len is not None and (t1 - t0) > _FRACTION_TOL:
            new_servo_len = (rel_len - t0) / (t1 - t0)
    else:
        servo_chord = None
        new_servo_len = None

    return TrailingEdgeDevice(
        name=_disambiguate_name(ted.name, ordinal),
        rel_chord_root=new_rc_root,
        rel_chord_tip=new_rc_tip,
        hinge_spacing=ted.hinge_spacing,
        side_spacing_root=new_ss_root,
        side_spacing_tip=new_ss_tip,
        servo=servo,
        servo_placement=ted.servo_placement,
        rel_chord_servo_position=servo_chord,
        rel_length_servo_position=new_servo_len,
        positive_deflection_deg=ted.positive_deflection_deg,
        negative_deflection_deg=ted.negative_deflection_deg,
        trailing_edge_offset_factor=ted.trailing_edge_offset_factor,
        hinge_type=ted.hinge_type,
        symmetric=ted.symmetric,
    )


def _disambiguate_name(name: str, ordinal: int) -> str:
    """Make a duplicated control surface's name globally unique.

    Sub-segment 0 keeps the original name verbatim. Later sub-segments append a
    ``#<ordinal>`` suffix to the **display** part, preserving any ``[role]``
    prefix so ``control_surface_mixing.parse_role_tag`` still recovers the role
    (gh-772). AVL/ASB collapse same-named CONTROL variables into one DOF, so the
    suffix prevents N duplicated surfaces from silently merging (gh-955).
    """
    if ordinal == 0:
        return name
    if name.startswith("[") and "]" in name:
        close = name.index("]")
        role = name[: close + 1]
        display = name[close + 1 :]
        return f"{role}{display}#{ordinal}"
    return f"{name}#{ordinal}"


def _split_turbulator(turb: Turbulator, t0: float, t1: float) -> Turbulator:
    """Carry the turbulator onto a sub-span with its position interpolated.

    The turbulator is a surface bump with no spar effect, so it simply rides the
    sub-segment; only its chordwise position (which tapers root→tip) is
    re-evaluated at the sub-span endpoints.
    """
    pos_root = turb.position_root
    pos_tip = turb.position_tip if turb.position_tip is not None else turb.position_root
    return Turbulator(
        position_root=_lerp(pos_root, pos_tip, t0),
        form=turb.form,
        height_mm=turb.height_mm,
        position_tip=_lerp(pos_root, pos_tip, t1),
        enabled=turb.enabled,
    )


def _rehome_spares(
    spares: list[Spare] | None,
    sub_y_lo: float,
    sub_y_hi: float,
    *,
    is_first: bool | None = None,
    is_last: bool = False,
) -> list[Spare]:
    """Return the existing spares whose (segment-local) origin y falls in the
    sub-span ``[sub_y_lo, sub_y_hi)``.

    No spare may ever be lost by a split (gh-1067 — data loss). A spare's local
    origin y can land slightly **below the segment root** (e.g. ``-0.6mm`` after
    a DB round-trip reconstructs a manual root spare from the dihedral geometry),
    or exactly at ``0``. Such root-side spares — the most load-critical location
    (the main joiner tube at the root) — clamp to the **first** sub-span. A spare
    at or beyond the outermost tip clamps to the **last** sub-span. A spare with
    no origin (defensive) homes to the first sub-span.

    ``is_first`` / ``is_last`` mark the root-most / tip-most sub-spans so the
    out-of-range clamps only fire once and no spare is double-counted or dropped.
    When ``is_first`` is not given it defaults to ``sub_y_lo == 0`` (the root).
    """
    if is_first is None:
        is_first = abs(sub_y_lo) <= _FRACTION_TOL  # this sub-span starts at root
    rehomed: list[Spare] = []
    for spare in spares or []:
        origin = spare.spare_origin
        y = float(origin.y) if origin is not None else 0.0
        in_span = sub_y_lo - _FRACTION_TOL <= y < sub_y_hi - _FRACTION_TOL
        on_outer = abs(y - sub_y_hi) <= _FRACTION_TOL and abs(sub_y_hi) > 0
        # Clamp a root-side (< root) spare onto the first sub-span and a
        # past-the-tip (>= outer) spare onto the last sub-span, so neither is
        # ever dropped by falling through every sub-span (gh-1067).
        below_root_to_first = is_first and y < sub_y_lo
        beyond_tip_to_last = is_last and y >= sub_y_hi
        if in_span or on_outer or below_root_to_first or beyond_tip_to_last:
            rehomed.append(spare)
    return rehomed


def split_segment_at_lengths(
    wing_config: WingConfiguration,
    segment_index: int,
    split_lengths: list[float],
    *,
    airfoil_morph_fn: AirfoilMorphFn | None = None,
    main_pieces_per_subsegment: list[list[Spare]] | None = None,
) -> WingConfiguration:
    """Like :func:`split_segment` but split positions are **mm** along the
    segment (the natural unit of a telescoping joint y) rather than fractions."""
    _ensure_segment_index(wing_config, segment_index)
    seg_len = float(wing_config.segments[segment_index].length)
    if seg_len <= 0.0:
        raise ValueError("cannot split a zero-length segment")
    fractions = [float(y) / seg_len for y in split_lengths]
    return split_segment(
        wing_config,
        segment_index,
        fractions,
        airfoil_morph_fn=airfoil_morph_fn,
        main_pieces_per_subsegment=main_pieces_per_subsegment,
    )


def split_segment(
    wing_config: WingConfiguration,
    segment_index: int,
    split_fractions: list[float],
    *,
    airfoil_morph_fn: AirfoilMorphFn | None = None,
    main_pieces_per_subsegment: list[list[Spare]] | None = None,
) -> WingConfiguration:
    """Split ``wing_config``'s segment ``segment_index`` into N contiguous
    sub-segments at ``split_fractions`` (strictly inside ``(0, 1)``, increasing).

    Returns a **new** ``WingConfiguration`` with the host segment replaced by
    ``len(split_fractions) + 1`` sub-segments whose lengths sum to the original
    and whose geometry reproduces the original ruled loft exactly. Children are
    transferred per the module docstring; the i-th sub-segment's main-spar
    pieces (``main_pieces_per_subsegment[i]``, if supplied) are placed at
    ``spar_list[0]``.

    Raises:
        IndexError: ``segment_index`` out of range.
        ValueError: invalid / non-increasing split fractions, or a sub-segment
            count mismatch with ``main_pieces_per_subsegment``.
    """
    _ensure_segment_index(wing_config, segment_index)
    _validate_fractions(split_fractions)

    n_sub = len(split_fractions) + 1
    if main_pieces_per_subsegment is not None and len(main_pieces_per_subsegment) != n_sub:
        raise ValueError(
            f"main_pieces_per_subsegment has {len(main_pieces_per_subsegment)} entries "
            f"but the split produces {n_sub} sub-segments."
        )

    host = wing_config.segments[segment_index]
    boundaries = [0.0, *split_fractions, 1.0]
    seg_len = float(host.length)

    # Build a fresh WingConfiguration by replaying every segment, substituting
    # the host with its sub-segments. The first segment is created via the
    # constructor; the rest via add_segment / add_tip_segment so the existing
    # topology re-derives each root airfoil + workplanes (read-only path).
    new_wc: WingConfiguration | None = None
    for idx, seg in enumerate(wing_config.segments):
        if idx == segment_index:
            new_wc = _emit_subsegments(
                new_wc,
                wing_config,
                seg,
                boundaries,
                seg_len,
                airfoil_morph_fn,
                main_pieces_per_subsegment,
            )
        else:
            new_wc = _emit_passthrough_segment(new_wc, wing_config, seg)

    assert new_wc is not None  # at least one segment always exists
    return new_wc


def _ensure_segment_index(wing_config: WingConfiguration, segment_index: int) -> None:
    n = len(wing_config.segments or [])
    if segment_index < 0 or segment_index >= n:
        raise IndexError(f"segment_index {segment_index} out of range (wing has {n} segment(s))")


def _clone_airfoil(af: Airfoil) -> Airfoil:
    return Airfoil(
        airfoil=af.airfoil,
        chord=af.chord,
        dihedral_as_rotation_in_degrees=af.dihedral_as_rotation_in_degrees,
        incidence=af.incidence,
    )


def _emit_passthrough_segment(
    new_wc: WingConfiguration | None,
    src_wc: WingConfiguration,
    seg: WingSegment,
) -> WingConfiguration:
    """Append an unchanged copy of ``seg`` to the new wing configuration."""
    if new_wc is None:
        return WingConfiguration(
            nose_pnt=src_wc.nose_pnt,
            root_airfoil=_clone_airfoil(seg.root_airfoil),
            length=seg.length,
            sweep=seg.sweep,
            sweep_is_angle=False,
            tip_airfoil=_clone_airfoil(seg.tip_airfoil),
            number_interpolation_points=seg.number_interpolation_points,
            spare_list=list(seg.spare_list) if seg.spare_list else None,
            trailing_edge_device=seg.trailing_edge_device,
            turbulator=seg.turbulator,
            symmetric=src_wc.symmetric,
            parameters=src_wc.parameters,
        )
    if seg.wing_segment_type == "tip":
        new_wc.add_tip_segment(
            tip_type=seg.tip_type,
            length=seg.length,
            sweep=seg.sweep,
            tip_airfoil=_clone_airfoil(seg.tip_airfoil),
            number_interpolation_points=seg.number_interpolation_points,
        )
    else:
        new_wc.add_segment(
            length=seg.length,
            sweep=seg.sweep,
            sweep_is_angle=False,
            tip_airfoil=_clone_airfoil(seg.tip_airfoil),
            number_interpolation_points=seg.number_interpolation_points,
            spare_list=list(seg.spare_list) if seg.spare_list else None,
            trailing_edge_device=seg.trailing_edge_device,
            turbulator=seg.turbulator,
        )
    return new_wc


def _emit_subsegments(
    new_wc: WingConfiguration | None,
    src_wc: WingConfiguration,
    host: WingSegment,
    boundaries: list[float],
    seg_len: float,
    airfoil_morph_fn: AirfoilMorphFn | None,
    main_pieces_per_subsegment: list[list[Spare]] | None,
) -> WingConfiguration:
    """Replace ``host`` with its contiguous sub-segments in the new wing."""
    root_af = host.root_airfoil
    tip_af = host.tip_airfoil
    # Total relative deltas the host carries from its root to its tip.
    d_incidence = tip_af.incidence
    d_dihedral = tip_af.dihedral_as_rotation_in_degrees

    # gh-1068: cumulative twist (R_y) at each split boundary that keeps the
    # *built ruled loft unchanged* even when the host is tapered. See
    # :func:`_boundary_twist_cumulative` for the why (a plain linear twist split
    # drifts the section center_z by ~0.7mm on a washout+taper wing).
    # The loft rotates each wire by the *cumulative* twist (theta_accum): the
    # host root wire by ``root_af.incidence`` and the host tip wire by
    # ``root_af.incidence + tip_af.incidence``. The chord-weighting below needs
    # those absolute cumulative angles; the inboard-chain offset cancels in the
    # per-sub-segment deltas.
    twist_cum = _boundary_twist_cumulative(
        boundaries,
        root_af.incidence,
        root_af.incidence + tip_af.incidence,
        root_af.chord,
        tip_af.chord,
    )

    n_sub = len(boundaries) - 1
    for i in range(n_sub):
        t0, t1 = boundaries[i], boundaries[i + 1]
        sub_length = (t1 - t0) * seg_len

        # Boundary airfoil at t1 (outer end of this sub-segment). Chord + file
        # come from the ruled blend. The LAST sub-segment's tip is the host's
        # original tip airfoil — no interpolation/morph there.
        if i == n_sub - 1:
            outer_af = _clone_airfoil(tip_af)
        else:
            outer_af = _interp_airfoil(root_af, tip_af, t1, airfoil_morph_fn)

        # Incidence (twist about the chord axis) does not move the spanwise
        # position, but for a *tapered* host the section's world-z is driven by
        # ``chord · sin(twist)``, which is nonlinear in the span fraction. The
        # per-sub-segment incidence delta is therefore the difference of the
        # chord-weighted cumulative twist at the two boundaries (not a plain
        # linear split), so the inserted intermediate wire reproduces the
        # original ruled blend of the two end wires (gh-1068).
        outer_af.incidence = twist_cum[i + 1] - twist_cum[i]

        # Dihedral rotates the spanwise translation about x. Splitting it
        # linearly would bend the intermediate station origins OFF the original
        # straight ruled line (a 1°/100mm-class geometry change). Instead carry
        # the FULL dihedral delta on the last sub-segment's tip and ZERO on the
        # intermediate boundaries: every intermediate origin stays on the
        # original straight line, and the final tip wire gets the original tilt
        # — reproducing the ruled loft exactly.
        outer_af.dihedral_as_rotation_in_degrees = d_dihedral if i == n_sub - 1 else 0.0

        sub_sweep = host.sweep * (t1 - t0)

        # Children for this sub-span.
        sub_ted = (
            _split_ted(host.trailing_edge_device, t0, t1, i)
            if host.trailing_edge_device is not None
            else None
        )
        sub_turb = (
            _split_turbulator(host.turbulator, t0, t1) if host.turbulator is not None else None
        )
        rehomed = _rehome_spares(
            host.spare_list,
            t0 * seg_len,
            t1 * seg_len,
            is_first=(i == 0),
            is_last=(i == n_sub - 1),
        )
        sub_spares = _assemble_spare_list(
            main_pieces_per_subsegment[i] if main_pieces_per_subsegment else None,
            rehomed,
        )

        if new_wc is None:
            # First sub-segment of a wing whose host is the root segment.
            first_root = _clone_airfoil(root_af)
            new_wc = WingConfiguration(
                nose_pnt=src_wc.nose_pnt,
                root_airfoil=first_root,
                length=sub_length,
                sweep=sub_sweep,
                sweep_is_angle=False,
                tip_airfoil=outer_af,
                number_interpolation_points=host.number_interpolation_points,
                spare_list=sub_spares,
                trailing_edge_device=sub_ted,
                turbulator=sub_turb,
                symmetric=src_wc.symmetric,
                parameters=src_wc.parameters,
            )
        else:
            new_wc.add_segment(
                length=sub_length,
                sweep=sub_sweep,
                sweep_is_angle=False,
                tip_airfoil=outer_af,
                number_interpolation_points=host.number_interpolation_points,
                spare_list=sub_spares,
                trailing_edge_device=sub_ted,
                turbulator=sub_turb,
            )
    return new_wc


def _assemble_spare_list(
    main_pieces: list[Spare] | None, rehomed: list[Spare]
) -> list[Spare] | None:
    """Build a sub-segment's spare_list with the main piece(s) at index 0.

    The main-spar piece(s) for this sub-segment come first (``spar_list[0]`` =
    main spar — the VaseMode invariant), then any re-homed existing spares.
    """
    combined: list[Spare] = []
    if main_pieces:
        combined.extend(main_pieces)
    combined.extend(rehomed)
    return combined or None
