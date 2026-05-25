"""Pure-numpy tests for the gh-727 adaptive-stations helpers.

These tests run in the CI **fast** tier (no ``requires_cadquery``
marker) — they don't actually call any OpenCASCADE / CadQuery API,
just the pure-Python curvature integration helpers introduced for
the OpenVSP-import pipeline.

OCC-touching tests live in ``test_slicer_shell_tolerant.py``
(requires_cadquery + requires_aerosandbox).
"""

from __future__ import annotations

import math

import numpy as np
import pytest

# These imports pull in cadquery + aerosandbox transitively, but only
# for type hints — the functions we exercise here are pure numpy.
pytest.importorskip("cadquery")
pytest.importorskip("aerosandbox")

from cad_designer.aerosandbox.slicing import (
    _curvature_density,
    adaptive_x_stations,
)


class TestAdaptiveXStations:
    def test_uniform_profile_gives_uniform_stations(self):
        top = [(float(x), 1.0) for x in np.linspace(0.0, 10.0, 21)]
        bot = [(float(x), -1.0) for x in np.linspace(0.0, 10.0, 21)]
        stations = adaptive_x_stations(top, bot, n_stations=11, curvature_weight=0.7)
        assert len(stations) == 11
        diffs = np.diff(stations)
        assert (diffs.max() - diffs.min()) / diffs.mean() < 0.05

    def test_localised_bump_clusters_stations_there(self):
        top = []
        for x in np.linspace(0.0, 10.0, 101):
            z = 1.0 + 2.0 * math.exp(-((x - 5.0) ** 2) / 0.2)
            top.append((float(x), float(z)))
        bot = [(float(x), -1.0) for x in np.linspace(0.0, 10.0, 101)]
        stations = adaptive_x_stations(top, bot, n_stations=20, curvature_weight=0.9)
        in_bump = sum(1 for s in stations if 3.0 < s < 7.0)
        assert in_bump >= 10

    def test_zero_curvature_weight_is_pure_uniform(self):
        top = []
        for x in np.linspace(0.0, 10.0, 101):
            z = 1.0 + 2.0 * math.exp(-((x - 5.0) ** 2) / 0.2)
            top.append((float(x), float(z)))
        bot = [(float(x), -1.0) for x in np.linspace(0.0, 10.0, 101)]
        stations = adaptive_x_stations(top, bot, n_stations=11, curvature_weight=0.0)
        diffs = np.diff(stations)
        assert (diffs.max() - diffs.min()) / diffs.mean() < 0.05

    def test_includes_x_bounds(self):
        top = [(float(x), 0.0) for x in np.linspace(0.0, 10.0, 21)]
        stations = adaptive_x_stations(top, [], n_stations=5)
        assert stations[0] == pytest.approx(0.0, abs=1e-9)
        assert stations[-1] == pytest.approx(10.0, abs=1e-9)

    def test_requires_minimum_stations(self):
        with pytest.raises(ValueError, match="n_stations"):
            adaptive_x_stations([(0, 0), (1, 0)], [], n_stations=1)

    def test_requires_at_least_one_outline(self):
        with pytest.raises(ValueError, match="outline"):
            adaptive_x_stations([], [], n_stations=5)

    def test_falls_back_to_uniform_with_no_curvature_samples(self):
        stations = adaptive_x_stations([(0, 0), (10, 0)], [], n_stations=5)
        assert len(stations) == 5
        assert stations[0] == pytest.approx(0.0)
        assert stations[-1] == pytest.approx(10.0)


class TestCurvatureDensity:
    def test_straight_line_has_zero_curvature(self):
        outline = [(float(x), 2.0 * float(x) + 1.0) for x in range(10)]
        xs, dz2 = _curvature_density(outline)
        assert len(dz2) == 8
        assert np.allclose(dz2, 0.0, atol=1e-9)

    def test_parabola_has_constant_curvature(self):
        outline = [(float(x), float(x) ** 2) for x in range(20)]
        _, dz2 = _curvature_density(outline)
        assert np.allclose(dz2, 2.0, atol=0.01)

    def test_too_short_returns_empty(self):
        xs, dz2 = _curvature_density([(0, 0), (1, 1)])
        assert len(xs) == 0
        assert len(dz2) == 0
