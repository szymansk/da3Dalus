"""Tests for PE0 → PER3 enrichment matching (gh-1000).

Matches PE0 weight/inertia/geometry to existing PER3 snapshot records by
diameter × pitch × variant, guarding units and flagging unmatched rows.
"""

from __future__ import annotations

import sys
from pathlib import Path

from scripts.parse_apc_pe0 import ParsedPe0

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from app.services.prop_polar_enrich import EnrichResult, enrich_records_with_pe0


def _pe0(dia: float, pitch: float, variant: str = "", *, weight_g=43.3, blades=2) -> ParsedPe0:
    return ParsedPe0(
        diameter_in=dia,
        pitch_in=pitch,
        variant=variant,
        blades=blades,
        weight_g=weight_g,
        inertia_kg_m2=0.000124,
        source_version="v2025-1001",
        geometry=[{"station_in": 0.0, "chord_in": 1.0}],
    )


def _record(name: str, dia: float, pitch: float, variant: str = "", blades: int = 2) -> dict:
    return {
        "manufacturer": "APC",
        "name": name,
        "component_type": "propeller",
        "model_ref": f"apc/{name.split()[-1]}",
        "specs": {"diameter_in": dia, "pitch_in": pitch, "variant": variant, "blades": blades},
        "polars": [],
    }


class TestMatching:
    def test_matches_by_dia_pitch_variant(self):
        records = [_record("APC 11x6", 11.0, 6.0, "")]
        result = enrich_records_with_pe0(records, [_pe0(11.0, 6.0, "")])
        assert isinstance(result, EnrichResult)
        assert result.matched == 1
        assert result.unmatched_pe0 == 0
        specs = records[0]["specs"]
        assert specs["weight_g"] == 43.3
        assert specs["inertia_kg_m2"] == 0.000124
        assert records[0]["geometry"][0]["chord_in"] == 1.0

    def test_variant_disambiguates(self):
        records = [
            _record("APC 9x6", 9.0, 6.0, ""),
            _record("APC 9x6-4", 9.0, 6.0, "-4", blades=4),
        ]
        result = enrich_records_with_pe0(
            records,
            [_pe0(9.0, 6.0, "-4", weight_g=60.0, blades=4)],
        )
        assert result.matched == 1
        assert records[0]["specs"].get("weight_g") is None  # plain 9x6 untouched
        assert records[1]["specs"]["weight_g"] == 60.0

    def test_unmatched_pe0_is_flagged_not_silent(self):
        records = [_record("APC 11x6", 11.0, 6.0, "")]
        result = enrich_records_with_pe0(records, [_pe0(99.0, 99.0, "")])
        assert result.matched == 0
        assert result.unmatched_pe0 == 1
        assert any("99x99" in u or "99" in u for u in result.unmatched_names)


class TestUnitGuard:
    def test_rejects_weight_in_kg_range(self):
        """A weight that looks like kg (<5 g for a real prop is implausible);
        the guard rejects sub-gram weights as a likely unit error."""
        records = [_record("APC 11x6", 11.0, 6.0, "")]
        bad = _pe0(11.0, 6.0, "", weight_g=0.043)  # forgot kg→g
        result = enrich_records_with_pe0(records, [bad])
        assert records[0]["specs"].get("weight_g") is None
        assert result.unit_warnings == 1
