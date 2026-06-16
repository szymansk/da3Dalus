"""Tests for the APC PROP-DATA xlsx loader (gh-1000).

Runs against a small committed xlsx fixture (no network, no large file).
Verifies designation parsing, oz→g weight normalisation and skipping of
unparseable rows.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts.parse_apc_xlsx import OZ_TO_G, parse_apc_xlsx

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "apc_pe0" / "PROP-DATA-SAMPLE.xlsx"


@pytest.fixture(scope="module")
def props():
    return parse_apc_xlsx(FIXTURE)


class TestXlsxParsing:
    def test_skips_unparseable_rows(self, props):
        # 2 valid props, the GARBAGE ROW is skipped.
        assert len(props) == 2

    def test_plain_designation(self, props):
        p = next(p for p in props if p.diameter_in == 11.0)
        assert p.pitch_in == 6.0
        assert p.variant == ""

    def test_variant_designation(self, props):
        p = next(p for p in props if p.variant == "E")
        assert p.diameter_in == 10.5
        assert p.pitch_in == 4.5

    def test_weight_oz_to_grams(self, props):
        p = next(p for p in props if p.diameter_in == 11.0)
        # 1.53 oz → ~43.4 g
        assert p.weight_g == pytest.approx(1.53 * OZ_TO_G, abs=1e-3)

    def test_weight_is_grams_not_oz(self, props):
        p = next(p for p in props if p.diameter_in == 11.0)
        assert p.weight_g > 5.0  # not left in ounces
