"""gh-1171: store BRYAN's spars as explicit plan axes (spare_mode "normal").

Maintainer decisions 2026-10-13: each spar follows its plan line exactly, through an explicit origin and
vector per segment instead of a chord fraction; in side view the main spar follows half profile depth
("Profilmitte"), as the built I-spar with flanges flush to the skin does.

  * main spar (index 0): plan line x = 136.75 mm, perpendicular, up to its end 1.86 mm into segment 12;
    pocket height = profile depth at the thinner segment end (flush).
  * auxiliary spar (index 1, aileron hinge stop, segments 0-5): plan line fitted through its stored
    positions; also at half depth, its stored height kept unless the profile is thinner there.

Each segment's origin is the axis point in the segment's root plane, absolute in the wing frame (metres),
which the DB/CAD path keeps unchanged (measured, see #1170). Station planes are built like the CAD does:
through the leading edge, normal = the outboard segment's direction in y/z, chord rotated by the twist.

    python bryan_spar_axes.py            # report only
    python bryan_spar_axes.py --apply    # rewrite bryan/bryan.airplane.json
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib

import numpy as np

HERE = pathlib.Path(__file__).parent / "bryan"
MAIN_X_MM = 136.75
# auxiliary spar plan line x = AUX_X0_MM + AUX_SLOPE * y (mm), fitted once through the positions stored
# before gh-1171 (chord fractions at the six segment roots, at most 0.08 mm off the line). Fixed here so a
# second run does not refit to its own output.
AUX_X0_MM, AUX_SLOPE = 208.288, -0.086216


def _airfoil() -> tuple[np.ndarray, np.ndarray]:
    pts = np.array(
        [
            [float(v) for v in line.split()]
            for line in (HERE / "bryan_profil.dat").read_text().splitlines()[1:]
            if len(line.split()) == 2
        ]
    )
    i = int(np.argmin(pts[:, 0]))
    upper, lower = pts[: i + 1][::-1], pts[i:]
    return upper[np.argsort(upper[:, 0])], lower[np.argsort(lower[:, 0])]


UPPER, LOWER = _airfoil()


def frame(xs: list, i: int) -> tuple:
    """(leading edge mm, chord dir, thickness dir, plane normal, chord mm) of station i."""
    j = min(i, len(xs) - 2)
    d = np.subtract(xs[j + 1]["xyz_le"], xs[j]["xyz_le"])
    g, t = math.atan2(d[2], d[1]), math.radians(xs[i]["twist"])
    chord_dir = np.array([math.cos(t), math.sin(t) * math.sin(g), -math.sin(t) * math.cos(g)])
    thick_dir = np.array([math.sin(t), -math.cos(t) * math.sin(g), math.cos(t) * math.cos(g)])
    normal = np.array([0.0, math.cos(g), math.sin(g)])
    return np.array(xs[i]["xyz_le"]) * 1000, chord_dir, thick_dir, normal, xs[i]["chord"] * 1000


def mid_point(f: tuple, x_world: float) -> tuple[np.ndarray, float, float]:
    """Point at half profile depth in station plane f whose x is x_world -> (point mm, depth mm, x/c)."""
    le, cd, td, _, c = f
    u = np.linspace(0.0, 1.0, 20001)
    zu, zl = np.interp(u, UPPER[:, 0], UPPER[:, 1]), np.interp(u, LOWER[:, 0], LOWER[:, 1])
    w = 0.5 * (zu + zl)
    xw = le[0] + c * (u * cd[0] + w * td[0])
    if not xw.min() <= x_world <= xw.max():
        raise ValueError(f"x {x_world:.2f} mm is outside the station at y {le[1]:.1f} mm")
    uu = float(np.interp(x_world, xw, u))
    ww = float(np.interp(uu, u, w))
    depth = (float(np.interp(uu, u, zu)) - float(np.interp(uu, u, zl))) * c
    return le + c * (uu * cd + ww * td), depth, uu


def _spar(
    old: dict, origin: np.ndarray, vec: np.ndarray, height_mm: float, u: float, length
) -> dict:
    return {
        "spare_support_dimension_width": old["spare_support_dimension_width"],
        "spare_support_dimension_height": round(height_mm / 1000, 6),
        "spare_position_factor": round(u, 4),
        "spare_length": length,
        "spare_start": 0.0,
        "spare_mode": "normal",
        "spare_vector": [round(float(c), 9) + 0.0 for c in vec],
        "spare_origin": [round(float(c) / 1000, 9) + 0.0 for c in origin],
    }


def _floor(h: float) -> float:
    return math.floor(h * 100) / 100


def _main_spar(xs: list) -> list[str]:
    segs = [i for i, x in enumerate(xs[:-1]) if x.get("spare_list")]
    pts = [mid_point(frame(xs, i), MAIN_X_MM) for i in range(segs[-1] + 2)]
    log = []
    for i in segs:
        old = xs[i]["spare_list"][0]
        (p0, d0, u0), (p1, d1, _) = pts[i], pts[i + 1]
        vec = (p1 - p0) / np.linalg.norm(p1 - p0)
        length = old["spare_length"]
        if length:  # the spar ends inside the segment: depth at its end, linear along the segment
            d1 = d0 + (d1 - d0) * min(1.0, length * 1000 / float(np.linalg.norm(p1 - p0)))
        h = _floor(min(d0, d1))
        log.append(
            f"  seg {i:2d}: x {p0[0]:.2f} z {p0[2]:7.2f} mm, Hoehe "
            f"{old['spare_support_dimension_height'] * 1000:.2f} -> {h:.2f} mm"
        )
        xs[i]["spare_list"][0] = _spar(old, p0, vec, h, u0, length)
    return log


def _aux_spar(xs: list) -> list[str]:
    segs = [i for i, x in enumerate(xs[:-1]) if len(x.get("spare_list") or []) > 1]
    slope, offset = AUX_SLOPE, AUX_X0_MM

    def on_line(i):
        f, y = frame(xs, i), frame(xs, i)[0][1]
        for _ in range(4):  # the mid-depth point's y drifts a little in a tilted plane
            p, d, u = mid_point(f, offset + slope * y)
            y = p[1]
        return p, d, u

    pts = {i: on_line(i) for i in segs + [segs[-1] + 1]}
    log = [f"  Linie x = {offset:.2f} + {slope:.5f} y (mm)"]
    for i in segs:
        old = xs[i]["spare_list"][1]
        (p0, d0, u0), (p1, d1, _) = pts[i], pts[i + 1]
        h_old = old["spare_support_dimension_height"] * 1000
        h = min(h_old, _floor(min(d0, d1)))
        log.append(
            f"  seg {i:2d}: x {p0[0]:.2f} z {p0[2]:7.2f} mm, Hoehe {h_old:.2f} -> {h:.2f} mm"
        )
        xs[i]["spare_list"][1] = _spar(
            old, p0, (p1 - p0) / np.linalg.norm(p1 - p0), h, u0, old["spare_length"]
        )
    return log


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apply", action="store_true", help="write bryan.airplane.json")
    a = ap.parse_args(argv)
    path = HERE / "bryan.airplane.json"
    text = path.read_text()
    geo = json.loads(text)
    second = text.splitlines()[1]
    indent = len(second) - len(second.lstrip(" ")) or None  # keep the file's own layout
    xs = geo["wings"]["Tragflaeche"]["x_secs"]
    print("Hauptholm (x = 136.75 mm, Profilmitte):")
    print("\n".join(_main_spar(xs)))
    print("Hilfsholm (Scharnieranschlag):")
    print("\n".join(_aux_spar(xs)))
    if a.apply:
        out = json.dumps(geo, indent=indent, ensure_ascii=False)
        path.write_text(out + "\n" if text.endswith("\n") else out)
        print(f"geschrieben: {path}")


if __name__ == "__main__":
    main()
