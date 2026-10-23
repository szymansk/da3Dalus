"""BRYAN neutral point under the aero_kernel's conditions, from the template's own mesh (gh-1203).

    poetry run python scripts/sim_export/crrcsim/avl_kernel_reference.py [--out table.md]

The reference value the kernel's AVL adapter is tested against (aero_kernel/tests, 0.1 % MAC). The
template's aligned explicit-station mesh (avl_diagnostics.py, 'full', Nchord/Nspan 10/24, core 0.25)
is run with the kernel's conditions: no fuselage (no BODY), Mach 0 (AVL's file default here), the
reference point at the origin, the
lift coefficient constrained (`a c`) and not trimmed, at the C_L of BRYAN's minimum-drag speed from
the kernel (C_L,md 0.6240228 for 0.151 kg at sea level, NeuralFoil xlarge). The control surfaces stay in
the file; at zero deflection they do not change the neutral point.

Two variants, because the template and the kernel differ in two station rules: the template adds
stations at control-surface boundaries and starts the wing at its stored root y = -0.25 mm (a strip
that crosses its own mirror image), while the kernel starts mirrored surfaces at the centreline and
has no control-surface stations.
  * template   the template's stations as they are;
  * centreline the same, without the control-surface stations and with the wing starting at y = 0.
The kernel is pinned against the second (the same mesh by construction); the first shows what the
template's own station rules are worth (0.2 % MAC).
"""

from __future__ import annotations

import argparse
import pathlib
import sys

import aerosandbox as asb

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import avl_diagnostics as ad  # noqa: E402
import bryan_aero as ba  # noqa: E402

KERNEL_CL = 0.6240228  # BRYAN C_L at the minimum-drag speed, aero_kernel/tests/test_minimum_drag_speed_fleet.py
PROTOTYPE_CL = 0.5656  # trimmed prototype, 7.82 m/s
CASES = (("kernel C_L,md", KERNEL_CL), ("prototype C_L", PROTOTYPE_CL))
VARIANTS = ("template", "centreline")


ORIGIN = [0.0, 0.0, 0.0]


def without_fuselage(b: ba.Bryan) -> ba.Bryan:
    """The same airplane without its fuselages (the kernel models none), reference point at the origin.

    The neutral point AVL reports depends on the reference point through the rotation into stability
    axes: moving it from the origin to BRYAN's CG (z = -6 mm) moves Xnp by +0.27 mm (0.2 % MAC). The
    kernel puts the reference at the geometry origin, so does this.
    """
    plane = asb.Airplane(
        name=b.airplane.name,
        xyz_ref=ORIGIN,
        wings=b.airplane.wings,
        fuselages=[],
        s_ref=b.ref.s_ref,
        c_ref=b.ref.c_ref,
        b_ref=b.ref.b_ref,
    )
    return ba.Bryan(plane, b.mass_kg, ORIGIN, b.ref, b.geometry)


def centreline_bounds(secs: list[dict], axis: int) -> tuple[float, float, list[float]]:
    """Replacement of ``bryan_aero._bounds``: no control stations, mirrored surfaces from y = 0."""
    first, last, _ = ORIGINAL_BOUNDS(secs, axis)
    return (max(first, 0.0) if axis == 1 else first), last, []


ORIGINAL_BOUNDS = ba._bounds


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=pathlib.Path)
    args = ap.parse_args(argv)
    b0 = ba.build_bryan()
    rows = ["| variant | C_L | label | Xnp m | NP % MAC | e |", "|---|---|---|---|---|---|"]
    for variant in VARIANTS:
        ba._bounds = ORIGINAL_BOUNDS if variant == "template" else centreline_bounds  # type: ignore[assignment]
        mesh = without_fuselage(ba.aligned_variant(b0, "full", 10, 24))
        for label, cl in CASES:
            r = ad.run(mesh, cl, 0.25)
            pct = 100 * (r["Xnp"] - b0.ref.x_mac_le) / b0.ref.c_ref
            rows.append(
                f"| {variant} | {cl} | {label} | {r['Xnp']:.6f} | {pct:.2f} | {r['e']:.3f} |"
            )
            print(rows[-1], flush=True)
    ba._bounds = ORIGINAL_BOUNDS  # type: ignore[assignment]
    if args.out:
        args.out.write_text("\n".join(rows) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
