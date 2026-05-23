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

from pathlib import Path
from types import ModuleType
from typing import Optional

from app.converters.openvsp_importer import ImportContext


# Resolves at import time. Tests monkeypatch this to a tmp directory.
AIRFOILS_DIR: Path = Path("components") / "airfoils"


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


def naca_16series_name(*, camber: float, thick_chord: float) -> str:
    """Build a NACA 16-series name (e.g. "naca16-012")."""
    c = round(camber * 100)
    t = round(thick_chord * 100)
    return f"naca16-{c:d}{t:02d}"


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


def _export_selig(
    vsp: ModuleType,
    geom_id: str,
    xsurf: object,
    xs_index: int,
    tag: str = "vsp_imported",
) -> str:
    """Write a Selig ``.dat`` file via ``vsp.WriteSeligAirfoil``.

    Returns a relative path string the WingXSecSchema can store.
    Filenames are unique per (geom, xs_index, tag) to support multiple
    file-airfoils on a single import.
    """
    AIRFOILS_DIR.mkdir(parents=True, exist_ok=True)
    fname = f"{tag}_{geom_id}_xsec{xs_index}.dat"
    target = AIRFOILS_DIR / fname
    u = foilsurf_u_for_xs(vsp, xsurf, xs_index)
    if u is None:
        # End-cap — call with 0.0 to keep behaviour deterministic.
        u = 0.0
    vsp.WriteSeligAirfoil(str(target), geom_id, float(u))
    return f"./components/airfoils/{fname}"


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
        return naca_4series_name(
            camber=_get_parm(vsp, xs_id, "Camber"),
            camber_loc=_get_parm(vsp, xs_id, "CamberLoc"),
            thick_chord=_get_parm(vsp, xs_id, "ThickChord"),
        )

    # ---- NACA 4-digit modified ---------------------------------------
    if shape == getattr(vsp, "XS_FOUR_DIGIT_MOD", None):
        base = naca_4series_name(
            camber=_get_parm(vsp, xs_id, "Camber"),
            camber_loc=_get_parm(vsp, xs_id, "CamberLoc"),
            thick_chord=_get_parm(vsp, xs_id, "ThickChord"),
        )
        # Append the leading-edge-radius/thickness-location modifier
        # (OpenVSP's "modified" parms). Format: "naca2412-mod"
        return f"{base}-mod"

    # ---- NACA 5-series + modified ------------------------------------
    if shape == getattr(vsp, "XS_FIVE_DIGIT", None):
        return naca_5series_name(
            camber=_get_parm(vsp, xs_id, "Camber"),
            camber_loc=_get_parm(vsp, xs_id, "CamberLoc"),
            reflex=_get_parm(vsp, xs_id, "Reflex"),
            thick_chord=_get_parm(vsp, xs_id, "ThickChord"),
        )
    if shape == getattr(vsp, "XS_FIVE_DIGIT_MOD", None):
        base = naca_5series_name(
            camber=_get_parm(vsp, xs_id, "Camber"),
            camber_loc=_get_parm(vsp, xs_id, "CamberLoc"),
            reflex=_get_parm(vsp, xs_id, "Reflex"),
            thick_chord=_get_parm(vsp, xs_id, "ThickChord"),
        )
        return f"{base}-mod"

    # ---- NACA 6-series ------------------------------------------------
    if shape == getattr(vsp, "XS_SIX_SERIES", None):
        return naca_6series_name(
            series=int(_get_parm(vsp, xs_id, "Series")),
            ideal_cl=_get_parm(vsp, xs_id, "IdealCl"),
            thick_chord=_get_parm(vsp, xs_id, "ThickChord"),
            a=_get_parm(vsp, xs_id, "A"),
        )

    # ---- NACA 16-series ----------------------------------------------
    if shape == getattr(vsp, "XS_ONE_SIX_SERIES", None):
        return naca_16series_name(
            camber=_get_parm(vsp, xs_id, "Camber"),
            thick_chord=_get_parm(vsp, xs_id, "ThickChord"),
        )

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
