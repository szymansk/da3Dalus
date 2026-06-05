"""OpenVSP airfoil-import helper (gh-642).

Per-section airfoil extraction for the OpenVSP importer (gh-637).
The WING handler (#641) calls :func:`import_airfoil_from_xsec` once
per ``WingXSecSchema`` to resolve the ``airfoil`` field — either a
NACA name string (NACA 4-/5-/6-/16-series) or a path to a Selig
``.dat`` file the handler wrote on the fly.

Scope (per ``feedback_openvsp_import_rc_scope``)
-----------------------------------------------

* In scope: NACA 4-series, 4-digit-modified, 5-series, 5-digit-mod,
  6-series, 16-series, biconvex / wedge (basic-thick), file-airfoil
  (Selig export), CST-fallback (file export + warning).
* Out of scope: native CST/Kulfan reconstruction (#651, closed),
  VKT airfoils, Bezier-export.
"""

from __future__ import annotations

import hashlib
import math
import os
import tempfile
from pathlib import Path
from types import ModuleType
from typing import Optional

from app.converters.openvsp_importer import ImportContext


# Resolves at import time. Tests monkeypatch this to a tmp directory.
AIRFOILS_DIR: Path = Path("components") / "airfoils"

# Cosine-spaced default resolution for generated NACA .dat files.
# Matches the density of the hand-curated files in components/airfoils.
_NACA_DAT_HALF_POINTS = 80


# ---------------------------------------------------------------------------
# NACA name synthesis
# ---------------------------------------------------------------------------


def naca_4series_name(*, camber: float, camber_loc: float, thick_chord: float) -> str:
    """Build the canonical NACA 4-series name (e.g. "naca2412").

    camber (max camber as chord fraction; 0.02 → "2")
    camber_loc (position of max camber as chord fraction; 0.4 → "4")
    thick_chord (thickness as chord fraction; 0.12 → "12")
    """
    m = round(camber * 100)
    p = round(camber_loc * 10)
    t = round(thick_chord * 100)
    return f"naca{m:d}{p:d}{t:02d}"


def naca_5series_name(
    *, camber: float, camber_loc: float, reflex: float, thick_chord: float
) -> str:
    """Build the canonical NACA 5-series name (e.g. "naca23012").

    5-series naming is "LPSTT":
      L = design Cl × 3/2 × 10 (1 digit; for Cl=0.3 → "2")
      P = camber-position fraction × 20 (1 digit; for x=0.15 → "3")
      S = 0 (standard) or 1 (reflex)
      TT = thickness × 100 (2 digits)

    OpenVSP stores "Camber" as the design Cl scaled by 3/2 (so
    Camber=0.30 represents Cl=0.45 × 2/3 = 0.30 → L=2 directly).
    """
    L = max(1, min(9, round(camber * 20 / 3)))
    P = max(0, min(9, round(camber_loc * 20)))
    S = 1 if reflex >= 0.5 else 0
    TT = max(0, min(99, round(thick_chord * 100)))
    return f"naca{L:d}{P:d}{S:d}{TT:02d}"


def naca_6series_name(*, series: int, ideal_cl: float, thick_chord: float, a: float) -> str:
    """Build a NACA 6-series name (e.g. "naca65-410-a0.5")."""
    cl_digit = max(0, min(9, round(ideal_cl * 10)))
    t = round(thick_chord * 100)
    return f"naca{int(series):d}-{cl_digit:d}{t:02d}-a{a:.1f}"


def naca_16series_name(*, design_cl: float, thick_chord: float) -> str:
    """Build a NACA 16-series name (e.g. "naca16-412" for Cl_i=0.4, t/c=0.12).

    The 16-series nomenclature is ``naca16-CTT`` where:
      C  = design lift coefficient × 10  (one digit; Cl=0.4 → "4")
      TT = thickness as a chord fraction × 100 (two digits; t/c=0.12 → "12")
    """
    cl_digit = max(0, min(9, round(design_cl * 10)))
    t = round(thick_chord * 100)
    return f"naca16-{cl_digit:d}{t:02d}"


# ---------------------------------------------------------------------------
# NACA 4-digit .dat generation (gh-700)
# ---------------------------------------------------------------------------


def _naca4_thickness_offset(x: float, thickness: float) -> float:
    """Standard NACA 4-digit half-thickness distribution.

    Uses the open-TE coefficient (-0.1015) consistent with Selig data;
    callers that need a closed TE can chop the last point or use
    -0.1036 instead.
    """
    return (
        5
        * thickness
        * (
            0.2969 * math.sqrt(max(x, 0.0))
            - 0.1260 * x
            - 0.3516 * x * x
            + 0.2843 * x * x * x
            - 0.1015 * x * x * x * x
        )
    )


def _naca4_camber_line(x: float, camber: float, camber_loc: float) -> tuple[float, float]:
    """Returns ``(y_camber, dy/dx)`` for the NACA 4-digit camber line.

    Symmetric airfoils (camber == 0) and the degenerate case
    camber_loc == 0 both produce ``(0.0, 0.0)``. The piecewise quadratic
    matches the canonical NACA definition.
    """
    if camber == 0 or camber_loc == 0:
        return 0.0, 0.0
    if x <= camber_loc:
        yc = (camber / (camber_loc**2)) * (2 * camber_loc * x - x * x)
        dyc = (2 * camber / (camber_loc**2)) * (camber_loc - x)
    else:
        denom = (1 - camber_loc) ** 2
        yc = (camber / denom) * ((1 - 2 * camber_loc) + 2 * camber_loc * x - x * x)
        dyc = (2 * camber / denom) * (camber_loc - x)
    return yc, dyc


def naca4_coordinates(
    *,
    camber: float,
    camber_loc: float,
    thick_chord: float,
    n_half: int = _NACA_DAT_HALF_POINTS,
) -> list[tuple[float, float]]:
    """Generate Selig-format coordinates for a NACA 4-digit airfoil.

    Returns ``n_half * 2 + 1`` points (cosine-spaced over each surface,
    sharing the LE point). Order: TE → upper → LE → lower → TE — the
    Selig convention all existing files in ``components/airfoils`` use.
    """
    upper: list[tuple[float, float]] = []
    lower: list[tuple[float, float]] = []
    for i in range(n_half + 1):
        beta = math.pi * i / n_half
        x = 0.5 * (1.0 - math.cos(beta))
        yt = _naca4_thickness_offset(x, thick_chord)
        yc, dyc = _naca4_camber_line(x, camber, camber_loc)
        theta = math.atan(dyc)
        sin_t = math.sin(theta)
        cos_t = math.cos(theta)
        upper.append((x - yt * sin_t, yc + yt * cos_t))
        lower.append((x + yt * sin_t, yc - yt * cos_t))
    # Selig: TE → upper-surface → LE → lower-surface → TE.
    # Reverse upper so we walk from TE to LE; share the LE point.
    return list(reversed(upper)) + lower[1:]


def ensure_naca4_dat(
    *,
    name: str,
    camber: float,
    camber_loc: float,
    thick_chord: float,
    airfoils_dir: Path | None = None,
) -> Path:
    """Write ``{airfoils_dir}/{name}.dat`` if it doesn't already exist.

    Idempotent: returns the path either way. Never raises — on write
    failure (e.g. read-only fs) it logs nothing and returns the path
    the caller should record; the downstream renderer will degrade
    gracefully when the file is missing.
    """
    target_dir = airfoils_dir if airfoils_dir is not None else AIRFOILS_DIR
    target = target_dir / f"{name}.dat"
    if target.exists():
        return target
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        coords = naca4_coordinates(camber=camber, camber_loc=camber_loc, thick_chord=thick_chord)
        # Header: airfoil name on its own line (XFOIL / Selig convention).
        header = name.upper().replace("NACA", "NACA ") if name.lower().startswith("naca") else name
        lines = [header.strip()]
        for x, y in coords:
            lines.append(f"{x:.6f}  {y:.6f}")
        target.write_text("\n".join(lines) + "\n")
    except OSError:
        # Read-only fs / permission error — don't crash the import.
        pass
    return target


# ---------------------------------------------------------------------------
# NACA 5-digit .dat generation (gh-733)
# ---------------------------------------------------------------------------
#
# 5-digit mean-line constants from Abbott & von Doenhoff, "Theory of
# Wing Sections" Appendix III, Tables 1–2 (originally NACA Reports 537
# & 824). Each row is keyed by the camber-position digit P (the 2nd
# digit of the 5-code), which represents the chord-fraction position
# of max camber as P × 0.05 — i.e. P=3 → x_m=0.15, P=4 → x_m=0.20.
# Standard (S=0) and reflex (S=1) families use different camber-line
# polynomials with different (m, k1) constants; reflex additionally
# carries a k2/k1 ratio for the aft segment. Tables apply at design
# C_l = 0.3; for other design C_l, k1 scales linearly (see
# ``_scale_k1``).

# (m, k1) keyed by camber-position digit P, for standard 5-digit.
_NACA5_STANDARD: dict[int, tuple[float, float]] = {
    1: (0.0580, 361.4),
    2: (0.1260, 51.64),
    3: (0.2025, 15.957),
    4: (0.2900, 6.643),
    5: (0.3910, 3.230),
}

# (m, k1, k2_over_k1) keyed by P, for reflex 5-digit (S=1, e.g. naca23112).
_NACA5_REFLEX: dict[int, tuple[float, float, float]] = {
    2: (0.1300, 51.99, 0.000764),
    3: (0.2170, 15.793, 0.00677),
    4: (0.3180, 6.520, 0.0303),
    5: (0.4410, 3.191, 0.1355),
}

# Reference design Cl that the (m, k1) tables are tabulated for.
_NACA5_REFERENCE_CL: float = 0.3


def _scale_k1(k1_table: float, design_cl: float) -> float:
    """Scale tabulated ``k1`` for a non-0.3 design C_l.

    k1 enters the camber line linearly, so the camber amplitude scales
    linearly with design C_l. Standard NACA 5-digit profiles (L=2)
    are tabulated at design C_l = 0.3; the L digit "L" is the
    nomenclature shorthand ``L = design_cl × 20/3``, so
    L=2 → design_cl=0.3 → factor=1.0.
    """
    return k1_table * (design_cl / _NACA5_REFERENCE_CL)


def _naca5_camber_line_standard(x: float, m: float, k1: float) -> tuple[float, float]:
    """Standard NACA 5-digit camber line — ``(y_camber, dy/dx)``.

    Cubic forward of ``x=m``, linear (-k1·m³/6 slope) aft. Reference:
    Abbott & von Doenhoff Theory of Wing Sections (eq. 4.13).
    """
    if x <= m:
        yc = (k1 / 6.0) * (x**3 - 3 * m * x * x + m * m * (3 - m) * x)
        dyc = (k1 / 6.0) * (3 * x * x - 6 * m * x + m * m * (3 - m))
    else:
        yc = (k1 * m**3 / 6.0) * (1.0 - x)
        dyc = -(k1 * m**3) / 6.0
    return yc, dyc


def _naca5_camber_line_reflex(
    x: float, m: float, k1: float, k2_over_k1: float
) -> tuple[float, float]:
    """Reflex NACA 5-digit camber line — ``(y_camber, dy/dx)``.

    Both forward and aft segments are cubics; the aft segment has
    its leading term scaled by ``k2/k1`` so the trailing edge curls
    back up ("reflex"). Reference: NACA Report 537 §3.
    """
    if x <= m:
        forward_cubic = (x - m) ** 3
    else:
        forward_cubic = k2_over_k1 * (x - m) ** 3
    common = k2_over_k1 * (1 - m) ** 3 * x + m**3 * x - m**3
    yc = (k1 / 6.0) * (forward_cubic - common)
    if x <= m:
        d_forward = 3.0 * (x - m) ** 2
    else:
        d_forward = 3.0 * k2_over_k1 * (x - m) ** 2
    d_common = k2_over_k1 * (1 - m) ** 3 + m**3
    dyc = (k1 / 6.0) * (d_forward - d_common)
    return yc, dyc


def naca5_coordinates(
    *,
    design_cl: float,
    camber_loc_digit: int,
    reflex: bool,
    thick_chord: float,
    n_half: int = _NACA_DAT_HALF_POINTS,
) -> list[tuple[float, float]]:
    """Generate Selig-format coordinates for a NACA 5-digit airfoil.

    Identical resolution + ordering convention as
    :func:`naca4_coordinates` (TE → upper → LE → lower → TE,
    cosine-spaced, ``2·n_half + 1`` points). Reuses the 4-digit
    thickness polynomial — both series share it.

    Raises ``ValueError`` if the camber-position digit isn't in the
    tabulated set ({1..5} for standard, {2..5} for reflex). The caller
    is expected to fall back to a curated default in that case.
    """
    if reflex:
        table_r = _NACA5_REFLEX.get(camber_loc_digit)
        if table_r is None:
            raise ValueError(
                f"NACA 5-digit reflex: no tabulated constants for "
                f"camber-position digit P={camber_loc_digit} "
                f"(valid: 2..5)"
            )
        m, k1_ref, k2_over_k1 = table_r
    else:
        table_s = _NACA5_STANDARD.get(camber_loc_digit)
        if table_s is None:
            raise ValueError(
                f"NACA 5-digit standard: no tabulated constants for "
                f"camber-position digit P={camber_loc_digit} "
                f"(valid: 1..5)"
            )
        m, k1_ref = table_s
        k2_over_k1 = 0.0  # unused on the standard path

    k1 = _scale_k1(k1_ref, design_cl)

    upper: list[tuple[float, float]] = []
    lower: list[tuple[float, float]] = []
    for i in range(n_half + 1):
        beta = math.pi * i / n_half
        x = 0.5 * (1.0 - math.cos(beta))
        yt = _naca4_thickness_offset(x, thick_chord)
        if reflex:
            yc, dyc = _naca5_camber_line_reflex(x, m, k1, k2_over_k1)
        else:
            yc, dyc = _naca5_camber_line_standard(x, m, k1)
        theta = math.atan(dyc)
        sin_t = math.sin(theta)
        cos_t = math.cos(theta)
        upper.append((x - yt * sin_t, yc + yt * cos_t))
        lower.append((x + yt * sin_t, yc - yt * cos_t))
    return list(reversed(upper)) + lower[1:]


def ensure_naca5_dat(
    *,
    name: str,
    camber: float,
    camber_loc: float,
    reflex: float,
    thick_chord: float,
    airfoils_dir: Path | None = None,
    ctx: Optional["ImportContext"] = None,
    component_name: str = "",
) -> Path:
    """Write ``{airfoils_dir}/{name}.dat`` for a NACA 5-digit airfoil.

    Idempotent (skips when the file already exists). When the
    OpenVSP-supplied camber-position is out of the tabulated range
    (P ∉ {1..5} standard, {2..5} reflex), the function emits an
    import warning via ``ctx`` (when provided) and returns the path
    that would have been written without writing anything — the
    schema's ``airfoil`` reference becomes dangling, which the
    downstream renderer falls back on a curved default.

    Parameters
    ----------
    name
        Canonical 5-digit name from :func:`naca_5series_name`
        (e.g. ``"naca23012"``).
    camber
        OpenVSP "Camber" parm — the design lift coefficient (0.3 for
        the canonical L=2 leading digit).
    camber_loc
        OpenVSP "CamberLoc" parm — chord-fraction position of max
        camber (0.15 for the canonical P=3 second digit).
    reflex
        OpenVSP "Reflex" parm — 0.0 (standard) or 1.0 (reflex).
    thick_chord
        Thickness-to-chord ratio (0.12 for the canonical TT=12).
    """
    target_dir = airfoils_dir if airfoils_dir is not None else AIRFOILS_DIR
    target = target_dir / f"{name}.dat"
    if target.exists():
        return target

    # Recover the P digit from CamberLoc (P × 0.05 = camber_loc).
    p_digit = max(0, min(9, round(camber_loc * 20)))
    is_reflex = reflex >= 0.5

    try:
        coords = naca5_coordinates(
            design_cl=camber,
            camber_loc_digit=p_digit,
            reflex=is_reflex,
            thick_chord=thick_chord,
        )
    except ValueError as exc:
        if ctx is not None:
            ctx.add_warning(
                component_type="WING_XSEC",
                component_name=component_name or name,
                reason=str(exc),
                severity="warning",
            )
        return target

    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        header = name.upper().replace("NACA", "NACA ") if name.lower().startswith("naca") else name
        lines = [header.strip()]
        for x, y in coords:
            lines.append(f"{x:.6f}  {y:.6f}")
        target.write_text("\n".join(lines) + "\n")
    except OSError:
        pass
    return target


# ---------------------------------------------------------------------------
# NACA "a"-family mean line (gh-733 Phase 2)
# ---------------------------------------------------------------------------
#
# Single-parameter mean-line shape per NACA Report 824 / Abbott &
# von Doenhoff §4.5. Lift is distributed uniformly over 0 ≤ x ≤ a
# then drops linearly to zero at x=1. a=1.0 is full-chord uniform
# load (6-series default), a=0.0 is triangular pressure.
#
# Closed form (Abbott eq. 4.26), valid 0 ≤ a < 1:
#
#   y_c/c_li = 1/(2π(a+1)) · {
#        (1/(1-a)) · [ ½(a-x)²ln|a-x| - ½(1-x)²ln(1-x)
#                      + ¼(1-x)² - ¼(a-x)² ]
#        - x·ln(x) + g - h·x
#   }
#
# Constants depend only on a:
#   g = -1/(1-a) · [ a²·(½ln(a) - ¼) + ¼ ]
#   h =  1/(1-a) · [ ½(1-a)²ln(1-a) - ¼(1-a)² ] + g
#
# Singular limit a → 1 (uniform full-chord load):
#   y_c/c_li = -1/(4π) · [ (1-x)·ln(1-x) + x·ln(x) ]


def _naca_a_family_g(a: float) -> float:
    """Constant ``g`` in Abbott eq. 4.26 — depends only on ``a``."""
    if abs(1.0 - a) < 1e-9:
        return 0.0  # singular branch handles a=1 separately
    if a <= 0.0:
        # Limit a→0: a²·ln(a) → 0, so g = -¼.
        return -0.25
    return -(1.0 / (1.0 - a)) * (a * a * (0.5 * math.log(a) - 0.25) + 0.25)


def _naca_a_family_h(a: float) -> float:
    """Constant ``h`` in Abbott eq. 4.26 — depends only on ``a``."""
    if abs(1.0 - a) < 1e-9:
        return 0.0
    g = _naca_a_family_g(a)
    return (1.0 / (1.0 - a)) * (
        0.5 * (1.0 - a) ** 2 * math.log(1.0 - a) - 0.25 * (1.0 - a) ** 2
    ) + g


def _xlnx(x: float) -> float:
    """``x·ln(x)`` with the analytic limit 0 at x=0."""
    if x <= 0.0:
        return 0.0
    return x * math.log(x)


def naca_a_family_camber_at(x: float, a: float, design_cl: float) -> float:
    """``y_c(x)`` for the NACA "a"-family at design lift coefficient
    ``design_cl``. Returns the camber-line y-coordinate at chord
    fraction ``x``.

    Slope is computed numerically by the caller via central
    differences — the closed-form derivative carries additional
    log-singularities at x=a and x=1 that don't add accuracy over
    a small-h finite difference.
    """
    if x <= 0.0 or x >= 1.0:
        return 0.0  # LE and TE: y_c = 0 by construction.

    if abs(1.0 - a) < 1e-9:
        # Uniform-load limit (a=1).
        return -(design_cl / (4.0 * math.pi)) * ((1.0 - x) * math.log(1.0 - x) + x * math.log(x))

    g = _naca_a_family_g(a)
    h = _naca_a_family_h(a)

    am_x = a - x
    log_am_x = math.log(abs(am_x)) if abs(am_x) > 1e-12 else 0.0
    log_1m_x = math.log(1.0 - x) if (1.0 - x) > 1e-12 else 0.0

    term_in = (
        0.5 * am_x * am_x * log_am_x
        - 0.5 * (1.0 - x) ** 2 * log_1m_x
        + 0.25 * (1.0 - x) ** 2
        - 0.25 * am_x * am_x
    )
    bracket = (1.0 / (1.0 - a)) * term_in - _xlnx(x) + g - h * x
    return (design_cl / (2.0 * math.pi * (a + 1.0))) * bracket


def naca_a_family_coordinates(
    *,
    a: float,
    design_cl: float,
    thick_chord: float,
    n_half: int = _NACA_DAT_HALF_POINTS,
) -> list[tuple[float, float]]:
    """Selig-format coordinates for an airfoil with a-family mean
    line and the 4-digit thickness polynomial.

    Reusing the 4-digit thickness is a deliberate approximation: the
    6-series profiles that natively use the a-family carry a
    numerical thickness distribution (conformal-mapping derived) we
    don't reconstruct here. The 4-digit polynomial preserves t/c and
    peak-thickness location to within a few percent — sufficient for
    the workbench renderer.

    Slopes are central-differenced (eps=1e-6) because the analytical
    derivative carries log-singularities at x=a and x=1 that
    finite-differences handle cleanly.
    """
    EPS = 1e-6
    upper: list[tuple[float, float]] = []
    lower: list[tuple[float, float]] = []
    for i in range(n_half + 1):
        beta = math.pi * i / n_half
        x = 0.5 * (1.0 - math.cos(beta))
        yt = _naca4_thickness_offset(x, thick_chord)
        yc = naca_a_family_camber_at(x, a, design_cl)
        x_l = max(0.0, x - EPS)
        x_r = min(1.0, x + EPS)
        dyc = (
            naca_a_family_camber_at(x_r, a, design_cl) - naca_a_family_camber_at(x_l, a, design_cl)
        ) / max(x_r - x_l, EPS)
        theta = math.atan(dyc)
        sin_t = math.sin(theta)
        cos_t = math.cos(theta)
        upper.append((x - yt * sin_t, yc + yt * cos_t))
        lower.append((x + yt * sin_t, yc - yt * cos_t))
    return list(reversed(upper)) + lower[1:]


def ensure_naca_a_family_dat(
    *,
    name: str,
    a: float,
    design_cl: float,
    thick_chord: float,
    airfoils_dir: Path | None = None,
    ctx: Optional["ImportContext"] = None,
    component_name: str = "",
) -> Path:
    """Write ``{airfoils_dir}/{name}.dat`` for an "a"-family-mean-line
    airfoil. Idempotent, never raises.

    Used by:
    * NACA 6-series xsecs (``XS_SIX_SERIES``) — VSP carries
      ``Series``, ``IdealCl``, ``ThickChord``, ``A`` parms.
    * NACA 16-series xsecs (``XS_ONE_SIX_SERIES``) — same a=1.0
      uniform-load mean line, smaller t/c family.
    * Mean-line-modified 4-digit shapes when OpenVSP carries a
      ``MeanLine_a`` parm on the xsec.

    Out-of-range ``a`` (a<0 or a>1) is clamped to [0, 1] and an
    importer warning is emitted; OpenVSP enforces the range upstream
    but the clamp prevents log-of-negative crashes on corrupt input.
    """
    target_dir = airfoils_dir if airfoils_dir is not None else AIRFOILS_DIR
    target = target_dir / f"{name}.dat"
    if target.exists():
        return target

    if a < 0.0 or a > 1.0:
        if ctx is not None:
            ctx.add_warning(
                component_type="WING_XSEC",
                component_name=component_name or name,
                reason=(
                    f"NACA mean-line parameter a={a:.3f} is outside the "
                    "physical range [0, 1]; clamping for .dat generation."
                ),
                severity="info",
            )
        a = max(0.0, min(1.0, a))

    try:
        coords = naca_a_family_coordinates(a=a, design_cl=design_cl, thick_chord=thick_chord)
    except (ValueError, ArithmeticError) as exc:
        if ctx is not None:
            ctx.add_warning(
                component_type="WING_XSEC",
                component_name=component_name or name,
                reason=f"a-family mean-line generation failed: {exc}",
                severity="warning",
            )
        return target

    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        # Header convention: uppercase digits/series ID, lowercase ``a``
        # in the mean-line suffix to match the canonical NACA designation
        # ("NACA 65-410, a=0.5"). The body uppercases the bare name but
        # preserves the ``-a`` token verbatim.
        if name.lower().startswith("naca"):
            head, _, suffix = name.partition("-a")
            head_up = head.upper().replace("NACA", "NACA ")
            header = f"{head_up}-a{suffix}" if suffix else head_up
        else:
            header = name
        lines = [header.strip()]
        for x, y in coords:
            lines.append(f"{x:.6f}  {y:.6f}")
        target.write_text("\n".join(lines) + "\n")
    except OSError:
        pass
    return target


# ---------------------------------------------------------------------------
# foilsurf_u_for_xs — end-cap-aware mapping (per review on #642)
# ---------------------------------------------------------------------------


def foilsurf_u_for_xs(vsp: ModuleType, xsurf: object, xsec_index: int) -> Optional[float]:
    """Map an XSec index to the ``foilsurf_u`` parameter [0, 1].

    The "airfoil surface" in OpenVSP is the swept loft between the
    first and last *non-cap* xsecs. ``XS_POINT`` xsecs at the root or
    tip are wing-end caps, not airfoils — they map to ``None``.
    """
    n = int(vsp.GetNumXSec(xsurf))
    if n < 2:
        return 0.0

    first_airfoil = 0
    last_airfoil = n - 1

    xs_point = getattr(vsp, "XS_POINT", 0)
    if vsp.GetXSecShape(vsp.GetXSec(xsurf, 0)) == xs_point:
        first_airfoil = 1
    if vsp.GetXSecShape(vsp.GetXSec(xsurf, n - 1)) == xs_point:
        last_airfoil = n - 2

    if xsec_index < first_airfoil or xsec_index > last_airfoil:
        return None

    span = last_airfoil - first_airfoil
    if span == 0:
        return 0.0
    return (xsec_index - first_airfoil) / span


# ---------------------------------------------------------------------------
# Selig export fallback
# ---------------------------------------------------------------------------


CoordList = list[tuple[float, float]]


def _coords_hash(coordinates: CoordList) -> str:
    """Stable 10-hex content hash of an airfoil's coordinates (gh-795).

    Coordinates are rounded to 6 decimals before hashing so trivial
    float-formatting differences don't change the name. Identical
    geometry → identical hash → identical filename → reused on
    re-import (no ``vsp_imported_<random-geom-id>`` clutter).
    """
    canon = ";".join(f"{float(x):.6f},{float(y):.6f}" for x, y in coordinates)
    # Not a security primitive — a short content-dedup key. usedforsecurity
    # silences SAST/Sonar weak-hash hotspots.
    return hashlib.sha1(canon.encode("utf-8"), usedforsecurity=False).hexdigest()[:10]


def _read_dat_coords(path: Path) -> CoordList:
    """Parse ``x y`` coordinate pairs from a Selig ``.dat`` (header lines
    and blanks ignored)."""
    coords: CoordList = []
    for line in path.read_text().splitlines():
        parts = line.split()
        if len(parts) != 2:
            continue
        try:
            coords.append((float(parts[0]), float(parts[1])))
        except ValueError:
            continue
    return coords


def _write_selig_dat(target: Path, coordinates: CoordList, *, name: str) -> None:
    lines = [name]
    lines += [f"{float(x):.6f} {float(y):.6f}" for x, y in coordinates]
    target.write_text("\n".join(lines) + "\n")


def _dedup_consecutive_points(coordinates: CoordList, *, tol: float = 1e-9) -> CoordList:
    """Drop consecutive duplicate (within ``tol``) coordinate pairs (gh-789).

    OpenVSP exports can carry adjacent identical points, which makes
    AeroSandbox's ``Airfoil.repanel()`` (used during VLM section
    subdivision) raise "duplicate point" and crash the solve. Only
    *adjacent* duplicates are removed, so a legitimately repeated
    closing point (first == last of a closed contour) is preserved.
    """
    out: CoordList = []
    for pt in coordinates:
        if out:
            px, py = out[-1]
            if abs(pt[0] - px) <= tol and abs(pt[1] - py) <= tol:
                continue
        out.append(pt)
    return out


def write_imported_airfoil_dat(coordinates: CoordList, *, tag: str = "vsp_imported") -> str:
    """Store an imported/derived airfoil under a **content-hash** filename
    and return its relative path (gh-795).

    Re-import of the same geometry maps to the same ``{tag}_{hash}.dat``
    and the write is skipped (dedup). Used both for VSP-exported anchor
    profiles and for morphed intermediate profiles (gh-796).

    Consecutive duplicate points are removed before hashing/writing so the
    stored ``.dat`` never trips AeroSandbox's repanel duplicate-point guard
    (gh-789).
    """
    coordinates = _dedup_consecutive_points(coordinates)
    AIRFOILS_DIR.mkdir(parents=True, exist_ok=True)
    fname = f"{tag}_{_coords_hash(coordinates)}.dat"
    target = AIRFOILS_DIR / fname
    if not target.exists():
        _write_selig_dat(target, coordinates, name=fname[:-4])
    return f"./components/airfoils/{fname}"


def _resolve_coords(ref: str) -> Optional[CoordList]:
    """Resolve an airfoil reference (NACA name or ``.dat`` path) to
    coordinates (gh-796). Tries the path as-is, under ``AIRFOILS_DIR``,
    and as ``<name>.dat``; falls back to AeroSandbox's named library for
    bare NACA names. Returns ``None`` if nothing resolves."""
    for cand in (Path(ref), AIRFOILS_DIR / Path(ref).name, AIRFOILS_DIR / f"{ref}.dat"):
        if cand.exists():
            coords = _read_dat_coords(cand)
            if coords:
                return coords
    try:
        import aerosandbox as asb

        af = asb.Airfoil(name=ref)
        if af.coordinates is not None:
            return [(float(x), float(y)) for x, y in af.coordinates]
    except (ImportError, ModuleNotFoundError, ValueError, KeyError, TypeError):
        # asb absent or the name isn't in its library — expected misses.
        pass
    return None


# Content-keyed cache of Kulfan fits: the SLSQP fit is the expensive part
# of morphing, and the augmenter morphs every insert of a pair from the
# same two anchors. Keyed by coordinate-content hash (not file path), so
# it's correct regardless of AIRFOILS_DIR and safe across imports/tests.
_KULFAN_FIT_CACHE: dict[str, Optional[tuple]] = {}


def _fit_kulfan(coords: CoordList) -> Optional[tuple]:
    """Fit ``coords`` to a KulfanAirfoil; return (upper, lower, le, te)
    weight tuple, or ``None`` on failure. Cached by content hash."""
    key = _coords_hash(coords)
    if key in _KULFAN_FIT_CACHE:
        return _KULFAN_FIT_CACHE[key]
    try:
        import aerosandbox as asb
        import numpy as np

        k = asb.Airfoil(coordinates=np.array(coords, dtype=float)).to_kulfan_airfoil()
        res: Optional[tuple] = (
            tuple(float(w) for w in k.upper_weights),
            tuple(float(w) for w in k.lower_weights),
            float(k.leading_edge_weight),
            float(k.TE_thickness),
        )
    except Exception:  # noqa: BLE001 — asb optional / fit failure → caller falls back
        res = None
    _KULFAN_FIT_CACHE[key] = res
    return res


def _kulfan_morph(ca: CoordList, cb: CoordList, t: float) -> Optional[CoordList]:
    """Morph two airfoils in Kulfan/CST weight space at fraction ``t``
    (gh-796). Both are fit to ``asb.KulfanAirfoil``, the weights
    interpolated, and coordinates regenerated. Returns ``None`` on any
    failure / mode-count mismatch / non-finite result so the caller can
    fall back to a raw coordinate blend."""
    import aerosandbox as asb
    import numpy as np

    fa, fb = _fit_kulfan(ca), _fit_kulfan(cb)
    if fa is None or fb is None:
        return None
    ua, la, lea, tea = fa
    ub, lb, leb, teb = fb
    # Guard for callers that fit with different n_weights_per_side — the
    # default fit always matches, but stay defensive.
    if len(ua) != len(ub) or len(la) != len(lb):
        return None

    def _blend(a, b):
        return (1.0 - t) * np.asarray(a, dtype=float) + t * np.asarray(b, dtype=float)

    m = asb.KulfanAirfoil(
        name="morph",
        upper_weights=_blend(ua, ub),
        lower_weights=_blend(la, lb),
        leading_edge_weight=float((1.0 - t) * lea + t * leb),
        TE_thickness=float((1.0 - t) * tea + t * teb),
    )
    coords = np.array(m.coordinates, dtype=float)
    if coords.size == 0 or not np.isfinite(coords).all():
        return None
    return [(float(x), float(y)) for x, y in coords]


def _raw_blend(ca: CoordList, cb: CoordList, t: float) -> Optional[CoordList]:
    """Fallback morph: blend upper/lower surfaces on a common cosine
    x-grid (gh-796). Pure NumPy — works when AeroSandbox/Kulfan is
    unavailable or its fit fails (e.g. reflex/cusp profiles)."""
    import numpy as np

    def _split(c):
        arr = np.array(c, dtype=float)
        i = int(np.argmin(arr[:, 0]))
        top, bot = arr[: i + 1], arr[i:]
        if top.shape[0] < 2 or bot.shape[0] < 2:
            return None, None
        if top[0, 0] > top[-1, 0]:
            top = top[::-1]
        if bot[0, 0] > bot[-1, 0]:
            bot = bot[::-1]
        # The argmin-split assumes Selig order (upper then lower). If the
        # points came the other way round, the halves are inverted — detect
        # via mean-y and swap so ``top`` is always the upper surface.
        if float(top[:, 1].mean()) < float(bot[:, 1].mean()):
            top, bot = bot, top
        return top, bot

    xs = 0.5 * (1.0 - np.cos(np.linspace(0.0, np.pi, 80)))
    ta, ba = _split(ca)
    tb, bb = _split(cb)
    if ta is None or tb is None:
        return None
    yu = (1.0 - t) * np.interp(xs, ta[:, 0], ta[:, 1]) + t * np.interp(xs, tb[:, 0], tb[:, 1])
    yl = (1.0 - t) * np.interp(xs, ba[:, 0], ba[:, 1]) + t * np.interp(xs, bb[:, 0], bb[:, 1])
    if not (np.isfinite(yu).all() and np.isfinite(yl).all()):
        return None
    upper = list(zip(xs[::-1], yu[::-1], strict=True))
    lower = list(zip(xs, yl, strict=True))
    return [(float(x), float(y)) for x, y in upper + lower[1:]]


def morph_airfoils(ref_a: str, ref_b: str, t: float) -> Optional[str]:
    """Morph between two airfoil references at fraction ``t`` and store the
    result under a content-hash ``vsp_morph_*.dat`` (gh-796).

    Kulfan/CST interpolation first (smooth, always-valid); raw coordinate
    blend as fallback. Returns the relative ``.dat`` path, or ``None`` if
    neither anchor resolves / both methods fail — the caller then assigns
    the nearer anchor's airfoil so the geometric form is still captured.
    """
    ca, cb = _resolve_coords(ref_a), _resolve_coords(ref_b)
    if ca is None or cb is None:
        return None
    coords: Optional[CoordList] = None
    try:
        coords = _kulfan_morph(ca, cb, t)
    except Exception:  # noqa: BLE001 — fall back on any asb/fit failure
        coords = None
    if coords is None:
        try:
            coords = _raw_blend(ca, cb, t)
        except Exception:  # noqa: BLE001
            return None
    if not coords:
        return None
    return write_imported_airfoil_dat(coords, tag="vsp_morph")


def _export_selig(
    vsp: ModuleType,
    geom_id: str,
    xsurf: object,
    xs_index: int,
    tag: str = "vsp_imported",
) -> str:
    """Export an XSec's airfoil via ``vsp.WriteSeligAirfoil`` and store it
    under a content-hash filename (gh-795).

    VSP writes by path, so we export to a throwaway temp file, read the
    coordinates back, and re-store them under ``{tag}_{hash}.dat`` so
    identical geometry dedups across re-imports. Returns a relative path
    the WingXSecSchema can store.
    """
    AIRFOILS_DIR.mkdir(parents=True, exist_ok=True)
    u = foilsurf_u_for_xs(vsp, xsurf, xs_index)
    if u is None:
        # End-cap — call with 0.0 to keep behaviour deterministic.
        u = 0.0
    # Collision-safe OS temp name (geom_id may contain unsafe chars).
    fd, tmp_name = tempfile.mkstemp(prefix="_tmp_export_", suffix=".dat", dir=AIRFOILS_DIR)
    os.close(fd)
    tmp = Path(tmp_name)
    vsp.WriteSeligAirfoil(str(tmp), geom_id, float(u))
    coords = _read_dat_coords(tmp) if tmp.exists() else []
    try:
        tmp.unlink()
    except OSError:
        pass
    if coords:
        return write_imported_airfoil_dat(coords, tag=tag)
    # Defensive fallback (should not happen for valid geometry): re-export
    # to a sanitized name and still route through the content-hash sink so
    # the result dedups like every other imported airfoil.
    safe_id = "".join(c if c.isalnum() else "_" for c in str(geom_id))
    fallback = AIRFOILS_DIR / f"{tag}_{safe_id}_xsec{xs_index}.dat"
    vsp.WriteSeligAirfoil(str(fallback), geom_id, float(u))
    fb_coords = _read_dat_coords(fallback) if fallback.exists() else []
    if fb_coords:
        try:
            fallback.unlink()
        except OSError:
            pass
        return write_imported_airfoil_dat(fb_coords, tag=tag)
    return f"./components/airfoils/{fallback.name}"


# ---------------------------------------------------------------------------
# Public dispatch
# ---------------------------------------------------------------------------


def _get_parm(vsp: ModuleType, xs_id: str, name: str) -> float:
    pid = vsp.GetXSecParm(xs_id, name)
    if not pid:
        return 0.0
    return float(vsp.GetParmVal(pid))


def import_airfoil_from_xsec(
    *,
    xs_id: str,
    geom_id: str,
    xsurf: object,
    xs_index: int,
    ctx: ImportContext,
    vsp: ModuleType,
) -> str:
    """Resolve a single XSec's airfoil to a string the schema accepts.

    Returns either a NACA name (``"naca2412"``) or a relative path
    to a Selig ``.dat`` file written under :data:`AIRFOILS_DIR`.
    Never raises; on unknown shapes it falls back to a Selig export
    and adds a warning to ``ctx``.
    """
    shape = vsp.GetXSecShape(xs_id)

    # ---- NACA 4-series ------------------------------------------------
    if shape == getattr(vsp, "XS_FOUR_SERIES", None):
        camber = _get_parm(vsp, xs_id, "Camber")
        camber_loc = _get_parm(vsp, xs_id, "CamberLoc")
        thick_chord = _get_parm(vsp, xs_id, "ThickChord")
        name = naca_4series_name(camber=camber, camber_loc=camber_loc, thick_chord=thick_chord)
        # gh-700: write a .dat for this NACA-4 profile so the renderer
        # has something to draw, regardless of whether it's in our
        # curated airfoil library.
        ensure_naca4_dat(
            name=name,
            camber=camber,
            camber_loc=camber_loc,
            thick_chord=thick_chord,
        )
        return name

    # ---- NACA 4-digit modified ---------------------------------------
    if shape == getattr(vsp, "XS_FOUR_DIGIT_MOD", None):
        camber = _get_parm(vsp, xs_id, "Camber")
        camber_loc = _get_parm(vsp, xs_id, "CamberLoc")
        thick_chord = _get_parm(vsp, xs_id, "ThickChord")
        # gh-733 Phase 2 note: an earlier draft tried to overlay an
        # a-family mean line via a hypothetical ``MeanLine_a`` parm on
        # ``XS_FOUR_DIGIT_MOD``. Verified against OpenVSP 3.50 (PR #750
        # review): no such parm exists. The 4-digit-mod xsec exposes
        # only ``Camber``, ``CamberLoc``, ``ThickChord``, ``ThickLoc``,
        # ``LERadIndx``, ``IdealCl``, ``CamberInputFlag``, ``SharpTEFlag``.
        # The "mod" in this shape is the LE-radius / max-thickness-
        # position modifier, which is not encoded in the analytical
        # 4-digit thickness polynomial — so we still fall back to the
        # plain 4-digit shape for a renderable baseline. Spitfire-style
        # ``naca4-923-a0.6`` profiles require a different OpenVSP shape
        # entirely (likely ``XS_SIX_SERIES`` mis-named in the spec) and
        # would be picked up by the 6-series branch below.
        base = naca_4series_name(camber=camber, camber_loc=camber_loc, thick_chord=thick_chord)
        name = f"{base}-mod"
        ensure_naca4_dat(
            name=name,
            camber=camber,
            camber_loc=camber_loc,
            thick_chord=thick_chord,
        )
        return name

    # ---- NACA 5-series + modified ------------------------------------
    if shape == getattr(vsp, "XS_FIVE_DIGIT", None):
        camber = _get_parm(vsp, xs_id, "Camber")
        camber_loc = _get_parm(vsp, xs_id, "CamberLoc")
        reflex = _get_parm(vsp, xs_id, "Reflex")
        thick_chord = _get_parm(vsp, xs_id, "ThickChord")
        name = naca_5series_name(
            camber=camber, camber_loc=camber_loc, reflex=reflex, thick_chord=thick_chord
        )
        # gh-733: write a .dat for the 5-digit profile so the renderer
        # has the actual airfoil curve to draw (Bugatti 23018 / 23012,
        # Corsair 23015 / 23009, Spitfire 14012, etc.).
        ensure_naca5_dat(
            name=name,
            camber=camber,
            camber_loc=camber_loc,
            reflex=reflex,
            thick_chord=thick_chord,
            ctx=ctx,
            component_name=f"{geom_id}::XSec[{xs_index}]",
        )
        return name
    if shape == getattr(vsp, "XS_FIVE_DIGIT_MOD", None):
        camber = _get_parm(vsp, xs_id, "Camber")
        camber_loc = _get_parm(vsp, xs_id, "CamberLoc")
        reflex = _get_parm(vsp, xs_id, "Reflex")
        thick_chord = _get_parm(vsp, xs_id, "ThickChord")
        base = naca_5series_name(
            camber=camber, camber_loc=camber_loc, reflex=reflex, thick_chord=thick_chord
        )
        name = f"{base}-mod"
        # gh-733: same approach as XS_FOUR_DIGIT_MOD — write the base
        # 5-digit shape so the modified profile at least has a
        # renderable fallback; the LE-radius / max-thickness-position
        # modifiers are not encoded in the analytical thickness polynomial.
        ensure_naca5_dat(
            name=name,
            camber=camber,
            camber_loc=camber_loc,
            reflex=reflex,
            thick_chord=thick_chord,
            ctx=ctx,
            component_name=f"{geom_id}::XSec[{xs_index}]",
        )
        return name

    # ---- NACA 6-series ------------------------------------------------
    if shape == getattr(vsp, "XS_SIX_SERIES", None):
        series = int(_get_parm(vsp, xs_id, "Series"))
        ideal_cl = _get_parm(vsp, xs_id, "IdealCl")
        thick_chord = _get_parm(vsp, xs_id, "ThickChord")
        a_value = _get_parm(vsp, xs_id, "A")
        name = naca_6series_name(
            series=series, ideal_cl=ideal_cl, thick_chord=thick_chord, a=a_value
        )
        # gh-733 Phase 2: write a .dat using the a-family mean line
        # (which is the 6-series canonical mean line) + 4-digit
        # thickness polynomial as a pragmatic stand-in for the
        # numerical 6-series thickness distribution. The schema's
        # airfoil reference resolves to a real curve for the renderer;
        # an "approximation" info-warning is emitted via ``ctx`` so
        # users know the t/c is exact but the thickness shape is
        # 4-digit-equivalent rather than the conformal-mapped 6-series
        # form.
        if ctx is not None:
            ctx.add_warning(
                component_type="WING_XSEC",
                component_name=f"{geom_id}::XSec[{xs_index}]",
                reason=(
                    f"NACA 6-series ({name}): writing .dat with a-family "
                    "mean line + 4-digit thickness approximation. The 6-series "
                    "thickness distribution requires conformal mapping; "
                    "t/c and design Cl are preserved exactly."
                ),
                severity="info",
            )
        ensure_naca_a_family_dat(
            name=name,
            a=a_value,
            design_cl=ideal_cl,
            thick_chord=thick_chord,
            ctx=ctx,
            component_name=f"{geom_id}::XSec[{xs_index}]",
        )
        return name

    # ---- NACA 16-series ----------------------------------------------
    if shape == getattr(vsp, "XS_ONE_SIX_SERIES", None):
        # gh-733 Phase 2: XS_ONE_SIX_SERIES exposes ``IdealCl`` (the
        # design lift coefficient), ``ThickChord``, ``SharpTEFlag``.
        # Verified against OpenVSP 3.50 (PR #750 review). The
        # pre-PR code read ``Camber`` which doesn't exist on this
        # shape — VSP printed "GetParmVal::Can't Find Parm" to stderr
        # and returned 0.0, so 16-series xsecs were always treated as
        # symmetric (design_cl=0). The 16-series is the high-speed
        # propeller family using an a=1.0 (full-chord uniform load)
        # mean line; same 4-digit thickness approximation as 6-series.
        design_cl = _get_parm(vsp, xs_id, "IdealCl")
        thick_chord = _get_parm(vsp, xs_id, "ThickChord")
        name = naca_16series_name(design_cl=design_cl, thick_chord=thick_chord)
        if ctx is not None:
            ctx.add_warning(
                component_type="WING_XSEC",
                component_name=f"{geom_id}::XSec[{xs_index}]",
                reason=(
                    f"NACA 16-series ({name}): writing .dat with a=1 mean "
                    "line + 4-digit thickness approximation (16-series "
                    "thickness shape is not analytically encoded)."
                ),
                severity="info",
            )
        ensure_naca_a_family_dat(
            name=name,
            a=1.0,
            design_cl=design_cl,
            thick_chord=thick_chord,
            ctx=ctx,
            component_name=f"{geom_id}::XSec[{xs_index}]",
        )
        return name

    # ---- File-airfoil → export verbatim -------------------------------
    if shape == getattr(vsp, "XS_FILE_AIRFOIL", None):
        return _export_selig(vsp, geom_id, xsurf, xs_index)

    # ---- CST fallback -------------------------------------------------
    if shape == getattr(vsp, "XS_CST_AIRFOIL", None):
        ctx.add_warning(
            component_type="WING_XSEC",
            component_name=f"{geom_id}::XSec[{xs_index}]",
            reason=(
                "CST airfoil import is not supported natively in Phase 1 "
                "(see closed #651). Falling back to a sampled Selig .dat "
                "export of the camber surface."
            ),
            severity="info",
        )
        return _export_selig(vsp, geom_id, xsurf, xs_index, tag="vsp_imported_cst")

    # ---- Unknown shape — best-effort Selig export + warning ----------
    ctx.add_warning(
        component_type="WING_XSEC",
        component_name=f"{geom_id}::XSec[{xs_index}]",
        reason=(
            f"Airfoil shape id={shape} is not handled in Phase 1; "
            "exporting sampled .dat as fallback."
        ),
        severity="warning",
    )
    try:
        return _export_selig(vsp, geom_id, xsurf, xs_index, tag="vsp_imported_unknown")
    except Exception:
        # As an absolute last resort, return a placeholder so the
        # schema stays valid.
        return "./components/airfoils/naca0012.dat"
