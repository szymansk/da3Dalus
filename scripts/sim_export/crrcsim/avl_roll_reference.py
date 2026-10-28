"""Steady roll of the reference fleet in AVL, from the geometry files alone (gh-1211).

    poetry run python scripts/sim_export/crrcsim/avl_roll_reference.py [--aircraft bryan jaguar]
        [--strips 24 48 96] [--cl 0.7] [--delta 20]

The independent reference the aero_kernel's AVL roll is tested against (aero_kernel/tests,
``test_solvers_avl_roll_real.py``). It imports nothing from ``aero_kernel``: it reads the fleet's JSON
documents and contour files itself, builds its own station set and writes its own ``.avl``. The
airplane is the wing, the horizontal tail and the fin (without the tails the roll is 3 - 6 % higher:
their damping matters). Conditions: Mach 0, no fuselage, C_L constrained, the
stability-axis rolling moment held at zero (``r rm 0``), the aileron command ``d1`` in degrees,
vortex core ratio 0.25, rotation about the airplane's reference point ``xyz_ref``.

Mesh (the expert's recipe, AVL guide rules 2 and 3):
  * the wing is split at the hinge line into a front and an aft SURFACE of one COMPONENT on the same
    stations, the aileron's CONTROL on the aft piece with its hinge at the aft leading edge;
  * the tails are single surfaces: the horizontal tail on the wing's stations inside its span plus its
    tip (a station within 0.3 strip widths of the tip is dropped), the fin on strips of the wing's
    width along z; ``CLAF`` and contour per surface;
  * the stations follow ONE sine-to-tip distribution ``y = (b/2) sin(pi/2 t)`` (``Sspace`` -2 from
    root to tip, ``avl_doc.txt:1043-1048``) with the aileron ends placed exactly: ``t`` of the ends is
    rounded to a strip count and runs evenly inside each of the three pieces, so the strip widths stay
    continuous (``avl_doc.txt:1100``). Uniform strips carry an O(1/N) tip error in the roll damping.

Reference values of the fleet (C_L 0.7, delta 20 deg, 24 / 48 / 96 strips per half span, chordwise
12 / 8, tails 10): BRYAN 0.28644 / 0.28625 / 0.28679, JAGUAR 0.27928 / 0.28042 / 0.28077
(the expert's resampling of the kernel's pre-split file gave 0.28657 / 0.28595 / 0.28624 and
0.27919 / 0.27990 / 0.27992). Clp and Cld01 still
move about 0.5 % each between 48 and 96 strips, in opposite directions: only the ratio is converged.

Every wing of the fleet has one airfoil and so one ``CLAF``; an aircraft that does not is refused,
not silently reduced to its first airfoil.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import re
import subprocess
import tempfile
from dataclasses import dataclass

import numpy as np
from avl_binary import avl_path

REFERENCE_DIR = pathlib.Path(__file__).resolve().parents[3] / "aero_kernel" / "reference"
FLEET = {"bryan": "bryan/bryan.airplane.json", "jaguar": "jaguar/flugzeug.json"}
ROLL_ROLES = ("aileron", "flaperon", "elevon")
CORE_RATIO = 0.25
CLAF_PER_THICKNESS = 0.77  # AVL's rule: 1 + 0.77 t/c
# AVL's fixed arrays (Avl/src/AVL.INC:22-24, amake.f:55)
MAX_STRIPS, MAX_VORTICES, MAX_CHORDWISE = 500, 6000, 50
MAX_CONTOUR_POINTS = 399
# a tail station closer to the tail tip than this many wing strip widths would leave a sliver strip
SLIVER_STEPS = 0.3
JOIN_TOLERANCE = 1e-6


@dataclass(frozen=True)
class Wing:
    """The oriented main wing: root first, y >= 0, the aileron as an absolute hinge line.

    Attributes:
        y, x, z, chord, twist: Per section, in metres and degrees.
        hinge_y, hinge_x: Knots of the absolute hinge line over the aileron span.
        contour: The contour file all sections share.
        xyz_ref: The reference point.
    """

    y: np.ndarray
    x: np.ndarray
    z: np.ndarray
    chord: np.ndarray
    twist: np.ndarray
    hinge_y: np.ndarray
    hinge_x: np.ndarray
    contour: pathlib.Path
    xyz_ref: tuple[float, float, float]


def load_wing(name: str) -> Wing:
    """Read the main wing of a fleet member and orient it root first on the positive side.

    Raises:
        ValueError: If the wing is not mirrored, uses more than one contour file, has an aileron
            with a missing hinge or a jump in its hinge line, or folds back along y.
    """
    path = REFERENCE_DIR / FLEET[name]
    document = json.loads(path.read_text())
    (key,) = [k for k, w in document["wings"].items() if w["surface_type"] == "main_wing"]
    wing = document["wings"][key]
    if not wing["symmetric"]:
        msg = "the reference needs a mirrored main wing"
        raise ValueError(msg)
    sections = wing["x_secs"]
    files = {pathlib.Path(s["airfoil"]).name for s in sections}
    if len(files) != 1:
        msg = f"the wing has {len(files)} contour files; this reference carries one CLAF per wing"
        raise ValueError(msg)
    sign = 1.0 if sum(s["xyz_le"][1] for s in sections) >= 0.0 else -1.0
    points = [
        (s["xyz_le"][0], sign * s["xyz_le"][1], s["xyz_le"][2], s["chord"], s["twist"])
        for s in sections
    ]
    # hinge line, absolute: the device on stored rib k covers the segment k -> k+1
    knots: list[tuple[float, float]] = []
    for index, section in enumerate(sections[:-1]):
        device = section.get("trailing_edge_device")
        if device is None or device["role"] not in ROLL_ROLES:
            continue
        root = device.get("rel_chord_root")
        if root is None:
            msg = "a roll device without a hinge position"
            raise ValueError(msg)
        tip = device.get("rel_chord_tip", root)
        tip = root if tip is None else tip
        a, b = points[index], points[index + 1]
        knots += [(a[1], a[0] + root * a[3]), (b[1], b[0] + tip * b[3])]
    order = sorted(range(len(points)), key=lambda i: points[i][1])
    if order != sorted(order, key=lambda i: points[i][1]) or any(
        points[i][1] > points[j][1] for i, j in zip(order, order[1:], strict=False)
    ):
        msg = "the sections fold back along y"
        raise ValueError(msg)
    ordered = np.array([points[i] for i in order])
    knots.sort()
    for (y_a, x_a), (y_b, x_b) in zip(knots, knots[1:], strict=False):
        if abs(y_a - y_b) < JOIN_TOLERANCE and abs(x_a - x_b) > JOIN_TOLERANCE:
            msg = f"the hinge line jumps at y = {y_a}"
            raise ValueError(msg)
    if not knots:
        msg = "the wing has no roll device"
        raise ValueError(msg)
    return Wing(
        y=ordered[:, 1],
        x=ordered[:, 0],
        z=ordered[:, 2],
        chord=ordered[:, 3],
        twist=ordered[:, 4],
        hinge_y=np.array([k[0] for k in knots]),
        hinge_x=np.array([k[1] for k in knots]),
        contour=path.parent / next(iter(files)),
        xyz_ref=tuple(document["xyz_ref"]),  # type: ignore[arg-type]
    )


@dataclass(frozen=True)
class Tail:
    """A tail surface oriented root first along its spreading axis (y for a mirrored tail, z for a fin).

    Attributes:
        along: The coordinate it spreads along (y or z), increasing.
        x, y, z, chord, twist: Per section.
        mirrored: Whether AVL mirrors it about y = 0.
        contour: Its contour file.
        name: Its name in the document.
    """

    along: np.ndarray
    x: np.ndarray
    y: np.ndarray
    z: np.ndarray
    chord: np.ndarray
    twist: np.ndarray
    mirrored: bool
    contour: pathlib.Path
    name: str


def load_tails(name: str) -> list[Tail]:
    """The surfaces other than the main wing, as the document gives them.

    Raises:
        ValueError: If a surface uses more than one contour file or folds back along its axis.
    """
    path = REFERENCE_DIR / FLEET[name]
    document = json.loads(path.read_text())
    tails = []
    for key, wing in sorted(document["wings"].items()):
        if wing["surface_type"] == "main_wing":
            continue
        sections = wing["x_secs"]
        files = {pathlib.Path(s["airfoil"]).name for s in sections}
        if len(files) != 1:
            msg = (
                f"{key} has {len(files)} contour files; this reference carries one CLAF per surface"
            )
            raise ValueError(msg)
        mirrored = bool(wing["symmetric"])
        sign = 1.0 if sum(s["xyz_le"][1] for s in sections) >= 0.0 else -1.0
        rows = np.array(
            [
                [
                    *s["xyz_le"][:1],
                    sign * s["xyz_le"][1] if mirrored else s["xyz_le"][1],
                    s["xyz_le"][2],
                ]
                + [s["chord"], s["twist"]]
                for s in sections
            ]
        )
        axis = 1 if mirrored else 2
        if rows[-1, axis] < rows[0, axis]:
            rows = rows[::-1]
        if np.any(np.diff(rows[:, axis]) < 0.0):
            msg = f"{key} folds back along its axis"
            raise ValueError(msg)
        tails.append(
            Tail(
                along=rows[:, axis],
                x=rows[:, 0],
                y=rows[:, 1],
                z=rows[:, 2],
                chord=rows[:, 3],
                twist=rows[:, 4],
                mirrored=mirrored,
                contour=path.parent / next(iter(files)),
                name=key,
            )
        )
    return tails


def claf_of(contour_file: pathlib.Path) -> float:
    """AVL's lift-curve-slope factor ``1 + 0.77 t/c`` of a contour file."""
    return 1.0 + CLAF_PER_THICKNESS * thickness_ratio(read_contour(contour_file))


def tail_text(
    tail: Tail, wing_stations: np.ndarray, strip: float, chordwise: int, index: int
) -> list[str]:
    """One tail surface of the file: stations on the wing's inside its span, or the wing's strip width."""
    root, tip = float(tail.along[0]), float(tail.along[-1])
    if tail.mirrored:
        inside = wing_stations[
            (wing_stations > root) & (wing_stations < tip - SLIVER_STEPS * strip)
        ]
        stations = np.array([root, *inside, tip])
    else:
        stations = np.linspace(root, tip, max(2, round((tip - root) / strip)) + 1)
    lines = ["SURFACE", tail.name, f"{chordwise} 1.0"]
    if tail.mirrored:
        lines += ["YDUPLICATE", "0.0"]
    for station in stations:
        x, y_le, z_le, chord, twist = (
            float(np.interp(station, tail.along, column))
            for column in (tail.x, tail.y, tail.z, tail.chord, tail.twist)
        )
        y, z = (float(station), z_le) if tail.mirrored else (y_le, float(station))
        lines += [
            "SECTION",
            f"{x!r} {y!r} {z!r} {chord!r} {twist!r} 1 1",
            "AFIL",
            f"tail{index}.dat",
            "CLAF",
            f"{claf_of(tail.contour)!r}",
        ]
    return lines


def read_contour(path: pathlib.Path) -> np.ndarray:
    """Selig contour, chord 1: the (x, y) pairs of the file."""
    rows = []
    for line in path.read_text().splitlines():
        fields = line.split()
        try:
            rows.append((float(fields[0]), float(fields[1])))
        except (ValueError, IndexError):
            continue  # the name line
    contour = np.array(rows)
    if len(contour) > MAX_CONTOUR_POINTS:
        msg = f"{path.name} has {len(contour)} points; AVL stops at {MAX_CONTOUR_POINTS}"
        raise ValueError(msg)
    return contour


def thickness_ratio(contour: np.ndarray) -> float:
    """Maximum thickness over chord: the upper and the lower side on a common x grid."""
    nose = int(np.argmin(contour[:, 0]))
    upper, lower = contour[: nose + 1][::-1], contour[nose:]
    grid = np.linspace(0.0, 1.0, 2001)
    gap = np.interp(grid, upper[:, 0], upper[:, 1]) - np.interp(grid, lower[:, 0], lower[:, 1])
    return float(np.max(np.abs(gap)))


def sine_to_tip_stations(tip: float, ends: tuple[float, float], strips: int) -> np.ndarray:
    """``strips + 1`` stations over [0, tip]: sine to tip, the aileron ends exact."""
    t_ends = [2.0 / math.pi * math.asin(y / tip) for y in ends]
    cuts = [0, *(round(strips * t) for t in t_ends), strips]
    edges = [0.0, *t_ends, 1.0]
    t_values = [0.0]
    for (low, high), (t_low, t_high) in zip(
        zip(cuts, cuts[1:], strict=False), zip(edges, edges[1:], strict=False), strict=True
    ):
        steps = max(high - low, 1)
        t_values += [t_low + (t_high - t_low) * i / steps for i in range(1, steps + 1)]
    return tip * np.sin(0.5 * math.pi * np.array(t_values))


def reference_values(wing: Wing) -> tuple[float, float, float]:
    """Sref, Cref (mean aerodynamic chord) and Bref of the wing continued to the centreline."""
    tip = float(wing.y[-1])
    grid = np.linspace(0.0, tip, 20001)
    chord = np.interp(grid, wing.y, wing.chord)
    area = 2.0 * float(np.trapezoid(chord, grid))
    mac = 2.0 * float(np.trapezoid(chord**2, grid)) / area
    return area, mac, 2.0 * tip


def avl_text(
    wing: Wing,
    stations: np.ndarray,
    chordwise: tuple[int, int],
    claf: float,
    tails: list[Tail],
    tail_chordwise: int,
) -> str:
    """The ``.avl`` file: the wing as a front and an aft surface of one component."""
    y_start, y_end = float(wing.hinge_y[0]), float(wing.hinge_y[-1])
    chord = np.interp(stations, wing.y, wing.chord)
    x_le = np.interp(stations, wing.y, wing.x)
    z_le = np.interp(stations, wing.y, wing.z)
    twist = np.interp(stations, wing.y, wing.twist)
    fraction = (np.interp(stations, wing.hinge_y, wing.hinge_x) - x_le) / chord
    on_device = (stations >= y_start - 1e-9) & (stations <= y_end + 1e-9)
    # off the device the cut is the hinge fraction of the nearer device end
    nearer = np.where(
        np.abs(stations - y_start) <= np.abs(stations - y_end),
        fraction[on_device][0],
        fraction[on_device][-1],
    )
    cut = np.where(on_device, fraction, nearer)
    area, mac, span = reference_values(wing)
    lines = [
        "reference roll",
        "0.0",
        "0 0 0.0",
        f"{area!r} {mac!r} {span!r}",
        " ".join(repr(float(v)) for v in wing.xyz_ref),
        "0.0",
    ]
    for name, count, aft in (("front", chordwise[0], False), ("aft", chordwise[1], True)):
        lines += ["SURFACE", f"wing {name}", f"{count} 1.0", "COMPONENT", "1", "YDUPLICATE", "0.0"]
        for k, y in enumerate(stations):
            c = float(cut[k])
            if aft:
                x, size, afil = float(x_le[k] + c * chord[k]), float((1.0 - c) * chord[k]), (c, 1.0)
            else:
                x, size, afil = float(x_le[k]), float(c * chord[k]), (0.0, c)
            lines += [
                "SECTION",
                f"{x!r} {float(y)!r} {float(z_le[k])!r} {size!r} {float(twist[k])!r} 1 1",
                f"AFIL {afil[0]!r} {afil[1]!r}",
                "contour.dat",
                "CLAF",
                f"{claf!r}",
            ]
            if aft and on_device[k]:
                lines += ["CONTROL", "aileron -1.0 0.0 0.0 0.0 0.0 -1"]
    strip = float(wing.y[-1]) / (len(stations) - 1)
    for index, tail in enumerate(tails):
        lines += tail_text(tail, stations, strip, tail_chordwise, index)
    return "\n".join(lines) + "\n"


def check_limits(text: str) -> None:
    """AVL's fixed arrays, counted on the file text: refuse before running (AVL fails silently)."""
    strips = vortices = 0
    for block in text.split("SURFACE\n")[1:]:
        lines = block.splitlines()
        chordwise = int(lines[1].split()[0])
        count = (block.count("SECTION\n") - 1) * (2 if "YDUPLICATE" in block else 1)
        strips += count
        vortices += count * chordwise
        if chordwise > MAX_CHORDWISE:
            msg = f"{chordwise} chordwise vortices on one surface (limit {MAX_CHORDWISE})"
            raise ValueError(msg)
    if strips > MAX_STRIPS or vortices > MAX_VORTICES:
        msg = f"{strips} strips and {vortices} vortices exceed AVL's arrays"
        raise ValueError(msg)


def trimmed_roll(
    wing: Wing,
    tails: list[Tail],
    strips: int,
    chordwise: tuple[int, int],
    cl: float,
    delta: float,
    tail_chordwise: int = 10,
) -> float:
    """``p'b/2V`` of the steady roll at ``cl`` and the aileron command ``delta`` in degrees."""
    contour = read_contour(wing.contour)
    claf = claf_of(wing.contour)
    ends = (float(wing.hinge_y[0]), float(wing.hinge_y[-1]))
    stations = sine_to_tip_stations(float(wing.y[-1]), ends, strips)
    commands = f"oper\no\nc\n{CORE_RATIO}\n\na c {cl!r}\nr rm 0\nd1 d1 {delta!r}\nx\n\nquit\n"
    with tempfile.TemporaryDirectory(prefix="avl_roll_reference_") as work:
        directory = pathlib.Path(work)
        (directory / "contour.dat").write_text(
            "contour\n" + "\n".join(f"{x:.8f} {y:.8f}" for x, y in contour) + "\n"
        )
        text = avl_text(wing, stations, chordwise, claf, tails, tail_chordwise)
        check_limits(text)
        for index, tail in enumerate(tails):
            (directory / f"tail{index}.dat").write_text(
                "contour\n"
                + "\n".join(f"{x:.8f} {y:.8f}" for x, y in read_contour(tail.contour))
                + "\n"
            )
        (directory / "roll.avl").write_text(text)
        output = subprocess.run(
            [str(avl_path()), "roll.avl"],
            input=commands,
            capture_output=True,
            text=True,
            cwd=directory,
            timeout=300,
            check=False,
        ).stdout
    if "overflow" in output.lower():
        msg = "AVL reported an array overflow"
        raise RuntimeError(msg)
    found = re.search(r"p'b/2V\s*=\s*(-?\d+\.\d*)", output)
    if found is None:
        msg = "AVL gave no steady roll"
        raise RuntimeError(msg)
    return float(found.group(1))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--aircraft", nargs="+", default=list(FLEET), choices=list(FLEET))
    parser.add_argument("--strips", nargs="+", type=int, default=[24, 48, 96])
    parser.add_argument("--cl", type=float, default=0.7)
    parser.add_argument("--delta", type=float, default=20.0)
    parser.add_argument("--chordwise", nargs=2, type=int, default=[12, 8], metavar=("FRONT", "AFT"))
    args = parser.parse_args(argv)
    for name in args.aircraft:
        wing, tails = load_wing(name), load_tails(name)
        values = [
            trimmed_roll(
                wing, tails, n, (args.chordwise[0], args.chordwise[1]), args.cl, args.delta
            )
            for n in args.strips
        ]
        print(
            name.upper(), " ".join(f"{n}:{v:.5f}" for n, v in zip(args.strips, values, strict=True))
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
