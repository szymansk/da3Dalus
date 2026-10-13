"""gh-1171: BRYAN's spars are stored as explicit plan axes (spare_mode "normal").

The main spar is straight in plan view at x = 136.75 mm up to its end, flush with the profile
(flanges glued to the skin, so the pocket is centred at half depth and as tall as the profile there).
The auxiliary spar (aileron hinge stop) is straight in plan view as well. The checks below rebuild the
station planes the way the CAD does (plane through the leading edge, normal = the outboard segment's
direction in y/z, chord rotated by the twist) without importing the CAD layer.
"""

from __future__ import annotations

import json
import math
import pathlib

import numpy as np
import pytest

_DIR = pathlib.Path(__file__).parents[2] / "scripts/canon_checks/reference_fleet/bryan"
MAIN_X_MM = 136.75


def _wing():
    d = json.loads((_DIR / "bryan.airplane.json").read_text())
    return d["wings"]["Tragflaeche"]["x_secs"]


def _airfoil():
    pts = np.array(
        [
            [float(v) for v in line.split()]
            for line in (_DIR / "bryan_profil.dat").read_text().splitlines()[1:]
            if len(line.split()) == 2
        ]
    )
    i = int(np.argmin(pts[:, 0]))
    upper, lower = pts[: i + 1][::-1], pts[i:]
    return upper[np.argsort(upper[:, 0])], lower[np.argsort(lower[:, 0])]


def _frame(xs, i):
    j = min(i, len(xs) - 2)
    d = np.subtract(xs[j + 1]["xyz_le"], xs[j]["xyz_le"])
    g, t = math.atan2(d[2], d[1]), math.radians(xs[i]["twist"])
    chord_dir = np.array([math.cos(t), math.sin(t) * math.sin(g), -math.sin(t) * math.cos(g)])
    thick_dir = np.array([math.sin(t), -math.cos(t) * math.sin(g), math.cos(t) * math.cos(g)])
    normal = np.array([0.0, math.cos(g), math.sin(g)])
    return np.array(xs[i]["xyz_le"]) * 1000, chord_dir, thick_dir, normal, xs[i]["chord"] * 1000


def _hit(origin, vec, frame):
    le, _, _, n, _ = frame
    return origin + float(np.dot(le - origin, n) / np.dot(vec, n)) * vec


def _depth(frame, p):
    """(upper clearance, lower clearance) of point p in its station plane, mm."""
    le, cd, td, _, c = frame
    upper, lower = _airfoil()
    u, w = float(np.dot(p - le, cd)) / c, float(np.dot(p - le, td)) / c
    return (
        (float(np.interp(u, upper[:, 0], upper[:, 1])) - w) * c,
        (w - float(np.interp(u, lower[:, 0], lower[:, 1]))) * c,
    )


def _axis(spar):
    return np.array(spar["spare_origin"]) * 1000, np.array(spar["spare_vector"])


def test_main_spar_is_the_plan_line_in_every_segment():
    xs = _wing()
    segs = [i for i, x in enumerate(xs[:-1]) if x.get("spare_list")]
    assert segs == list(range(13))
    for i in segs:
        spar = xs[i]["spare_list"][0]
        assert spar["spare_mode"] == "normal"
        o, v = _axis(spar)
        assert abs(np.linalg.norm(v) - 1) < 1e-6
        root, tip = _hit(o, v, _frame(xs, i)), _hit(o, v, _frame(xs, i + 1))
        assert np.linalg.norm(root - o) < 1e-3, i  # origin = root-plane crossing
        assert abs(root[0] - MAIN_X_MM) < 0.01 and abs(tip[0] - MAIN_X_MM) < 0.01, (i, root, tip)


def test_main_spar_pieces_meet_without_a_gap():
    xs = _wing()
    for i in range(12):
        o, v = _axis(xs[i]["spare_list"][0])
        o2, _ = _axis(xs[i + 1]["spare_list"][0])
        assert np.linalg.norm(_hit(o, v, _frame(xs, i + 1)) - o2) < 1e-3, i


def test_main_spar_is_flush_with_the_profile():
    """Half depth at both segment ends, and the pocket as tall as the thinner end (never taller)."""
    xs = _wing()
    for i in range(13):
        spar = xs[i]["spare_list"][0]
        o, v = _axis(spar)
        f0, f1 = _frame(xs, i), _frame(xs, i + 1)
        if spar["spare_length"]:  # the spar ends inside the segment: depth at its end
            end = o + v * spar["spare_length"] * 1000
            ends = [(f0, o), (None, end)]
        else:
            ends = [(f0, o), (f1, _hit(o, v, f1))]
        depths = []
        for f, p in ends:
            if f is None:  # the loft is linear between the two station sections along the axis
                tip = _hit(o, v, f1)
                t = float(np.dot(p - o, tip - o) / np.dot(tip - o, tip - o))
                a, b = _depth(f0, o), _depth(f1, tip)
                up, lo = a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])
            else:
                up, lo = _depth(f, p)
            assert abs(up - lo) < 0.05, (i, up, lo)
            depths.append(up + lo)
        h = spar["spare_support_dimension_height"] * 1000
        assert min(depths) - 0.02 <= h <= min(depths) + 1e-6, (i, h, depths)


def test_main_spar_keeps_its_end_on_segment_12():
    xs = _wing()
    assert xs[12]["spare_list"][0]["spare_length"] == pytest.approx(0.00186, abs=1e-5)
    assert all(xs[i]["spare_list"][0]["spare_length"] is None for i in range(12))


def test_auxiliary_spar_is_one_straight_line_in_plan_view():
    xs = _wing()
    pts = []
    for i in range(6):
        spar = xs[i]["spare_list"][1]
        assert spar["spare_mode"] == "normal"
        o, v = _axis(spar)
        for f in (_frame(xs, i), _frame(xs, i + 1)):
            p = _hit(o, v, f)
            pts.append((p[1], p[0]))
            up, lo = _depth(f, p)
            assert min(up, lo) > spar["spare_support_dimension_height"] * 1000 / 2 - 1e-6, (
                i,
                up,
                lo,
            )
    p = np.array(pts)
    fit = np.polyval(np.polyfit(p[:, 0], p[:, 1], 1), p[:, 0])
    assert np.max(np.abs(p[:, 1] - fit)) < 0.01
    assert all(len(x.get("spare_list") or []) == 1 for x in xs[6:13])
