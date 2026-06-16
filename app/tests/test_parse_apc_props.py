"""Tests for scripts/parse_apc_props.py — APC PER3 .dat parser (gh-995, gh-999).

All tests run offline against committed fixture .dat files.
No network access required.
"""

from __future__ import annotations

import gzip
import json
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
    build_snapshot_record,
    derive_blades,
    parse_apc_dat_file,
    parse_filename,
    parse_header_designation,
)


# ──────────────────────────────────────────────────────────────────────────────
# parse_filename (legacy fallback — still supported)
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
# parse_header_designation — NEW header-based parser (gh-999)
# ──────────────────────────────────────────────────────────────────────────────


class TestParseHeaderDesignation:
    """Header line 1 first token is the canonical designation.

    Format: ``<dia>x<pitch>[<variant>]``
    where dia and pitch are decimal numbers and variant is the rest.
    """

    def test_plain_9x6(self):
        dia, pitch, variant = parse_header_designation(
            "         9x6                      (9x6.dat)"
        )
        assert dia == 9.0
        assert pitch == 6.0
        assert variant == ""

    def test_plain_12x6(self):
        dia, pitch, variant = parse_header_designation(
            "         12x6                      (12x6.dat)"
        )
        assert dia == 12.0
        assert pitch == 6.0
        assert variant == ""

    def test_decimal_10p5x4p5(self):
        """PER3_105x45 header reads '10.5x4.5' — decimal correctly parsed."""
        dia, pitch, variant = parse_header_designation(
            "         10.5x4.5                 (105x45.dat)"
        )
        assert dia == pytest.approx(10.5)
        assert pitch == pytest.approx(4.5)
        assert variant == ""

    def test_variant_E(self):
        """'10x10E' → dia=10, pitch=10, variant='E'."""
        dia, pitch, variant = parse_header_designation(
            "         10x10E                   (10x10E.dat)"
        )
        assert dia == 10.0
        assert pitch == 10.0
        assert variant == "E"

    def test_variant_marine_hyphen(self):
        """'10x10M-JK' → dia=10, pitch=10, variant='M-JK'."""
        dia, pitch, variant = parse_header_designation(
            "         10x10M-JK                (10x10M-JK.dat)"
        )
        assert dia == 10.0
        assert pitch == 10.0
        assert variant == "M-JK"

    def test_variant_with_decimal_pitch_and_suffix(self):
        """'10x3.8MRF-RH' → dia=10, pitch=3.8, variant='MRF-RH'."""
        dia, pitch, variant = parse_header_designation(
            "         10x3.8MRF-RH             (10x38MRF-RH.dat)"
        )
        assert dia == pytest.approx(10.0)
        assert pitch == pytest.approx(3.8)
        assert variant == "MRF-RH"

    def test_variant_with_parentheses(self):
        """'10x5.8EP(F2B)' → dia=10, pitch=5.8, variant='EP(F2B)'."""
        dia, pitch, variant = parse_header_designation(
            "         10x5.8EP(F2B)            (10x58EP(F2B).dat)"
        )
        assert dia == pytest.approx(10.0)
        assert pitch == pytest.approx(5.8)
        assert variant == "EP(F2B)"

    def test_blade_count_variant(self):
        """'10x6-4' → dia=10, pitch=6, variant='-4' (4-blade prop)."""
        dia, pitch, variant = parse_header_designation(
            "         10x6-4                   (10x6-4.dat)"
        )
        assert dia == 10.0
        assert pitch == 6.0
        assert variant == "-4"

    def test_invalid_returns_none(self):
        """Completely invalid line returns None."""
        result = parse_header_designation("   not a prop designation   ")
        assert result is None

    def test_empty_line_returns_none(self):
        result = parse_header_designation("")
        assert result is None


# ──────────────────────────────────────────────────────────────────────────────
# parse_apc_dat_file — fixture: 7x4 (existing, no header change needed)
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

    def test_variant_empty_for_plain_prop(self):
        assert self.result.variant == ""

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

    def test_variant_empty(self):
        assert self.result.variant == ""

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

    def test_variant_empty(self):
        assert self.result.variant == ""

    def test_rpm_blocks_count(self):
        assert len(self.result.rpm_blocks) == 2

    def test_source_version_captured(self):
        """Source version string (v2022-...) should be extracted from header."""
        assert self.result.source_version is not None
        assert "2022" in self.result.source_version


# ──────────────────────────────────────────────────────────────────────────────
# parse_apc_dat_file — new fixture: 105x45 (decimal without dot, gh-999)
# ──────────────────────────────────────────────────────────────────────────────


class TestParseApcDatFile105x45:
    """PER3_105x45.dat has filename '105x45' (decimal without dot),
    but header says '10.5x4.5' — parser must read from header."""

    @pytest.fixture(autouse=True)
    def parsed(self):
        path = FIXTURES_DIR / "PER3_105x45.dat"
        self.result = parse_apc_dat_file(path)

    def test_diameter_from_header(self):
        """Must be 10.5, not 105."""
        assert self.result.diameter_in == pytest.approx(10.5)

    def test_pitch_from_header(self):
        """Must be 4.5, not 45."""
        assert self.result.pitch_in == pytest.approx(4.5)

    def test_variant_empty(self):
        assert self.result.variant == ""

    def test_has_rpm_blocks(self):
        assert len(self.result.rpm_blocks) > 0

    def test_has_samples(self):
        assert any(len(b.samples) > 0 for b in self.result.rpm_blocks)


# ──────────────────────────────────────────────────────────────────────────────
# parse_apc_dat_file — new fixture: 10x10E (variant suffix E, gh-999)
# ──────────────────────────────────────────────────────────────────────────────


class TestParseApcDatFile10x10E:
    """PER3_10x10E.dat has variant suffix 'E' (electric pitch prop)."""

    @pytest.fixture(autouse=True)
    def parsed(self):
        path = FIXTURES_DIR / "PER3_10x10E.dat"
        self.result = parse_apc_dat_file(path)

    def test_diameter(self):
        assert self.result.diameter_in == 10.0

    def test_pitch(self):
        assert self.result.pitch_in == 10.0

    def test_variant_E(self):
        assert self.result.variant == "E"

    def test_has_rpm_blocks(self):
        assert len(self.result.rpm_blocks) > 0


# ──────────────────────────────────────────────────────────────────────────────
# parse_apc_dat_file — new fixture: 10x10M-JK (marine with hyphen, gh-999)
# ──────────────────────────────────────────────────────────────────────────────


class TestParseApcDatFile10x10MJK:
    """PER3_10x10M-JK.dat has compound variant suffix 'M-JK'."""

    @pytest.fixture(autouse=True)
    def parsed(self):
        path = FIXTURES_DIR / "PER3_10x10M-JK.dat"
        self.result = parse_apc_dat_file(path)

    def test_diameter(self):
        assert self.result.diameter_in == 10.0

    def test_pitch(self):
        assert self.result.pitch_in == 10.0

    def test_variant_MJK(self):
        assert self.result.variant == "M-JK"

    def test_has_rpm_blocks(self):
        assert len(self.result.rpm_blocks) > 0


# ──────────────────────────────────────────────────────────────────────────────
# build_snapshot_record — includes variant
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

    def test_variant_empty_in_specs(self):
        assert self.record["specs"]["variant"] == ""

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


class TestBuildSnapshotRecordVariant:
    """Snapshot record for a variant prop carries the variant field."""

    @pytest.fixture(autouse=True)
    def setup(self):
        path = FIXTURES_DIR / "PER3_10x10E.dat"
        parsed = parse_apc_dat_file(path)
        self.record = build_snapshot_record(parsed, path.name)

    def test_name_includes_variant(self):
        assert "10x10E" in self.record["name"]

    def test_specs_variant(self):
        assert self.record["specs"]["variant"] == "E"

    def test_model_ref_includes_variant(self):
        assert "E" in self.record.get("model_ref", "")


class TestBuildSnapshotRecordDecimal:
    """Snapshot record for a decimal-diameter prop uses correct values."""

    @pytest.fixture(autouse=True)
    def setup(self):
        path = FIXTURES_DIR / "PER3_105x45.dat"
        parsed = parse_apc_dat_file(path)
        self.record = build_snapshot_record(parsed, path.name)

    def test_specs_diameter_decimal(self):
        assert self.record["specs"]["diameter_in"] == pytest.approx(10.5)

    def test_specs_pitch_decimal(self):
        assert self.record["specs"]["pitch_in"] == pytest.approx(4.5)

    def test_name_format(self):
        assert self.record["name"] == "APC 10.5x4.5"


# ──────────────────────────────────────────────────────────────────────────────
# parse_all (batch, uses all fixture files)
# ──────────────────────────────────────────────────────────────────────────────


class TestParseAll:
    def test_parse_all_three_fixtures(self, tmp_path):
        """parse_all() should return one record per fixture file."""
        import shutil

        from scripts.parse_apc_props import parse_all, write_snapshot

        # Copy the 3 original fixture .dat files to a temp raw dir
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

    def test_parse_all_variant_fixtures(self, tmp_path):
        """parse_all() correctly handles variant and decimal fixtures."""
        import shutil

        from scripts.parse_apc_props import parse_all

        for fname in ("PER3_105x45.dat", "PER3_10x10E.dat", "PER3_10x10M-JK.dat"):
            shutil.copy(FIXTURES_DIR / fname, tmp_path / fname)

        records, fetched, skipped = parse_all(raw_dir=tmp_path)

        assert len(records) == 3
        assert len(fetched) == 3
        assert skipped == []

        names = {r["name"] for r in records}
        assert "APC 10.5x4.5" in names
        assert "APC 10x10E" in names
        assert "APC 10x10M-JK" in names

    def test_empty_file_skipped(self, tmp_path):
        """Zero-byte files in raw dir are skipped, not crash."""
        from scripts.parse_apc_props import parse_all

        (tmp_path / "PER3_99x99.dat").write_bytes(b"")

        records, fetched, skipped = parse_all(raw_dir=tmp_path)
        assert len(records) == 0
        assert "PER3_99x99.dat" in skipped

    def test_write_snapshot_roundtrip(self, tmp_path):
        """write_snapshot writes valid gzip JSON; reload equals original records."""
        import shutil

        from scripts.parse_apc_props import parse_all, write_snapshot

        shutil.copy(FIXTURES_DIR / "PER3_9x6.dat", tmp_path / "PER3_9x6.dat")

        records, _, _ = parse_all(raw_dir=tmp_path)
        out = tmp_path / "apc_props.json.gz"
        write_snapshot(records, output_path=out)

        with gzip.open(out, "rt", encoding="utf-8") as fh:
            reloaded = json.loads(fh.read())
        assert len(reloaded) == 1
        assert reloaded[0]["name"] == "APC 9x6"
        assert reloaded[0]["polars"][0]["samples"][0]["J"] == pytest.approx(0.0, abs=1e-4)

    def test_write_snapshot_produces_gz_file(self, tmp_path):
        """write_snapshot with .gz extension produces a valid gzip file."""
        import shutil

        from scripts.parse_apc_props import parse_all, write_snapshot

        shutil.copy(FIXTURES_DIR / "PER3_9x6.dat", tmp_path / "PER3_9x6.dat")
        records, _, _ = parse_all(raw_dir=tmp_path)
        out = tmp_path / "apc_props.json.gz"
        write_snapshot(records, output_path=out)

        assert out.exists()
        # File must be a valid gzip — magic bytes
        raw = out.read_bytes()
        assert raw[:2] == b"\x1f\x8b"  # gzip magic

    def test_missing_dir_returns_empty(self, tmp_path):
        """Calling parse_all on a non-existent directory returns ([], [], [])."""
        from scripts.parse_apc_props import parse_all

        non_existent = tmp_path / "no_such_dir"
        records, fetched, skipped = parse_all(raw_dir=non_existent)
        assert records == []
        assert fetched == []
        assert skipped == []


# ──────────────────────────────────────────────────────────────────────────────
# Committed snapshot validity (gh-999: validates gzip snapshot with ≥400 props)
# ──────────────────────────────────────────────────────────────────────────────


class TestCommittedSnapshot:
    def test_committed_snapshot_is_valid_gz(self):
        """The committed data/cots/apc_props.json.gz must be importable: every
        record passes validation, carries at least one polar sample, and the
        archive contains at least 400 props (we have 454 source files)."""
        from app.services.prop_polar_import import _validate_prop_record

        snapshot_path = REPO_ROOT / "data" / "cots" / "apc_props.json.gz"
        assert snapshot_path.exists(), f"Snapshot not found: {snapshot_path}"

        with gzip.open(snapshot_path, "rt", encoding="utf-8") as fh:
            data = json.loads(fh.read())

        # Must have a meaningful number — we parsed 454 files, expect at most
        # a handful of skips (empty or corrupt files).
        assert len(data) >= 400, f"Expected >= 400 props, got {len(data)}"

        for record in data:
            assert _validate_prop_record(record) is None, (
                f"Record failed validation: {record.get('name')}"
            )
            assert len(record["polars"]) > 0, f"Record has no polars: {record.get('name')}"

    def test_snapshot_has_decimal_diameter_prop(self):
        """Snapshot must include the 10.5x4.5 prop (decimal diameter)."""
        snapshot_path = REPO_ROOT / "data" / "cots" / "apc_props.json.gz"
        with gzip.open(snapshot_path, "rt", encoding="utf-8") as fh:
            data = json.loads(fh.read())

        names = {r["name"] for r in data}
        assert "APC 10.5x4.5" in names

    def test_snapshot_has_variant_prop(self):
        """Snapshot must include at least one variant prop (suffix like E, M-JK, etc.)."""
        snapshot_path = REPO_ROOT / "data" / "cots" / "apc_props.json.gz"
        with gzip.open(snapshot_path, "rt", encoding="utf-8") as fh:
            data = json.loads(fh.read())

        variant_records = [r for r in data if r.get("specs", {}).get("variant")]
        assert len(variant_records) > 0, "No variant props found in snapshot"

    def test_snapshot_variant_fields_present(self):
        """Every record in snapshot has a 'variant' field in specs."""
        snapshot_path = REPO_ROOT / "data" / "cots" / "apc_props.json.gz"
        with gzip.open(snapshot_path, "rt", encoding="utf-8") as fh:
            data = json.loads(fh.read())

        for record in data:
            assert "variant" in record.get("specs", {}), (
                f"Missing 'variant' in specs for {record.get('name')}"
            )


# ──────────────────────────────────────────────────────────────────────────────
# derive_blades — blade count from variant suffix (gh-1004)
# ──────────────────────────────────────────────────────────────────────────────


class TestDeriveBlades:
    """Blade count is encoded in the trailing -N token of the variant.

    APC designations carry a trailing ``-3`` / ``-4`` token for 3- and
    4-blade props (also as composites like ``E-3``, ``E-4``). Everything
    else (plain, ``E``, marine ``M-JK``, ``MRF-RH`` …) is the standard
    2-blade prop.
    """

    def test_plain_is_two(self):
        assert derive_blades("") == 2

    def test_electric_is_two(self):
        assert derive_blades("E") == 2

    def test_trailing_dash_4(self):
        assert derive_blades("-4") == 4

    def test_trailing_dash_3(self):
        assert derive_blades("-3") == 3

    def test_composite_E_dash_3(self):
        assert derive_blades("E-3") == 3

    def test_composite_E_dash_4(self):
        assert derive_blades("E-4") == 4

    def test_marine_letter_suffix_stays_two(self):
        # M-JK, M-LH, MRF-RH, P-LH, R-RH end in letters, not a blade count.
        assert derive_blades("M-JK") == 2
        assert derive_blades("M-LH") == 2
        assert derive_blades("MRF-RH") == 2
        assert derive_blades("P-LH") == 2
        assert derive_blades("R-RH") == 2

    def test_parenthesised_variant_stays_two(self):
        assert derive_blades("EP(F2B)") == 2
        assert derive_blades("(F1-GT)") == 2


class TestBuildSnapshotRecordBladeCount:
    """build_snapshot_record derives blades from the parsed variant."""

    def _record(self, variant: str) -> dict:
        parsed = ParsedPropFile(
            diameter_in=10.0,
            pitch_in=6.0,
            variant=variant,
            source_version="test",
            rpm_blocks=[],
        )
        return build_snapshot_record(parsed, "test.dat")

    def test_default_two_blades(self):
        assert self._record("")["specs"]["blades"] == 2

    def test_four_blade_variant(self):
        assert self._record("-4")["specs"]["blades"] == 4

    def test_three_blade_composite(self):
        assert self._record("E-3")["specs"]["blades"] == 3


class TestSnapshotBladeCounts:
    """The committed snapshot must encode real blade counts for -3/-4 props."""

    def _load(self) -> list[dict]:
        snapshot_path = REPO_ROOT / "data" / "cots" / "apc_props.json.gz"
        with gzip.open(snapshot_path, "rt", encoding="utf-8") as fh:
            return json.loads(fh.read())

    def test_known_multi_blade_props(self):
        data = {r["name"]: r for r in self._load()}
        assert data["APC 28x20-4"]["specs"]["blades"] == 4
        assert data["APC 4x4E-3"]["specs"]["blades"] == 3
        assert data["APC 15.75x13-3"]["specs"]["blades"] == 3

    def test_plain_prop_two_blades(self):
        data = {r["name"]: r for r in self._load()}
        assert data["APC 9x6"]["specs"]["blades"] == 2

    def test_seventeen_multiblade_records(self):
        data = self._load()
        multi = [r for r in data if r["specs"]["blades"] != 2]
        assert len(multi) == 17, f"expected 17 multi-blade props, got {len(multi)}"
