"""In-process VLM strip-force producer (gh-674).

Reconstructs AVL-equivalent per-strip spanwise force distributions from an
AeroSandbox ``VortexLatticeMethod`` solve, so the Trefftz-Plane chart works
without spawning an AVL subprocess. AeroSandbox runs the same Trefftz-plane
induced-drag core in-process, an order of magnitude faster than the AVL
file-I/O round trip.

The returned dict mirrors the keys the AVL path produces
(``Sref``/``Cref``/``Bref``/``alpha``/``beta``/``mach``/``strip_forces``),
so ``analysis_service`` can feed it through the existing
``StripForcesResponse`` builder unchanged.

Panel→strip→surface reconstruction relies only on public, version-stable VLM
geometry (``is_trailing_edge`` marks the last panel of each chordwise strip;
panels are emitted chordwise-fastest, strips spanwise, wings in
``airplane.wings`` order), not on AeroSandbox internals.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np


def _strip_index_ranges(is_trailing_edge: np.ndarray) -> list[tuple[int, int]]:
    """Return [start, end) panel index ranges, one per chordwise strip.

    A strip ends at each panel flagged ``is_trailing_edge``; panels are
    ordered chordwise-fastest, so consecutive panels up to and including a
    trailing-edge panel form one strip.
    """
    ranges: list[tuple[int, int]] = []
    start = 0
    for i, te in enumerate(is_trailing_edge):
        if te:
            ranges.append((start, i + 1))
            start = i + 1
    return ranges


def _wing_strip_counts(airplane, spanwise_resolution: int) -> list[int]:
    """Expected number of spanwise strips contributed by each wing.

    Each wing segment (between two cross-sections) is split into
    ``spanwise_resolution`` strips; a symmetric wing contributes both halves.
    """
    counts = []
    for wing in airplane.wings:
        segments = max(len(wing.xsecs) - 1, 0)
        n = segments * spanwise_resolution * (2 if wing.symmetric else 1)
        counts.append(n)
    return counts


# gh-855: target spanwise panels per half-wing, distributed ∝ segment span.
_SPANWISE_PANELS_PER_HALF = 40
_MIN_PANELS_PER_SEGMENT = 2


def _panels_per_segment(spans: list[float], budget: int, min_per_segment: int) -> list[int]:
    """Distribute ``budget`` spanwise panels across segments ∝ span (gh-855).

    Each segment gets at least ``min_per_segment`` panels so a tiny segment is
    never over-resolved relative to a large one. Pure function (no aerosandbox).
    """
    if not spans:
        return []
    total = float(sum(spans))
    if total <= 0:
        return [max(min_per_segment, 1) for _ in spans]
    return [max(min_per_segment, int(round(budget * s / total))) for s in spans]


def _segment_spans(wing) -> list[float]:
    """True (dihedral-inclusive) spanwise length of each wing segment [m]."""
    xs = wing.xsecs
    spans: list[float] = []
    for xa, xb in zip(xs[:-1], xs[1:], strict=False):
        a = np.asarray(xa.xyz_le, dtype=float)
        b = np.asarray(xb.xyz_le, dtype=float)
        spans.append(float(math.hypot(b[1] - a[1], b[2] - a[2])))
    return spans


def _blend_xsec(xa, xb, frac: float):
    """Interpolate a ``WingXSec`` between ``xa`` (frac 0) and ``xb`` (frac 1).

    chord/twist/xyz_le are linear; the airfoil is blended via
    ``Airfoil.blend_with_another_airfoil`` — the same call AeroSandbox uses
    internally when subdividing sections (gh-855).
    """
    import aerosandbox as asb

    a, b = 1.0 - frac, frac
    name_a = getattr(xa.airfoil, "name", "") or ""
    name_b = getattr(xb.airfoil, "name", "") or ""
    if frac <= 0.0 or name_a == name_b:
        airfoil = xa.airfoil
    elif frac >= 1.0:
        airfoil = xb.airfoil
    else:
        try:
            airfoil = xa.airfoil.blend_with_another_airfoil(airfoil=xb.airfoil, blend_fraction=b)
        except Exception:  # noqa: BLE001 — blend failure → keep inboard section
            airfoil = xa.airfoil
    return asb.WingXSec(
        xyz_le=np.asarray(xa.xyz_le, dtype=float) * a + np.asarray(xb.xyz_le, dtype=float) * b,
        chord=float(xa.chord) * a + float(xb.chord) * b,
        twist=float(xa.twist) * a + float(xb.twist) * b,
        airfoil=airfoil,
        control_surfaces=xa.control_surfaces,
    )


def remesh_uniform_density(wing, *, budget: int, min_per_segment: int):
    """Return a copy of ``wing`` with span-proportional spanwise subdivision.

    Inserts intermediate cross-sections so the wing carries ~``budget`` panels
    per half, distributed ∝ segment span (≥ ``min_per_segment`` each). Run the
    VLM with ``spanwise_resolution=1`` on the result so each inserted section is
    exactly one spanwise panel → uniform panel density (gh-855).
    """
    import aerosandbox as asb

    xs = wing.xsecs
    if len(xs) < 2:
        return wing
    counts = _panels_per_segment(_segment_spans(wing), budget, min_per_segment)
    new_xsecs = []
    for (xa, xb), n in zip(zip(xs[:-1], xs[1:], strict=False), counts, strict=False):
        for i in range(n):
            new_xsecs.append(_blend_xsec(xa, xb, i / n))
    new_xsecs.append(xs[-1])
    return asb.Wing(name=wing.name, xsecs=new_xsecs, symmetric=wing.symmetric)


def _remesh_airplane(asb_airplane, *, budget: int, min_per_segment: int):
    """Rebuild the airplane with uniform-density wings, preserving the (gh-788)
    reference geometry."""
    import aerosandbox as asb

    remeshed = [
        remesh_uniform_density(w, budget=budget, min_per_segment=min_per_segment)
        for w in asb_airplane.wings
    ]
    return asb.Airplane(
        name=asb_airplane.name,
        wings=remeshed,
        fuselages=list(getattr(asb_airplane, "fuselages", []) or []),
        xyz_ref=asb_airplane.xyz_ref,
        s_ref=float(asb_airplane.s_ref),
        b_ref=float(asb_airplane.b_ref),
        c_ref=float(asb_airplane.c_ref),
    )


def compute_vlm_strip_forces(
    asb_airplane,
    op_point,
    *,
    xyz_ref: list[float] | None = None,
    spanwise_panels: int = _SPANWISE_PANELS_PER_HALF,
    chordwise_resolution: int = 8,
    min_panels_per_segment: int = _MIN_PANELS_PER_SEGMENT,
) -> dict[str, Any]:
    """Run a VLM solve and return AVL-compatible per-strip force data.

    Spanwise panels are distributed **∝ segment span** (gh-855): the wing is
    remeshed so panel density is ~uniform (``spanwise_panels`` per half,
    ≥ ``min_panels_per_segment`` per segment), then the VLM runs with
    ``spanwise_resolution=1``. This avoids over-resolving tiny segments — the
    old per-segment ``spanwise_resolution`` gave a 5 cm segment as many strips
    as a 95 cm one, spiking the cl(y) plot.

    Args:
        asb_airplane: the ``asb.Airplane`` to analyse.
        op_point: the ``asb.OperatingPoint``.
        xyz_ref: moment reference point; defaults to the airplane's own.
        spanwise_panels: target spanwise panels per half-wing.
        chordwise_resolution: VLM chordwise panels per strip.
        min_panels_per_segment: floor on panels for any single segment.

    Returns:
        A dict with ``Sref``/``Cref``/``Bref``/``alpha``/``beta``/``mach``/
        ``CL``/``CD`` and a ``strip_forces`` list of per-surface dicts whose
        ``strips`` entries validate into ``StripForceEntry``.
    """
    import aerosandbox as asb

    if xyz_ref is not None:
        asb_airplane.xyz_ref = xyz_ref

    meshed = _remesh_airplane(
        asb_airplane, budget=spanwise_panels, min_per_segment=min_panels_per_segment
    )

    vlm = asb.VortexLatticeMethod(
        airplane=meshed,
        op_point=op_point,
        spanwise_resolution=1,  # gh-855: density set by the remesh, not here
        chordwise_resolution=chordwise_resolution,
        spanwise_spacing_function=np.linspace,
    )
    run = vlm.run()

    q = float(op_point.dynamic_pressure())
    s_ref = float(asb_airplane.s_ref)
    c_ref = float(asb_airplane.c_ref)
    b_ref = float(asb_airplane.b_ref)

    forces = np.asarray(vlm.forces_geometry, dtype=float)  # (N, 3) geometry axes
    areas = np.asarray(vlm.areas, dtype=float)
    fl = np.asarray(vlm.front_left_vertices, dtype=float)
    fr = np.asarray(vlm.front_right_vertices, dtype=float)
    bl = np.asarray(vlm.back_left_vertices, dtype=float)
    br = np.asarray(vlm.back_right_vertices, dtype=float)

    # Drag along the freestream; lift perpendicular to it in the x–z plane.
    d_hat = np.asarray(vlm.steady_freestream_direction, dtype=float)
    d_hat = d_hat / np.linalg.norm(d_hat)
    l_hat = np.array([-d_hat[2], 0.0, d_hat[0]])
    l_hat = l_hat / np.linalg.norm(l_hat)

    strip_ranges = _strip_index_ranges(np.asarray(vlm.is_trailing_edge))
    # spanwise_resolution=1 → one strip per (remeshed) segment per half.
    wing_counts = _wing_strip_counts(meshed, 1)

    # Assign contiguous blocks of strips to wings in airplane.wings order.
    # If the expected counts don't sum to the actual strip count (unusual
    # paneling), fall back to a single aggregate surface so we never crash.
    if sum(wing_counts) != len(strip_ranges):
        wing_counts = [len(strip_ranges)]
        wing_names = [asb_airplane.name or "Aircraft"]
    else:
        wing_names = [w.name for w in meshed.wings]

    surfaces: list[dict[str, Any]] = []
    cursor = 0
    total_lift = 0.0
    total_drag = 0.0
    for surface_number, (name, count) in enumerate(zip(wing_names, wing_counts, strict=False)):
        if count == 0:
            continue
        my_ranges = strip_ranges[cursor : cursor + count]
        cursor += count
        strips: list[dict[str, Any]] = []
        surface_area = 0.0
        for j, (lo, hi) in enumerate(my_ranges, start=1):
            sl = slice(lo, hi)
            f_strip = forces[sl].sum(axis=0)
            area = float(areas[sl].sum())
            le = 0.5 * (fl[lo] + fr[lo])  # leading edge of the strip
            te_pt = 0.5 * (bl[hi - 1] + br[hi - 1])  # trailing edge of the strip
            chord = float(abs(te_pt[0] - le[0]))

            lift = float(np.dot(f_strip, l_hat))
            drag = float(np.dot(f_strip, d_hat))
            total_lift += lift
            total_drag += drag
            surface_area += area

            denom = q * area
            cl = lift / denom if denom > 0 else 0.0
            cd = drag / denom if denom > 0 else 0.0
            # Induced angle: D_i = L · α_i for small angles → α_i = atan(cd/cl).
            # atan2 is well-defined for all inputs (atan2(0, 0) == 0), so no
            # float-equality guard is needed.
            ai_deg = math.degrees(math.atan2(drag, lift))
            cl_norm = cl * chord / c_ref if c_ref > 0 else 0.0

            strips.append(
                {
                    "j": j,
                    "Xle": float(le[0]),
                    "Yle": float(le[1]),
                    "Zle": float(le[2]),
                    "Chord": chord,
                    "Area": area,
                    "c_cl": chord * cl,
                    "ai": ai_deg,
                    "cl_norm": cl_norm,
                    "cl": cl,
                    "cd": cd,
                    # VLM is inviscid: no viscous drag, and chordwise pressure
                    # for c/4-moment / centre-of-pressure isn't resolved here.
                    "cdv": 0.0,
                    "cm_c/4": 0.0,
                    "cm_LE": 0.0,
                    "C.P.x/c": 0.25,
                }
            )
        surfaces.append(
            {
                "surface_name": name,
                "surface_number": surface_number,
                "n_chordwise": chordwise_resolution,
                "n_spanwise": len(strips),
                "surface_area": surface_area,
                "strips": strips,
            }
        )

    return {
        "Sref": s_ref,
        "Cref": c_ref,
        "Bref": b_ref,
        "alpha": float(op_point.alpha),
        "beta": float(op_point.beta),
        "mach": float(op_point.mach()),
        "CL": float(run["CL"]),
        "CD": float(run["CD"]),
        "strip_forces": surfaces,
    }
