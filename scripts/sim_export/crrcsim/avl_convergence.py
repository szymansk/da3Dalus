"""AVL mesh-convergence study for BRYAN's stability derivatives (gh-1195).

    poetry run python scripts/sim_export/crrcsim/avl_convergence.py [--out table.md]

Meshes (all with the x-y projected references of the full geometry, trimmed at CL = m g / (q S)):
  segment-N   per-segment strips (the exporter's setting is segment-1), original sections
  surface-S-N surface-level Nspan = N with spacing S ("cosine" | "uniform"), on sections merged to a
              minimum spacing MIN_DY (AVL needs Nspan >= number of sections - 1, and sliver sections
              of a few mm cannot be meshed at surface level); wing and tail share N and spacing
Reports NP (% MAC), static margin, e, CL_a, Cm_a, Cm_q, elevator trim and the lateral set per mesh.
"""

from __future__ import annotations

import argparse
import pathlib
import sys

import aerosandbox as asb

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import bryan_aero as ba  # noqa: E402

SPEED, MIN_DY = 7.82, 0.02
SURFACE_N = (12, 20, 40, 80)
SPACINGS = ("cosine", "uniform")
SEGMENT_N = (1, 2, 3)
KEYS = ("e", "CLa", "Cma", "Cmq", "Clb", "Clp", "Cnb", "Cnr", "elevator_trim_deg")


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


def with_mesh(b: ba.Bryan, mode: str, n: int, spacing: str) -> ba.Bryan:
    wings = []
    for w in b.airplane.wings:
        if mode == "segment":
            xs = list(w.xsecs)
            xo = {asb.AVL: dict(spanwise_resolution=n, spanwise_spacing="uniform")}
            wo = {asb.AVL: dict(wing_level_spanwise_spacing=False, chordwise_resolution=10)}
        else:
            xs = merged(w, MIN_DY)
            xo = {asb.AVL: {}}
            wo = {
                asb.AVL: dict(
                    wing_level_spanwise_spacing=True,
                    spanwise_resolution=n,
                    spanwise_spacing=spacing,
                    chordwise_resolution=10,
                )
            }
        wings.append(
            asb.Wing(
                name=w.name,
                symmetric=w.symmetric,
                analysis_specific_options=wo,
                xsecs=[
                    asb.WingXSec(
                        xyz_le=x.xyz_le,
                        chord=x.chord,
                        twist=x.twist,
                        airfoil=x.airfoil,
                        control_surfaces=x.control_surfaces,
                        analysis_specific_options=xo,
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
    return ba.Bryan(p, b.mass_kg, b.xyz_cg, b.ref, b.geometry)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=pathlib.Path)
    args = ap.parse_args(argv)
    b0 = ba.build_bryan()
    cl = b0.mass_kg * ba.G / (0.5 * float(b0.atmosphere.density()) * SPEED**2 * b0.ref.s_ref)
    meshes = [("segment", n, "uniform") for n in SEGMENT_N]
    meshes += [("surface", n, s) for s in SPACINGS for n in SURFACE_N]
    rows = [
        "| mesh | NP % MAC | SM % MAC | " + " | ".join(KEYS) + " |",
        "|---|---|---|" + "---|" * len(KEYS),
    ]
    for mode, n, spacing in meshes:
        label = f"segment-{n}" if mode == "segment" else f"surface-{spacing}-{n}"
        try:
            r = ba.run_avl_trimmed(with_mesh(b0, mode, n, spacing), cl, SPEED)
        except RuntimeError as exc:
            rows.append(f"| {label} | failed: {str(exc).strip().splitlines()[-1][:60]} |")
        else:
            x_le = b0.ref.x_mac_le
            np_pct = 100 * (r["Xnp"] - x_le) / b0.ref.c_ref
            sm = 100 * (r["Xnp"] - b0.xyz_cg[0]) / b0.ref.c_ref
            rows.append(
                f"| {label} | {np_pct:.1f} | {sm:.1f} | "
                + " | ".join(f"{r[k]:.3f}" for k in KEYS)
                + " |"
            )
        print(rows[-1], flush=True)
    if args.out:
        args.out.write_text("\n".join(rows) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
