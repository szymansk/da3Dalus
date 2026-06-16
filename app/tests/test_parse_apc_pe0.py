"""Tests for the APC PE0 parser (gh-1000).

PE0 files carry per-prop weight, moment of inertia, blade count and
per-station blade geometry — data absent from the PER3 polars. Tests run
against committed fixtures (no network, no archive extraction).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts.parse_apc_pe0 import ParsedPe0, parse_pe0_file

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "apc_pe0"


@pytest.fixture(scope="module")
def pe0_11x6() -> ParsedPe0:
    return parse_pe0_file(FIXTURES / "11x6-PERF.PE0")


@pytest.fixture(scope="module")
def pe0_9x6_4() -> ParsedPe0:
    return parse_pe0_file(FIXTURES / "9x6-4-PERF.PE0")


class TestPe0Designation:
    def test_diameter_pitch_variant(self, pe0_11x6: ParsedPe0):
        assert pe0_11x6.diameter_in == 11.0
        assert pe0_11x6.pitch_in == 6.0
        assert pe0_11x6.variant == ""

    def test_four_blade_designation(self, pe0_9x6_4: ParsedPe0):
        assert pe0_9x6_4.diameter_in == 9.0
        assert pe0_9x6_4.pitch_in == 6.0
        assert pe0_9x6_4.variant == "-4"


class TestPe0Blades:
    def test_two_blade(self, pe0_11x6: ParsedPe0):
        assert pe0_11x6.blades == 2

    def test_four_blade(self, pe0_9x6_4: ParsedPe0):
        assert pe0_9x6_4.blades == 4


class TestPe0WeightInertia:
    def test_weight_grams(self, pe0_11x6: ParsedPe0):
        # PE0 says TOTAL WEIGHT (Kg) = 0.043299 → 43.299 g
        assert pe0_11x6.weight_g == pytest.approx(43.299, abs=1e-2)

    def test_weight_is_grams_not_kg(self, pe0_11x6: ParsedPe0):
        # Unit guard: must NOT leave it in kg.
        assert pe0_11x6.weight_g > 1.0

    def test_inertia_kg_m2(self, pe0_11x6: ParsedPe0):
        # MOMENT OF INERTIA (Kg-M**2) = 0.000124
        assert pe0_11x6.inertia_kg_m2 == pytest.approx(0.000124, abs=1e-6)


class TestPe0Geometry:
    def test_geometry_is_list_of_stations(self, pe0_11x6: ParsedPe0):
        assert isinstance(pe0_11x6.geometry, list)
        assert len(pe0_11x6.geometry) > 10

    def test_station_fields(self, pe0_11x6: ParsedPe0):
        first = pe0_11x6.geometry[0]
        assert "station_in" in first
        assert "chord_in" in first
        # First station chord is 1.0 in for 11x6.
        assert first["chord_in"] == pytest.approx(1.0, abs=1e-3)


class TestPe0SourceVersion:
    def test_source_version_captured(self, pe0_11x6: ParsedPe0):
        assert pe0_11x6.source_version == "v2025-1001"
