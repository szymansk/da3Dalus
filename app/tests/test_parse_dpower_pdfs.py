"""Tests for scripts/parse_dpower_pdfs.py (gh-986).

The parser tests run against the actual D-Power PDFs located in:
  components/cots-assets/dpower/manuals/

These PDFs are gitignored and must be present locally for the full suite to
pass. If they are absent the tests are skipped (CI uses the committed JSON
snapshot only — see test_cots_json_snapshot.py).

No network access is performed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PDF_DIR = REPO_ROOT / "components" / "cots-assets" / "dpower" / "manuals"
SNAPSHOT_PATH = REPO_ROOT / "data" / "cots" / "dpower.json"

# Ensure the scripts directory is importable
sys.path.insert(0, str(REPO_ROOT))

pdfs_present = (
    (PDF_DIR / "V3_AL-Manual_print_A5_Max.pdf").exists()
    and (PDF_DIR / "Avicon Anleitung_web.pdf").exists()
    and (PDF_DIR / "manual_Antares_V3.pdf").exists()
)

skip_if_no_pdfs = pytest.mark.skipif(
    not pdfs_present,
    reason="D-Power PDFs not present (gitignored; copy to components/cots-assets/dpower/manuals/)",
)


@skip_if_no_pdfs
class TestParseDpowerPdfs:
    """Parser assertions against the actual PDF files."""

    @pytest.fixture(scope="class")
    def all_records(self):
        from scripts.parse_dpower_pdfs import parse_all

        return parse_all(pdf_dir=PDF_DIR)

    def test_total_count_motors_and_escs(self, all_records):
        motors = [r for r in all_records if r["component_type"] == "brushless_motor"]
        escs = [r for r in all_records if r["component_type"] == "esc"]
        assert len(motors) >= 20, f"Expected ≥20 motors, got {len(motors)}"
        assert len(escs) >= 15, f"Expected ≥15 ESCs, got {len(escs)}"

    def test_al_42_06_known_values(self, all_records):
        """AL 42-06: KV 540, Io 1.5 A, peak 45 A, 199 g."""
        record = next((r for r in all_records if r["name"] == "AL 42-06"), None)
        assert record is not None, "AL 42-06 not found"
        specs = record["specs"]
        assert specs["kv_rpm_per_volt"] == 540
        assert specs["io_no_load_a"] == pytest.approx(1.5)
        assert specs["max_current_a"] == pytest.approx(45.0)
        assert record["mass_g"] == 199

    def test_avicon_60a_known_values(self, all_records):
        """Avicon 60A: 60/80 A, 50 g."""
        record = next((r for r in all_records if r["name"] == "AVICON 60A"), None)
        assert record is not None, "AVICON 60A not found"
        specs = record["specs"]
        assert specs["continuous_current_a"] == pytest.approx(60.0)
        assert specs["max_current_a"] == pytest.approx(80.0)
        assert record["mass_g"] == 50

    def test_antares_25a_known_values(self, all_records):
        """Antares 25A BEC: 25/35 A, cells 2-4S, mass 19 g."""
        record = next((r for r in all_records if r["name"] == "Antares 25A BEC"), None)
        assert record is not None, "Antares 25A BEC not found"
        specs = record["specs"]
        assert specs["continuous_current_a"] == pytest.approx(25.0)
        assert specs["max_current_a"] == pytest.approx(35.0)
        assert specs["cells_lipo_min"] == 2
        assert specs["cells_lipo_max"] == 4
        assert record["mass_g"] == 19

    def test_ddrive_il36_3_7_known_values(self, all_records):
        """D-Drive IL36 3.7:1: KV 2040, peak 70 A, mass 364 g."""
        record = next((r for r in all_records if "D-Drive IL36 3.7" in r["name"]), None)
        assert record is not None, "D-Drive IL36 3.7:1 not found"
        specs = record["specs"]
        assert specs["kv_rpm_per_volt"] == 2040
        assert specs["max_current_a"] == pytest.approx(70.0)
        assert record["mass_g"] == 364

    def test_all_records_have_required_fields(self, all_records):
        for r in all_records:
            assert r.get("manufacturer") == "D-Power"
            assert r.get("name")
            assert r.get("component_type") in {"brushless_motor", "esc"}
            assert r.get("specs") is not None

    def test_no_none_kv_on_al_motors(self, all_records):
        al_motors = [r for r in all_records if r["name"].startswith("AL ")]
        for r in al_motors:
            assert r["specs"].get("kv_rpm_per_volt") is not None, f"{r['name']} has null KV"


class TestDpowerJsonSnapshot:
    """Validate the committed dpower.json snapshot (always runs, no PDFs needed)."""

    @pytest.fixture(scope="class")
    def snapshot(self):
        assert SNAPSHOT_PATH.exists(), f"Snapshot not found: {SNAPSHOT_PATH}"
        return json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))

    def test_snapshot_is_a_list(self, snapshot):
        assert isinstance(snapshot, list)

    def test_snapshot_has_expected_counts(self, snapshot):
        motors = [r for r in snapshot if r["component_type"] == "brushless_motor"]
        escs = [r for r in snapshot if r["component_type"] == "esc"]
        assert len(motors) >= 20
        assert len(escs) >= 15

    def test_al_42_06_in_snapshot(self, snapshot):
        record = next((r for r in snapshot if r["name"] == "AL 42-06"), None)
        assert record is not None
        assert record["specs"]["kv_rpm_per_volt"] == 540
        assert record["specs"]["io_no_load_a"] == 1.5
        assert record["specs"]["max_current_a"] == 45.0
        assert record["mass_g"] == 199

    def test_avicon_60a_in_snapshot(self, snapshot):
        record = next((r for r in snapshot if r["name"] == "AVICON 60A"), None)
        assert record is not None
        assert record["specs"]["continuous_current_a"] == 60.0
        assert record["specs"]["max_current_a"] == 80.0
        assert record["mass_g"] == 50

    def test_all_snapshot_records_have_valid_component_types(self, snapshot):
        valid = {"brushless_motor", "esc"}
        for r in snapshot:
            assert r.get("component_type") in valid, (
                f"Invalid component_type for {r.get('name')}: {r.get('component_type')}"
            )

    def test_all_motors_have_kv(self, snapshot):
        motors = [r for r in snapshot if r["component_type"] == "brushless_motor"]
        for r in motors:
            assert r["specs"].get("kv_rpm_per_volt") is not None, (
                f"Motor {r['name']} has null KV in snapshot"
            )

    def test_all_escs_have_continuous_current(self, snapshot):
        escs = [r for r in snapshot if r["component_type"] == "esc"]
        for r in escs:
            assert r["specs"].get("continuous_current_a") is not None, (
                f"ESC {r['name']} has null continuous_current_a in snapshot"
            )

    def test_no_pdf_content_in_snapshot(self, snapshot):
        """Ensure no PDF binary or path references leaked into the snapshot."""
        raw = json.dumps(snapshot)
        assert ".pdf" not in raw.lower()
        assert "/Users/" not in raw
