"""BRYAN neutral point under the aero_kernel's conditions, from the template's own mesh (gh-1203).

    poetry run python scripts/sim_export/crrcsim/avl_kernel_reference.py [--out table.md]

The reference value the kernel's AVL adapter is tested against (aero_kernel/tests, 0.1 % MAC). The
template's aligned explicit-station mesh (avl_diagnostics.py, 'full', Nchord/Nspan 10/24, core 0.25)
is run with the kernel's conditions: no fuselage (no BODY), Mach 0 (AVL's file default here), the
reference point at the origin, the lift coefficient constrained (`a c`) and not trimmed, at the C_L of
BRYAN's minimum-drag speed from the kernel (C_L,md 0.6240228 for 0.151 kg at sea level, NeuralFoil
xlarge). The control surfaces stay in the file; at zero deflection they do not change the neutral
point.

The airfoil contours are those the kernel gives AVL: every contour repanelled to 80 points per side
by the kernel's own function (aero_kernel/solvers/avl_contour.py, AIRFOIL_POINTS_PER_SIDE in
aero_kernel/solvers/avl.py; AVL stops at 399 contour points in total). The geometry document's
contour files are repanelled so, the writer is the template's.

Two variants, because the template and the kernel differ in two station rules: the template adds
stations at control-surface boundaries and starts the wing at its stored root y = -0.25 mm, while the
kernel starts mirrored surfaces at the centreline and has no control-surface stations.
  * template   the template's stations as they are; the kernel is pinned against this row;
  * centreline the template's stations without the control-surface stations and with the wing
               starting at y = 0, reported to show what the two station rules are worth.
"""

from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys
import tempfile

import aerosandbox as asb
from avl_binary import avl_path

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
import bryan_aero as ba  # noqa: E402
from aero_kernel.solvers.avl import AIRFOIL_POINTS_PER_SIDE  # noqa: E402
from aero_kernel.solvers.avl_contour import repanel  # noqa: E402

KERNEL_CL = 0.6240228  # BRYAN C_L at the minimum-drag speed, aero_kernel/tests/test_minimum_drag_speed_fleet.py
PROTOTYPE_CL = 0.5656  # trimmed prototype, 7.82 m/s
CASES = (("kernel C_L,md", KERNEL_CL), ("prototype C_L", PROTOTYPE_CL))
VARIANTS = ("template", "centreline")
CORE_RATIO = 0.25
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


def repanelled(work: pathlib.Path, source: pathlib.Path) -> pathlib.Path:
    """Write ``source`` repanelled to AIRFOIL_POINTS_PER_SIDE per side into ``work``."""
    points = [
        (float(x), float(y))
        for x, y in (
            map(float, line.split())
            for line in source.read_text().splitlines()
            if len(line.split()) == 2 and line.split()[0].replace(".", "", 1).lstrip("-").isdigit()
        )
    ]
    target = work / f"{source.stem}_repanelled.dat"
    body = "\n".join(f"{x:.8f} {y:.8f}" for x, y in repanel(points, AIRFOIL_POINTS_PER_SIDE))
    target.write_text(f"{source.stem}\n{body}\n")
    return target


def run(b: ba.Bryan, cl: float) -> dict[str, float]:
    """AVL on the mesh of ``b`` with repanelled contours, C_L constrained, Xnp and e read."""
    op = asb.OperatingPoint(b.atmosphere, velocity=7.82, alpha=2.0)
    work = pathlib.Path(tempfile.mkdtemp(prefix="avl_kernel_reference_"))
    geometry = ba.write_avl_geometry(b, work, op)
    text = geometry.read_text()
    for name in ("bryan_profil.dat", "bryan_platte.dat"):
        text = text.replace(str(ba.BRYAN_DIR / name), str(repanelled(work, ba.BRYAN_DIR / name)))
    geometry.write_text(text)
    commands = ["oper", "o", "c", str(CORE_RATIO), "", f"a c {cl}", "x", "st", "", "", "quit"]
    out = subprocess.run(
        [str(avl_path()), str(geometry)],
        input="\n".join(commands) + "\n",
        capture_output=True,
        text=True,
        cwd=work,
        timeout=300,
        check=False,
    ).stdout
    return {key: ba._get(out, key) for key in ("e", "Xnp")}


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
            r = run(mesh, cl)
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
