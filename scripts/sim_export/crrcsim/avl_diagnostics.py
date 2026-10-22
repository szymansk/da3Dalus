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
                    r = run(ba.aligned_variant(b0, case, n_chord, n_wing), cl, core)
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
