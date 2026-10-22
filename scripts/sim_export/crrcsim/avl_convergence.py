"""AVL mesh-convergence study for BRYAN's stability derivatives (gh-1195).

    poetry run python scripts/sim_export/crrcsim/avl_convergence.py [--out table.md]

Follows the AVL manual's vortex-spacing rules (avl_doc, "Panel refinement study"):
  * one spanwise distribution per SURFACE (wing-level Nspan/Sspace) on sections merged to MIN_DY,
  * wing, tail and fin share the strip width where they line up in x ("uniform-aligned": equal strip
    width, tail/fin counts scaled by span) or use -sine/cosine per surface ("sine"),
  * Nchord and Nspan are refined together in 2x steps (LEVELS),
  * the vortex-core ratio (OPER > Option > C, default 0.25) is varied 0.25 / 0.5 per level.
Reports NP, static margin, e, CL_a, Cm_a, Cm_q, elevator trim and lateral derivatives per level.
Converged means |delta NP| < 0.5 % MAC between the last two levels, with e < 1.
"""

from __future__ import annotations

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import bryan_aero as ba  # noqa: E402

SPEED = 7.82
LEVELS = ((5, 12), (10, 24), (20, 48), (40, 96))  # (Nchord, Nspan of the wing half)
CORES = (0.25, 0.5)
FAMILIES = ("uniform-aligned", "sine")
KEYS = ("e", "CLa", "Cma", "Cmq", "Clb", "Clp", "Cnb", "Cnr", "elevator_trim_deg")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=pathlib.Path)
    args = ap.parse_args(argv)
    b0 = ba.build_bryan()
    cl = b0.mass_kg * ba.G / (0.5 * float(b0.atmosphere.density()) * SPEED**2 * b0.ref.s_ref)
    rows = [
        "| family | Nchord/Nspan(wing) | core | NP % MAC | SM % MAC | " + " | ".join(KEYS) + " |",
        "|---|---|---|---|---|" + "---|" * len(KEYS),
    ]
    for family in FAMILIES:
        for n_chord, n_wing in LEVELS:
            for core in CORES:
                label = f"| {family} | {n_chord}/{n_wing} | {core} |"
                try:
                    r = ba.run_avl_trimmed(
                        ba.avl_variant(b0, family, n_chord, n_wing), cl, SPEED, core
                    )
                except RuntimeError as exc:
                    rows.append(f"{label} failed: {str(exc).strip().splitlines()[-1][:60]} |")
                else:
                    np_pct = 100 * (r["Xnp"] - b0.ref.x_mac_le) / b0.ref.c_ref
                    sm = 100 * (r["Xnp"] - b0.xyz_cg[0]) / b0.ref.c_ref
                    vals = " | ".join(f"{r[k]:.3f}" for k in KEYS)
                    rows.append(f"{label} {np_pct:.1f} | {sm:.1f} | {vals} |")
                print(rows[-1], flush=True)
    if args.out:
        args.out.write_text("\n".join(rows) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
