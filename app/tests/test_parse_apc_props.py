"""Tests for scripts/parse_apc_props.py — APC PER3 .dat parser (gh-995).

All tests run offline against committed fixture .dat files.
No network access required.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Allow importing from scripts/
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "apc_props"


# ──────────────────────────────────────────────────────────────────────────────
# Import the module under test (after sys.path tweak above)
# ──────────────────────────────────────────────────────────────────────────────

from scripts.parse_apc_props import (  # noqa: E402
    ParsedPropFile,
    RpmBlock,
    parse_apc_dat_file,
    parse_filename,
    build_snapshot_record,
)


# ──────────────────────────────────────────────────────────────────────────────
# parse_filename
# ──────────────────────────────────────────────────────────────────────────────


class TestParseFilename:
    def test_7x4(self):
        dia, pitch = parse_filename("PER3_7x4.dat")
        assert dia == 7.0
        assert pitch == 4.0

    def test_9x6(self):
        dia, pitch = parse_filename("PER3_9x6.dat")
        assert dia == 9.0
        assert pitch == 6.0

    def test_12x8(self):
        dia, pitch = parse_filename("PER3_12x8.dat")
        assert dia == 12.0
        assert pitch == 8.0

    def test_invalid_returns_none(self):
        result = parse_filename("not_an_apc_file.txt")
        assert result is None

    def test_fractional_pitch(self):
        # APC uses decimal: PER3_9x4.5.dat → 9.0, 4.5
        dia, pitch = parse_filename("PER3_9x4.5.dat")
        assert dia == 9.0
        assert pitch == 4.5


# ──────────────────────────────────────────────────────────────────────────────
# parse_apc_dat_file — fixture: 7x4
# ──────────────────────────────────────────────────────────────────────────────


class TestParseApcDatFile7x4:
    @pytest.fixture(autouse=True)
    def parsed(self):
        path = FIXTURES_DIR / "PER3_7x4.dat"
        self.result = parse_apc_dat_file(path)

    def test_returns_parsed_prop_file(self):
        assert isinstance(self.result, ParsedPropFile)

    def test_diameter_and_pitch(self):
        assert self.result.diameter_in == 7.0
        assert self.result.pitch_in == 4.0

    def test_two_rpm_blocks(self):
        assert len(self.result.rpm_blocks) == 2

    def test_rpm_block_1000(self):
        block = self.result.rpm_blocks[0]
        assert block.rpm == 1000

    def test_rpm_block_5000(self):
        block = self.result.rpm_blocks[1]
        assert block.rpm == 5000

    def test_rpm_1000_has_samples(self):
        block = self.result.rpm_blocks[0]
        assert len(block.samples) > 5

    def test_rpm_1000_first_sample_J_zero(self):
        """At J=0 (static), thrust > 0 and Pe = 0."""
        block = self.result.rpm_blocks[0]
        first = block.samples[0]
        assert first["J"] == pytest.approx(0.0, abs=1e-4)
        assert first["Pe"] == pytest.approx(0.0, abs=1e-4)

    def test_rpm_1000_Ct_at_J_zero_physical(self):
        """Ct at J=0 for 7x4 at 1000rpm should be around 0.10-0.13."""
        block = self.result.rpm_blocks[0]
        first = block.samples[0]
        assert 0.08 < first["Ct"] < 0.15

    def test_rpm_1000_Cp_at_J_zero_physical(self):
        """Cp at J=0 for 7x4 should be positive and < 0.15."""
        block = self.result.rpm_blocks[0]
        first = block.samples[0]
        assert 0.0 < first["Cp"] < 0.15

    def test_sample_fields_present(self):
        """Every sample must have J, Pe, Ct, Cp, PWR_W, Torque_Nm, Thrust_N."""
        for block in self.result.rpm_blocks:
            for s in block.samples:
                for field in ("J", "Pe", "Ct", "Cp", "PWR_W", "Torque_Nm", "Thrust_N"):
                    assert field in s, f"Missing field '{field}' in sample"

    def test_J_monotonically_increasing(self):
        """Advance ratio must increase through the block (the prop stalls beyond J_max)."""
        for block in self.result.rpm_blocks:
            js = [s["J"] for s in block.samples]
            assert js == sorted(js), f"J not sorted in RPM {block.rpm} block"

    def test_efficiency_in_thrust_region(self):
        """In the thrust-producing region the fixtures cover (J up to ~0.7),
        propulsive efficiency Pe stays in [0, 1]. NOTE: real APC data at high J
        (past the thrust-producing region) legitimately has Pe < 0 — the prop
        windmills/brakes — so this bound holds for the fixtures, not universally."""
        for block in self.result.rpm_blocks:
            for s in block.samples:
                if s["J"] > 0.01:  # skip near-static where Pe is near 0
                    assert 0.0 <= s["Pe"] <= 1.0, f"Pe={s['Pe']} out of range at J={s['J']}"


# ──────────────────────────────────────────────────────────────────────────────
# parse_apc_dat_file — fixture: 9x6
# ──────────────────────────────────────────────────────────────────────────────


class TestParseApcDatFile9x6:
    @pytest.fixture(autouse=True)
    def parsed(self):
        path = FIXTURES_DIR / "PER3_9x6.dat"
        self.result = parse_apc_dat_file(path)

    def test_diameter(self):
        assert self.result.diameter_in == 9.0

    def test_pitch(self):
        assert self.result.pitch_in == 6.0

    def test_rpm_blocks(self):
        assert len(self.result.rpm_blocks) == 2
        rpms = {b.rpm for b in self.result.rpm_blocks}
        assert 3000 in rpms
        assert 5000 in rpms

    def test_ct_at_3000rpm_static(self):
        """At 3000 rpm, J=0: Ct for 9x6 should be around 0.12-0.14."""
        block = next(b for b in self.result.rpm_blocks if b.rpm == 3000)
        first = block.samples[0]
        assert 0.10 < first["Ct"] < 0.16

    def test_pwr_W_positive_at_3000rpm(self):
        block = next(b for b in self.result.rpm_blocks if b.rpm == 3000)
        first = block.samples[0]
        assert first["PWR_W"] > 0.0

    def test_thrust_N_positive_at_3000rpm(self):
        block = next(b for b in self.result.rpm_blocks if b.rpm == 3000)
        first = block.samples[0]
        assert first["Thrust_N"] > 0.0


# ──────────────────────────────────────────────────────────────────────────────
# parse_apc_dat_file — fixture: 12x6
# ──────────────────────────────────────────────────────────────────────────────


class TestParseApcDatFile12x6:
    @pytest.fixture(autouse=True)
    def parsed(self):
        path = FIXTURES_DIR / "PER3_12x6.dat"
        self.result = parse_apc_dat_file(path)

    def test_diameter(self):
        assert self.result.diameter_in == 12.0

    def test_pitch(self):
        assert self.result.pitch_in == 6.0

    def test_rpm_blocks_count(self):
        assert len(self.result.rpm_blocks) == 2

    def test_source_version_captured(self):
        """Source version string (v2022-...) should be extracted from header."""
        assert self.result.source_version is not None
        assert "2022" in self.result.source_version


# ──────────────────────────────────────────────────────────────────────────────
# build_snapshot_record
# ──────────────────────────────────────────────────────────────────────────────


class TestBuildSnapshotRecord:
    @pytest.fixture(autouse=True)
    def setup(self):
        path = FIXTURES_DIR / "PER3_9x6.dat"
        parsed = parse_apc_dat_file(path)
        self.record = build_snapshot_record(parsed, path.name)

    def test_manufacturer(self):
        assert self.record["manufacturer"] == "APC"

    def test_component_type(self):
        assert self.record["component_type"] == "propeller"

    def test_name_format(self):
        assert self.record["name"] == "APC 9x6"

    def test_specs_diameter(self):
        assert self.record["specs"]["diameter_in"] == 9.0

    def test_specs_pitch(self):
        assert self.record["specs"]["pitch_in"] == 6.0

    def test_specs_blades(self):
        assert self.record["specs"]["blades"] == 2

    def test_polars_present(self):
        assert "polars" in self.record
        assert isinstance(self.record["polars"], list)
        assert len(self.record["polars"]) == 2  # 2 RPM blocks in fixture

    def test_polar_rpm_field(self):
        polar = self.record["polars"][0]
        assert "rpm" in polar
        assert polar["rpm"] in (3000, 5000)

    def test_polar_samples_field(self):
        polar = self.record["polars"][0]
        assert "samples" in polar
        assert len(polar["samples"]) > 0

    def test_polar_sample_fields(self):
        sample = self.record["polars"][0]["samples"][0]
        for field in ("J", "Ct", "Cp", "Pe", "PWR_W", "Torque_Nm", "Thrust_N"):
            assert field in sample

    def test_source_url(self):
        assert "apcprop.com" in self.record.get("source_url", "")

    def test_model_ref(self):
        assert "apc" in self.record.get("model_ref", "").lower()


# ──────────────────────────────────────────────────────────────────────────────
# parse_all (batch, uses all fixture files)
# ──────────────────────────────────────────────────────────────────────────────


class TestParseAll:
    def test_parse_all_three_fixtures(self, tmp_path):
        """parse_all() should return one record per fixture file."""
        import shutil

        from scripts.parse_apc_props import parse_all, write_snapshot

        # Copy the 3 fixture .dat files to a temp raw dir
        for fname in ("PER3_7x4.dat", "PER3_9x6.dat", "PER3_12x6.dat"):
            shutil.copy(FIXTURES_DIR / fname, tmp_path / fname)

        records, fetched, skipped = parse_all(raw_dir=tmp_path)

        assert len(records) == 3
        assert len(fetched) == 3
        assert skipped == []

        names = {r["name"] for r in records}
        assert "APC 7x4" in names
        assert "APC 9x6" in names
        assert "APC 12x6" in names

    def test_empty_file_skipped(self, tmp_path):
        """Zero-byte files in raw dir are skipped, not crash."""
        from scripts.parse_apc_props import parse_all

        (tmp_path / "PER3_99x99.dat").write_bytes(b"")

        records, fetched, skipped = parse_all(raw_dir=tmp_path)
        assert len(records) == 0
        assert "PER3_99x99.dat" in skipped

    def test_write_snapshot_roundtrip(self, tmp_path):
        """write_snapshot writes valid JSON; reload equals original records."""
        import json
        import shutil

        from scripts.parse_apc_props import parse_all, write_snapshot

        shutil.copy(FIXTURES_DIR / "PER3_9x6.dat", tmp_path / "PER3_9x6.dat")

        records, _, _ = parse_all(raw_dir=tmp_path)
        out = tmp_path / "apc_props.json"
        write_snapshot(records, output_path=out)

        reloaded = json.loads(out.read_text())
        assert len(reloaded) == 1
        assert reloaded[0]["name"] == "APC 9x6"
        assert reloaded[0]["polars"][0]["samples"][0]["J"] == pytest.approx(0.0, abs=1e-4)

    def test_missing_dir_returns_empty(self, tmp_path):
        """Calling parse_all on a non-existent directory returns ([], [], [])."""
        from scripts.parse_apc_props import parse_all

        non_existent = tmp_path / "no_such_dir"
        records, fetched, skipped = parse_all(raw_dir=non_existent)
        assert records == []
        assert fetched == []
        assert skipped == []


# ──────────────────────────────────────────────────────────────────────────────
# Committed snapshot validity (gh-986 spec §9: validate the committed snapshot)
# ──────────────────────────────────────────────────────────────────────────────


class TestCommittedSnapshot:
    def test_committed_snapshot_is_valid(self):
        """The committed data/cots/apc_props.json must stay importable: every
        record passes validation and carries at least one polar sample."""
        import json

        from app.services.prop_polar_import import _validate_prop_record

        data = json.loads((REPO_ROOT / "data" / "cots" / "apc_props.json").read_text())
        assert len(data) == 22
        for record in data:
            assert _validate_prop_record(record) is None, record.get("name")
            assert len(record["polars"]) > 0
