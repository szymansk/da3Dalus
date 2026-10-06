"""gh-1163: the reference-fleet tool that puts each TED on one straight hinge line."""

from __future__ import annotations

import importlib.util
import math
import pathlib

import numpy as np
import pytest

_PATH = (
    pathlib.Path(__file__).parents[2]
    / "scripts/canon_checks/reference_fleet/straighten_ted_hinges.py"
)
_spec = importlib.util.spec_from_file_location("straighten_ted_hinges", _PATH)
tool = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tool)


def _xsec(y, x_le, chord, ted=None, z=0.0, twist=0.0):
    x = {"xyz_le": [x_le, y, z], "chord": chord, "twist": twist}
    if ted:
        x["trailing_edge_device"] = ted
    return x


def _hinge(x, rel):
    return x["xyz_le"][0] + rel * x["chord"] * math.cos(math.radians(x["twist"]))


def _apply(x_secs, changes):
    for c in changes:
        ted = x_secs[c["index"]]["trailing_edge_device"]
        ted["rel_chord_root"], ted["rel_chord_tip"] = c["new"]


def test_kinked_aileron_lands_on_one_line_and_agrees_at_shared_sections():
    # swept hinge x = 0.15 + 0.02*y, stored with +-0.4 mm noise and mismatching shared values
    xs = [
        _xsec(0.0, 0.00, 0.20, twist=2.0),
        _xsec(0.2, 0.01, 0.18, twist=2.0),
        _xsec(0.4, 0.02, 0.16, twist=2.0),
        _xsec(0.6, 0.03, 0.14, twist=2.0),
    ]
    for i in range(3):
        a, b = xs[i], xs[i + 1]
        root = (0.15 + 0.02 * a["xyz_le"][1] - a["xyz_le"][0] + 0.0004) / (
            a["chord"] * math.cos(math.radians(2))
        )
        tip = (0.15 + 0.02 * b["xyz_le"][1] - b["xyz_le"][0] - 0.0004) / (
            b["chord"] * math.cos(math.radians(2))
        )
        a["trailing_edge_device"] = {
            "name": "Querruder",
            "rel_chord_root": root,
            "rel_chord_tip": tip,
        }

    changes = tool.straighten(xs)
    _apply(xs, changes)

    assert [c["index"] for c in changes] == [0, 1, 2]
    pts = []
    for i in range(3):
        ted = xs[i]["trailing_edge_device"]
        for x, rel in ((xs[i], ted["rel_chord_root"]), (xs[i + 1], ted["rel_chord_tip"])):
            pts.append((x["xyz_le"][1], _hinge(x, rel)))
        if i:
            assert ted["rel_chord_root"] == xs[i - 1]["trailing_edge_device"]["rel_chord_tip"]
    # all hinge points on one straight line (up to the 4-decimal rounding of the fractions)
    p = np.array(pts)
    fit = np.polyval(np.polyfit(p[:, 0], p[:, 1], 1), p[:, 0])
    assert np.max(np.abs(p[:, 1] - fit)) < 2e-5
    assert changes[0]["line_error_mm"] > 0.3


def test_edge_clamps_do_not_pull_the_line_on_a_vertical_surface():
    # fin: span along z, hinge at x = 0.50; the tip section is shorter than the hinge
    # position, so its stored fraction is clamped to 1.0
    xs = [
        _xsec(0.0, 0.40, 0.15, z=0.00),
        _xsec(0.0, 0.42, 0.12, z=0.05),
        _xsec(0.0, 0.44, 0.09, z=0.10),
        _xsec(0.0, 0.46, 0.03, z=0.12),
    ]
    rels = [(0.10 / 0.15, 0.08 / 0.12), (0.08 / 0.12, 0.06 / 0.09), (0.06 / 0.09, 1.0)]
    for i, (r, t) in enumerate(rels):
        xs[i]["trailing_edge_device"] = {
            "name": "Seitenruder",
            "rel_chord_root": r,
            "rel_chord_tip": t,
        }

    changes = tool.straighten(xs)

    assert changes[0]["line_error_mm"] == pytest.approx(0.0, abs=1e-6)
    assert changes[2]["new"] == (round(0.06 / 0.09, 4), 1.0)
    assert changes[2]["clamped"] is True
    assert changes[0]["new"] == (round(0.10 / 0.15, 4), round(0.08 / 0.12, 4))


def test_surfaces_without_ted_are_left_alone():
    xs = [_xsec(0.0, 0.0, 0.2), _xsec(0.5, 0.0, 0.2)]
    assert tool.straighten(xs) == []
