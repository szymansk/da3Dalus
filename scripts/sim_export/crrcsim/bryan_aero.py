"""BRYAN aerodynamics for the CRRCSim export: AVL stability run + AeroBuildup polar.

Script prototype (gh-1195 step 2). Numbers come straight from AeroSandbox/AVL and are not read from
`app/` (ADR 0022: the kernel will replace these sources later).

Sources, by CRRCSim coefficient group:
  * AVL ST (stability axes, trimmed point): CL_a, CL_q, CL_de, Cm_a, Cm_q, Cm_de, all lateral
    derivatives and control derivatives, span efficiency e.
  * AeroBuildup polar (viscous, whole airplane incl. fuselage): CL_max, CL_min, CL_drop, CD profile
    parabola, Reynolds exponent, CD_stall, CG_arm, CD_AIsq.

Reference values (maintainer decision 2026-10-22): S_ref, b_ref, c_ref are projected onto the x-y
plane and passed explicitly to AVL and AeroBuildup.
"""

from __future__ import annotations

import json
import pathlib
import re
import subprocess
import tempfile
from dataclasses import dataclass, field

import aerosandbox as asb
import numpy as np
from avl_binary import avl_path

BRYAN_DIR = (
    pathlib.Path(__file__).resolve().parents[2] / "canon_checks" / "reference_fleet" / "bryan"
)
G = 9.80665
# control surface name in the geometry file -> name used here (and in the AVL file)
CONTROL_NAMES = {"Querruder": "aileron", "Hoehenruder": "elevator", "Seitenruder": "rudder"}
# Sections with a hinge point below this are not control surfaces: the geometry marks the
# rudder's slender lower trailing blade with hinge_point 0.0 / 0.002 (whole chord = rudder), which
# is not a hinged surface of the model. Documented in MAPPING.md.
MIN_HINGE_POINT = 0.3
AVL_WING_OPTS = {asb.AVL: dict(wing_level_spanwise_spacing=False, chordwise_resolution=10)}
# One strip per geometry segment. With 2..5 strips per segment AVL's longitudinal results drift
# without converging (static margin 6.1 / 4.0 / 1.7 / -1.5 / -6.5 % MAC, e 1.10 / 1.14 / 1.24 / 1.44 / 2.0):
# the tail sits within ~0.02 m of the wing's trailing-vortex plane, and strips narrower than that
# separation make the tail's induced velocities ill-conditioned. Lateral derivatives do not move.
# Coarsening the section clusters instead gives 5.4..6.2 % at one strip per segment.
AVL_XSEC_OPTS = {asb.AVL: dict(spanwise_resolution=1, spanwise_spacing="uniform")}


@dataclass(frozen=True)
class Reference:
    """Reference quantities, all projected onto the x-y plane."""

    s_ref: float
    b_ref: float
    c_ref: float
    x_mac_le: float  # MAC leading edge x (for % MAC reporting)


@dataclass
class Bryan:
    airplane: asb.Airplane
    mass_kg: float
    xyz_cg: list[float]
    ref: Reference
    geometry: dict
    atmosphere: asb.Atmosphere = field(default_factory=lambda: asb.Atmosphere(altitude=0))


def _airfoils() -> dict[str, asb.Airfoil]:
    return {
        "./bryan_profil.dat": asb.Airfoil("bryan", coordinates=str(BRYAN_DIR / "bryan_profil.dat")),
        "./bryan_platte.dat": asb.Airfoil(
            "bryan_platte", coordinates=str(BRYAN_DIR / "bryan_platte.dat")
        ),
    }


def projected_reference(wing: asb.Wing) -> Reference:
    """S, b, MAC of the main wing projected onto the x-y plane (top view)."""
    areas = wing.area(type="xy", _sectional=True)
    chords = []
    for inner, outer in zip(wing.xsecs[:-1], wing.xsecs[1:], strict=True):
        lam = outer.chord / inner.chord
        chords.append(2 / 3 * inner.chord * (1 + lam + lam**2) / (1 + lam))
    s_xy = float(sum(areas)) * (2 if wing.symmetric else 1)
    mac = float(np.dot(chords, areas) / sum(areas))
    b_y = float(wing.span(type="y"))
    # leading-edge x of the MAC from the area-weighted centroid of the quarter-chord line
    x_ac = float(wing.aerodynamic_center()[0])
    return Reference(s_ref=s_xy, b_ref=b_y, c_ref=mac, x_mac_le=x_ac - 0.25 * mac)


def build_bryan(deflections: dict[str, float] | None = None) -> Bryan:
    """BRYAN as an ASB airplane. `deflections` (deg) set aileron/elevator/rudder for AeroBuildup."""
    deflections = deflections or {}
    geo = json.loads((BRYAN_DIR / "bryan.airplane.json").read_text())
    af = _airfoils()
    wings = []
    for name, w in geo["wings"].items():
        xsecs = []
        for x in w["x_secs"]:
            cs = []
            c = x.get("control_surface")
            if c and c["hinge_point"] >= MIN_HINGE_POINT:
                cname = CONTROL_NAMES[c["name"]]
                cs = [
                    asb.ControlSurface(
                        name=cname,
                        symmetric=c["symmetric"],
                        hinge_point=c["hinge_point"],
                        deflection=deflections.get(cname, 0.0),
                    )
                ]
            xsecs.append(
                asb.WingXSec(
                    xyz_le=x["xyz_le"],
                    chord=x["chord"],
                    twist=x["twist"],
                    airfoil=af[x["airfoil"]],
                    control_surfaces=cs,
                    analysis_specific_options=AVL_XSEC_OPTS,
                )
            )
        wings.append(
            asb.Wing(
                name=name,
                symmetric=w["symmetric"],
                xsecs=xsecs,
                analysis_specific_options=AVL_WING_OPTS,
            )
        )
    # fuselage a, b are half-axes (schema); ASB width/height are full -> 2a, 2b
    fuselages = [
        asb.Fuselage(
            name=n,
            xsecs=[
                asb.FuselageXSec(xyz_c=x["xyz"], width=2 * x["a"], height=2 * x["b"], shape=x["n"])
                for x in f["x_secs"]
            ],
        )
        for n, f in geo["fuselages"].items()
    ]
    ref = projected_reference(wings[0])
    plane = asb.Airplane(
        name="BRYAN",
        xyz_ref=geo["xyz_ref"],
        wings=wings,
        fuselages=fuselages,
        s_ref=ref.s_ref,
        c_ref=ref.c_ref,
        b_ref=ref.b_ref,
    )
    return Bryan(plane, geo["total_mass_kg"], list(geo["xyz_ref"]), ref, geo)


# --- AVL ------------------------------------------------------------------------------------------
_NUM = r"(-?\d+\.\d*(?:[EeDd][-+]?\d+)?)"


def _get(out: str, key: str) -> float:
    # first hit: AVL also prints derived ratios such as "Clb Cnr / Clr Cnb = ..."
    found = re.findall(rf"\b{re.escape(key)}\s*=\s*{_NUM}", out)
    if not found:
        raise RuntimeError(f"AVL output lacks {key!r}:\n{out[-2500:]}")
    return float(found[0])


def write_avl_geometry(b: Bryan, work: pathlib.Path, op: asb.OperatingPoint) -> pathlib.Path:
    """Write the .avl file with ASB, then point AFIL at the original coordinate files (ASB's
    re-panelled export puts points at x > 1 for the wing section and AVL then returns nonsense)."""
    geom = work / "bryan.avl"
    asb.AVL(airplane=b.airplane, op_point=op, xyz_ref=b.xyz_cg).write_avl(geom)
    parts = geom.read_text().split("SURFACE")
    for k in range(1, len(parts)):
        main = parts[k].strip().startswith("Tragflaeche")
        dat = BRYAN_DIR / ("bryan_profil.dat" if main else "bryan_platte.dat")
        parts[k] = re.sub(r"\nAFIL\n[^\n]+\n", "\nAFIL\n" + str(dat) + "\n", parts[k])
    geom.write_text("SURFACE".join(parts))
    return geom


def control_order(avl_text: str) -> list[str]:
    """Control names in AVL's index order (d1, d2, ...): order of first appearance in the file."""
    names: list[str] = []
    for m in re.finditer(r"^CONTROL\s*\n#[^\n]*\n(\S+)", avl_text, re.M):
        if m.group(1) not in names:
            names.append(m.group(1))
    return names


def run_avl_trimmed(
    b: Bryan, cl_trim: float, v_trim: float, core_ratio: float | None = None
) -> dict[str, float]:
    """AVL at C_L = cl_trim, elevator trimmed to Cm = 0 about the CG, then the ST derivatives."""
    op = asb.OperatingPoint(b.atmosphere, velocity=v_trim, alpha=2.0)
    work = pathlib.Path(tempfile.mkdtemp(prefix="crrcsim_avl_"))
    geom = write_avl_geometry(b, work, op)
    order = control_order(geom.read_text())
    if order != ["aileron", "elevator", "rudder"]:
        raise RuntimeError(f"unexpected AVL control order {order}")
    # OPER > Option > C: core size / strip width ratio of the vortex cores (AVL default 0.25)
    core = ["o", "c", str(core_ratio), ""] if core_ratio is not None else []
    cmds = ["oper", *core, f"a c {cl_trim}", "d2 pm 0", "x", "st", "", "", "quit"]
    out = subprocess.run(
        [str(avl_path()), str(geom)],
        input="\n".join(cmds) + "\n",
        capture_output=True,
        text=True,
        cwd=work,
        timeout=120,
        check=False,
    ).stdout
    res = {
        "Sref": _get(out, "Sref"),
        "Cref": _get(out, "Cref"),
        "Bref": _get(out, "Bref"),
        "alpha_deg": _get(out, "Alpha"),
        "CL": _get(out, "CLtot"),
        "Cm": _get(out, "Cmtot"),
        "e": _get(out, "e"),
        "Xnp": _get(out, "Xnp"),
        "elevator_trim_deg": float(
            re.findall(rf"^\s*elevator\s*=\s*{_NUM}", out, re.M)[-1]
        ),  # last block: the trimmed deflection
    }
    for key in (
        "CLa", "CLq", "Cma", "Cmq",
        "CYb", "CYp", "CYr", "Clb", "Clp", "Clr", "Cnb", "Cnp", "Cnr",
        "CLd02", "Cmd02",
        "CYd01", "Cld01", "Cnd01",
        "CYd03", "Cld03", "Cnd03",
    ):  # fmt: skip
        res[key] = _get(out, key)
    res["raw_output"] = out  # type: ignore[assignment]
    return res


# --- AeroBuildup polar ------------------------------------------------------------------------------
def ab_polar(b: Bryan, v: float, alpha_deg: np.ndarray) -> dict[str, np.ndarray]:
    """Whole-airplane AeroBuildup polar at speed v (CL, CD, Cm about the CG)."""
    op = asb.OperatingPoint(b.atmosphere, velocity=v, alpha=np.asarray(alpha_deg, dtype=float))
    r = asb.AeroBuildup(b.airplane, op).run()
    return {k: np.ravel(r[k]).astype(float) for k in ("CL", "CD", "Cm")} | {
        "alpha": np.asarray(alpha_deg, dtype=float)
    }


# --- surface-level AVL mesh (convergence study / exporter) -------------------------------------
MIN_DY = 0.02


def merged(wing: asb.Wing, min_dy: float) -> list[asb.WingXSec]:
    xs = list(wing.xsecs)
    kept = [xs[0]]
    for x in xs[1:-1]:
        a, b = kept[-1].xyz_le, x.xyz_le
        if ((a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2) ** 0.5 >= min_dy:
            kept.append(x)
    a, b = kept[-1].xyz_le, xs[-1].xyz_le
    if len(kept) > 1 and ((a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2) ** 0.5 < min_dy:
        kept.pop()
    return [*kept, xs[-1]]


def inplane_span(xs: list[asb.WingXSec]) -> float:
    return sum(
        ((a.xyz_le[1] - b.xyz_le[1]) ** 2 + (a.xyz_le[2] - b.xyz_le[2]) ** 2) ** 0.5
        for a, b in zip(xs[:-1], xs[1:], strict=True)
    )


def avl_variant(b: Bryan, family: str, n_chord: int, n_wing: int) -> Bryan:
    """BRYAN with a surface-level AVL mesh: sections merged to MIN_DY, Nspan scaled by in-plane span,
    family 'uniform-aligned' (equal strip width on all surfaces) or 'sine' (-sine per half wing,
    cosine on the fin); Nchord = n_chord. References stay those of the full geometry."""
    sections = {w.name: merged(w, MIN_DY) for w in b.airplane.wings}
    span_wing = inplane_span(sections["Tragflaeche"])
    wings = []
    for w in b.airplane.wings:
        xs = sections[w.name]
        n = max(len(xs) - 1, round(n_wing * inplane_span(xs) / span_wing))
        spacing = (
            "uniform" if family == "uniform-aligned" else ("-sine" if w.symmetric else "cosine")
        )
        wings.append(
            asb.Wing(
                name=w.name,
                symmetric=w.symmetric,
                analysis_specific_options={
                    asb.AVL: dict(
                        wing_level_spanwise_spacing=True,
                        spanwise_resolution=n,
                        spanwise_spacing=spacing,
                        chordwise_resolution=n_chord,
                    )
                },
                xsecs=[
                    asb.WingXSec(
                        xyz_le=x.xyz_le,
                        chord=x.chord,
                        twist=x.twist,
                        airfoil=x.airfoil,
                        control_surfaces=x.control_surfaces,
                        analysis_specific_options={asb.AVL: {}},
                    )
                    for x in xs
                ],
            )
        )
    p = asb.Airplane(
        name="BRYAN",
        xyz_ref=b.airplane.xyz_ref,
        wings=wings,
        fuselages=b.airplane.fuselages,
        s_ref=b.ref.s_ref,
        c_ref=b.ref.c_ref,
        b_ref=b.ref.b_ref,
    )
    return Bryan(p, b.mass_kg, b.xyz_cg, b.ref, b.geometry)


# --- aligned explicit-station AVL mesh (the exporter's mesh) -----------------------------------
def _on(sec: dict) -> bool:
    c = sec.get("control_surface")
    return bool(c and c["hinge_point"] >= MIN_HINGE_POINT)


def _bounds(secs: list[dict], axis: int) -> tuple[float, float, list[float]]:
    pos = [s["xyz_le"][axis] for s in secs]
    bounds = [pos[i] for i in range(len(secs)) if _on(secs[i]) != (i > 0 and _on(secs[i - 1]))]
    bounds += [
        pos[i] for i in range(len(secs)) if i + 1 < len(secs) and _on(secs[i]) != _on(secs[i + 1])
    ]
    return pos[0], pos[-1], bounds


def _resample(
    secs: list[dict], axis: int, stations: list[float], af: dict, dz: float, symmetric_ctrl: dict
) -> list[asb.WingXSec]:
    pos = np.array([s["xyz_le"][axis] for s in secs])
    cols = {k: np.array([s["xyz_le"][i] for s in secs]) for i, k in enumerate("xyz")}
    chord = np.array([s["chord"] for s in secs])
    twist = np.array([s["twist"] for s in secs])
    hinge = np.array([s["control_surface"]["hinge_point"] if _on(s) else 0.0 for s in secs])
    out = []
    for t in stations:
        near = np.where(np.abs(pos - t) < 1e-9)[0]
        i = int(np.searchsorted(pos, t, side="right") - 1)
        i = min(max(i, 0), len(secs) - 2)
        if len(near):
            j = int(near[-1])
            ctrl_on = _on(secs[j])
        else:
            ctrl_on = _on(secs[i]) and _on(secs[i + 1])
        ctrl = []
        if ctrl_on:
            c = next(s["control_surface"] for s in (secs[i], secs[i + 1]) if _on(s))
            ctrl = [
                asb.ControlSurface(
                    name=CONTROL_NAMES[c["name"]],
                    symmetric=c["symmetric"],
                    hinge_point=float(np.interp(t, pos, hinge)),
                    deflection=0.0,
                )
            ]
        out.append(
            asb.WingXSec(
                xyz_le=[
                    float(np.interp(t, pos, cols["x"])),
                    float(np.interp(t, pos, cols["y"])),
                    float(np.interp(t, pos, cols["z"])) + dz,
                ],
                chord=float(np.interp(t, pos, chord)),
                twist=float(np.interp(t, pos, twist)),
                airfoil=af[secs[i]["airfoil"]],
                control_surfaces=ctrl,
                analysis_specific_options={asb.AVL: dict(spanwise_resolution=1)},
            )
        )
    return out


def aligned_stations(geo: dict, n_wing: int) -> tuple[list[float], list[float], list[float]]:
    """Strip stations of the aligned AVL mesh: wing y, horizontal tail y (the wing's stations over the
    tail span plus its tip) and fin z. geo is the `wings` dict of the geometry file."""
    w_secs, h_secs, f_secs = (
        geo["Tragflaeche"]["x_secs"],
        geo["Hoehenleitwerk"]["x_secs"],
        geo["Seitenleitwerk"]["x_secs"],
    )
    y0, y_tip, w_bounds = _bounds(w_secs, 1)
    _, t_tip, h_bounds = _bounds(h_secs, 1)
    step = (y_tip - y0) / n_wing
    grid = [y0 + k * step for k in range(n_wing + 1)]
    extra = [y for y in (*w_bounds, *h_bounds) if y0 < y < y_tip]
    wing_st = sorted({round(y, 9) for y in (*grid, *extra)})
    ht_st = [y for y in wing_st if y < t_tip - 0.3 * step]
    ht_st = [h_secs[0]["xyz_le"][1], *[y for y in ht_st if y > h_secs[0]["xyz_le"][1]], t_tip]
    z0, z1 = f_secs[0]["xyz_le"][2], f_secs[-1]["xyz_le"][2]
    _, _, f_bounds = _bounds(f_secs, 2)
    nf = max(2, round((z1 - z0) / step))
    fin_st = sorted(
        {round(z, 9) for z in (*[z0 + k * (z1 - z0) / nf for k in range(nf + 1)], *f_bounds)}
    )
    return wing_st, ht_st, fin_st


def aligned_variant(b: Bryan, case: str, n_chord: int, n_wing: int) -> Bryan:
    """BRYAN with an aligned explicit-station AVL mesh (one strip per station pair). case: 'full',
    'no-fin', 'ht+0.05', 'ht-0.05' (diagnostic tail shift) or 'wing-only'. References stay those of
    the full geometry."""
    af = _airfoils()
    geo = b.geometry["wings"]
    w_secs, h_secs, f_secs = (
        geo["Tragflaeche"]["x_secs"],
        geo["Hoehenleitwerk"]["x_secs"],
        geo["Seitenleitwerk"]["x_secs"],
    )
    wing_st, ht_st, fin_st = aligned_stations(geo, n_wing)
    dz = {"ht+0.05": 0.05, "ht-0.05": -0.05}.get(case, 0.0)
    opts = {asb.AVL: dict(wing_level_spanwise_spacing=False, chordwise_resolution=n_chord)}
    wings = [
        asb.Wing(name="Tragflaeche", symmetric=True, analysis_specific_options=opts,
                 xsecs=_resample(w_secs, 1, wing_st, af, 0.0, {}))
    ]  # fmt: skip
    if case != "wing-only":
        wings.append(
            asb.Wing(name="Hoehenleitwerk", symmetric=True, analysis_specific_options=opts,
                     xsecs=_resample(h_secs, 1, ht_st, af, dz, {}))
        )  # fmt: skip
    if case == "full":
        wings.append(
            asb.Wing(name="Seitenleitwerk", symmetric=False, analysis_specific_options=opts,
                     xsecs=_resample(f_secs, 2, fin_st, af, 0.0, {}))
        )  # fmt: skip
    plane = asb.Airplane(
        name="BRYAN", xyz_ref=b.airplane.xyz_ref, wings=wings, fuselages=b.airplane.fuselages,
        s_ref=b.ref.s_ref, c_ref=b.ref.c_ref, b_ref=b.ref.b_ref,
    )  # fmt: skip
    return Bryan(plane, b.mass_kg, b.xyz_cg, b.ref, b.geometry)
