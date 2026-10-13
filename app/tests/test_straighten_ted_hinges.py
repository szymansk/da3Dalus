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
    assert changes[0]["new"] == (round(0.10 / 0.15, 4), round(0.08 / 0.12, 4))


def _fin_leaving_the_trailing_edge():
    # hinge x = 0.50 on every section; the tip (te 0.49) lies ahead of it, so the
    # straight hinge leaves the outline inside the last segment (te 0.53 -> 0.49)
    xs = [
        _xsec(0.0, 0.40, 0.15, z=0.00),
        _xsec(0.0, 0.42, 0.12, z=0.05),
        _xsec(0.0, 0.44, 0.09, z=0.10),
        _xsec(0.0, 0.46, 0.03, z=0.12),
    ]
    xs[2]["x_sec_type"], xs[2]["tip_type"] = "tip", "round"
    rels = [(0.10 / 0.15, 0.08 / 0.12), (0.08 / 0.12, 0.06 / 0.09), (0.06 / 0.09, 1.0)]
    for i, (r, t) in enumerate(rels):
        xs[i]["trailing_edge_device"] = {
            "name": "Seitenruder",
            "rel_chord_root": r,
            "rel_chord_tip": t,
        }
        xs[i]["control_surface"] = {"name": "Seitenruder", "hinge_point": r}
    xs[2]["spare_list"] = [{"spare_position_factor": 0.3, "spare_mode": "standard"}]
    return xs


def test_rudder_ends_where_the_straight_hinge_leaves_the_outline():
    xs = _fin_leaving_the_trailing_edge()

    new, report = tool.rebuild(xs)

    # te x = 0.53 - 0.04*(t) along the last segment hits x = 0.50 at t = 0.75 -> z = 0.115
    assert len(new) == 5
    cut = new[3]
    assert cut["xyz_le"][2] == pytest.approx(0.115)
    assert cut["xyz_le"][0] + cut["chord"] == pytest.approx(0.50)
    # the new section lies on the old outline: LE and TE interpolate linearly
    assert cut["xyz_le"][0] == pytest.approx(0.455)
    assert "trailing_edge_device" not in cut and "control_surface" not in cut
    assert new[2]["trailing_edge_device"]["rel_chord_tip"] == 1.0
    assert new[2]["trailing_edge_device"]["rel_chord_root"] == round(0.06 / 0.09, 4)
    # the tip classification moves to the outermost real segment
    assert (cut["x_sec_type"], cut["tip_type"]) == ("tip", "round")
    assert new[2].get("x_sec_type") == "segment" and new[2].get("tip_type") is None
    # a spar in the split segment continues on the same line in the new segment
    assert cut["spare_list"] == [{"spare_position_factor": 0.3, "spare_mode": "follow"}]
    assert report["inserted"] == [3]
    # every stored hinge point now lies on the straight line x = 0.50
    for i in range(3):
        ted = new[i]["trailing_edge_device"]
        for x, rel in ((new[i], ted["rel_chord_root"]), (new[i + 1], ted["rel_chord_tip"])):
            assert _hinge(x, rel) == pytest.approx(0.50, abs=1e-5)
    assert xs[2]["trailing_edge_device"]["rel_chord_tip"] == 1.0  # input left untouched


def test_full_chord_rudder_below_the_hinge_keeps_zero_and_is_not_cut():
    # lower fin part: the hinge line runs 0.4 mm ahead of the leading edge, so the
    # whole section moves (fraction 0) - that is a rudder, not a missing one
    xs = [
        _xsec(0.0, 0.4684, 0.03, z=-0.02),
        _xsec(0.0, 0.4684, 0.04, z=-0.01),
        _xsec(0.0, 0.4400, 0.10, z=0.03),
        _xsec(0.0, 0.4500, 0.06, z=0.06),
    ]
    for i, (r, t) in enumerate([(0.0, 0.0), (0.0, 0.28), (0.28, 0.3)]):
        xs[i]["trailing_edge_device"] = {
            "name": "Seitenruder",
            "rel_chord_root": r,
            "rel_chord_tip": t,
        }

    new, report = tool.rebuild(xs)

    assert len(new) == 4 and report["inserted"] == []
    assert new[0]["trailing_edge_device"]["rel_chord_root"] == 0.0
    assert all("trailing_edge_device" in new[i] for i in range(3))


def test_hinge_leaving_the_outline_mid_run_is_refused():
    xs = [
        _xsec(0.0, 0.40, 0.15, z=0.00),
        _xsec(0.0, 0.46, 0.03, z=0.05),
        _xsec(0.0, 0.40, 0.15, z=0.10),
    ]
    for i in range(2):
        xs[i]["trailing_edge_device"] = {
            "name": "Seitenruder",
            "rel_chord_root": 0.66,
            "rel_chord_tip": 0.66,
        }
    xs[0]["trailing_edge_device"]["rel_chord_tip"] = 1.0
    xs[1]["trailing_edge_device"]["rel_chord_root"] = 1.0

    with pytest.raises(ValueError, match="Seitenruder"):
        tool.rebuild(xs)


def test_surfaces_without_ted_are_left_alone():
    xs = [_xsec(0.0, 0.0, 0.2), _xsec(0.5, 0.0, 0.2)]
    assert tool.straighten(xs) == []


def test_rebuild_is_idempotent_on_its_own_output():
    new, _ = tool.rebuild(_fin_leaving_the_trailing_edge())

    again, report = tool.rebuild(new)

    assert report["inserted"] == [] and report["removed"] == []
    assert len(again) == len(new)
    assert again[3]["xyz_le"] == new[3]["xyz_le"]
