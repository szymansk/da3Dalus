"""AVL non-convergence diagnostics for BRYAN (gh-1195), complementing avl_convergence.py.

    poetry run python scripts/sim_export/crrcsim/avl_diagnostics.py [--out table.md]

Meshes are *aligned*: every surface is resampled (linear in x_le, z_le, chord, twist) at explicit
stations, one strip per station pair, so the horizontal tail's strip boundaries sit at the wing's strip
y-positions over the tail span (plus the control-surface boundaries of both). The fin uses the same strip
width along z. Cases, one change each:
  full        wing + HT + fin
  no-fin      wing + HT
  ht+0.05 / ht-0.05   no-fin with the HT moved vertically by +-0.05 m (diagnostic only)
  wing-only   wing alone (does e converge below 1?)
Levels refine Nchord and Nspan together; core ratio 0.25 and 0.5 (OPER > Option > C).
"""

from __future__ import annotations

import argparse
import pathlib
import re
import subprocess
import sys
import tempfile

import aerosandbox as asb
import numpy as np
from avl_binary import avl_path

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import bryan_aero as ba  # noqa: E402

SPEED = 7.82
LEVELS = ((5, 12), (10, 24), (20, 48))
CORES = (0.25, 0.5)
CASES = ("full", "no-fin", "ht+0.05", "ht-0.05", "wing-only")


def on(sec: dict) -> bool:
    c = sec.get("control_surface")
    return bool(c and c["hinge_point"] >= ba.MIN_HINGE_POINT)


def stations_for(secs: list[dict], axis: int) -> tuple[float, float, list[float]]:
    pos = [s["xyz_le"][axis] for s in secs]
    bounds = [pos[i] for i in range(len(secs)) if on(secs[i]) != (i > 0 and on(secs[i - 1]))]
    bounds += [
        pos[i] for i in range(len(secs)) if i + 1 < len(secs) and on(secs[i]) != on(secs[i + 1])
    ]
    return pos[0], pos[-1], bounds


def resample(
    secs: list[dict], axis: int, stations: list[float], af: dict, dz: float, symmetric_ctrl: dict
) -> list[asb.WingXSec]:
    pos = np.array([s["xyz_le"][axis] for s in secs])
    cols = {k: np.array([s["xyz_le"][i] for s in secs]) for i, k in enumerate("xyz")}
    chord = np.array([s["chord"] for s in secs])
    twist = np.array([s["twist"] for s in secs])
    hinge = np.array([s["control_surface"]["hinge_point"] if on(s) else 0.0 for s in secs])
    out = []
    for t in stations:
        near = np.where(np.abs(pos - t) < 1e-9)[0]
        i = int(np.searchsorted(pos, t, side="right") - 1)
        i = min(max(i, 0), len(secs) - 2)
        if len(near):
            j = int(near[-1])
            ctrl_on = on(secs[j])
        else:
            ctrl_on = on(secs[i]) and on(secs[i + 1])
        ctrl = []
        if ctrl_on:
            c = next(s["control_surface"] for s in (secs[i], secs[i + 1]) if on(s))
            ctrl = [
                asb.ControlSurface(
                    name=ba.CONTROL_NAMES[c["name"]],
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


def aligned_variant(b: ba.Bryan, case: str, n_chord: int, n_wing: int) -> ba.Bryan:
    af = ba._airfoils()
    geo = b.geometry["wings"]
    w_secs, h_secs, f_secs = (
        geo["Tragflaeche"]["x_secs"],
        geo["Hoehenleitwerk"]["x_secs"],
        geo["Seitenleitwerk"]["x_secs"],
    )
    y0, y_tip, w_bounds = stations_for(w_secs, 1)
    _, t_tip, h_bounds = stations_for(h_secs, 1)
    step = (y_tip - y0) / n_wing
    grid = [y0 + k * step for k in range(n_wing + 1)]
    extra = [y for y in (*w_bounds, *h_bounds) if y0 < y < y_tip]
    wing_st = sorted({round(y, 9) for y in (*grid, *extra)})
    ht_st = [y for y in wing_st if y < t_tip - 0.3 * step]
    ht_st = [h_secs[0]["xyz_le"][1], *[y for y in ht_st if y > h_secs[0]["xyz_le"][1]], t_tip]
    z0, z1 = f_secs[0]["xyz_le"][2], f_secs[-1]["xyz_le"][2]
    _, _, f_bounds = stations_for(f_secs, 2)
    nf = max(2, round((z1 - z0) / step))
    fin_st = sorted(
        {round(z, 9) for z in (*[z0 + k * (z1 - z0) / nf for k in range(nf + 1)], *f_bounds)}
    )
    dz = {"ht+0.05": 0.05, "ht-0.05": -0.05}.get(case, 0.0)
    opts = {asb.AVL: dict(wing_level_spanwise_spacing=False, chordwise_resolution=n_chord)}
    wings = [
        asb.Wing(name="Tragflaeche", symmetric=True, analysis_specific_options=opts,
                 xsecs=resample(w_secs, 1, wing_st, af, 0.0, {}))
    ]  # fmt: skip
    if case != "wing-only":
        wings.append(
            asb.Wing(name="Hoehenleitwerk", symmetric=True, analysis_specific_options=opts,
                     xsecs=resample(h_secs, 1, ht_st, af, dz, {}))
        )  # fmt: skip
    if case == "full":
        wings.append(
            asb.Wing(name="Seitenleitwerk", symmetric=False, analysis_specific_options=opts,
                     xsecs=resample(f_secs, 2, fin_st, af, 0.0, {}))
        )  # fmt: skip
    plane = asb.Airplane(
        name="BRYAN", xyz_ref=b.airplane.xyz_ref, wings=wings, fuselages=b.airplane.fuselages,
        s_ref=b.ref.s_ref, c_ref=b.ref.c_ref, b_ref=b.ref.b_ref,
    )  # fmt: skip
    return ba.Bryan(plane, b.mass_kg, b.xyz_cg, b.ref, b.geometry)


def run(b: ba.Bryan, cl: float, core: float) -> dict[str, float]:
    op = asb.OperatingPoint(b.atmosphere, velocity=SPEED, alpha=2.0)
    work = pathlib.Path(tempfile.mkdtemp(prefix="avl_diag_"))
    geom = ba.write_avl_geometry(b, work, op)
    cmds = ["oper", "o", "c", str(core), "", f"a c {cl}", "x", "st", "", "", "quit"]
    out = subprocess.run(
        [str(avl_path()), str(geom)], input="\n".join(cmds) + "\n", capture_output=True,
        text=True, cwd=work, timeout=300, check=False,
    ).stdout  # fmt: skip
    return {k: ba._get(out, k) for k in ("e", "CLa", "Cma", "Xnp")}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=pathlib.Path)
    args = ap.parse_args(argv)
    b0 = ba.build_bryan()
    cl = b0.mass_kg * ba.G / (0.5 * float(b0.atmosphere.density()) * SPEED**2 * b0.ref.s_ref)
    rows = [
        "| case | Nchord/Nspan | core | NP % MAC | SM % MAC | e | CLa | Cma |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for case in CASES:
        for n_chord, n_wing in LEVELS:
            for core in CORES:
                label = f"| {case} | {n_chord}/{n_wing} | {core} |"
                try:
                    r = run(aligned_variant(b0, case, n_chord, n_wing), cl, core)
                except (RuntimeError, ValueError) as exc:
                    rows.append(f"{label} failed: {str(exc).strip().splitlines()[-1][:70]} |")
                else:
                    npp = 100 * (r["Xnp"] - b0.ref.x_mac_le) / b0.ref.c_ref
                    sm = 100 * (r["Xnp"] - b0.xyz_cg[0]) / b0.ref.c_ref
                    rows.append(
                        f"{label} {npp:.1f} | {sm:.1f} | {r['e']:.3f} | {r['CLa']:.3f} | {r['Cma']:.3f} |"
                    )
                print(rows[-1], flush=True)
    if args.out:
        args.out.write_text("\n".join(rows) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
