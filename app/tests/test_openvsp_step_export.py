"""Tests for the gh-729 per-geom STEP-export service.

Pure-Python tests live here (filename sanitisation, path resolution,
cleanup logic). Full integration with VSP + DB lives in
``test_openvsp_import_endpoint.py``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services.openvsp_step_export_service import (
    cleanup_aeroplane_step_files,
    sanitize_geom_filename,
    step_storage_dir,
)


class TestSanitizeGeomFilename:
    def test_passes_through_simple_names(self):
        assert sanitize_geom_filename("Fuselage") == "Fuselage"
        assert sanitize_geom_filename("Wing_1") == "Wing_1"
        assert sanitize_geom_filename("X-tail.v2") == "X-tail.v2"

    def test_collapses_spaces_and_punctuation(self):
        # Real Diamond DA42 name from the test corpus.
        assert sanitize_geom_filename("Engine carter (type fuselage)") == (
            "Engine_carter_type_fuselage"
        )

    def test_strips_path_traversal(self):
        assert ".." not in sanitize_geom_filename("../etc/passwd")
        assert "/" not in sanitize_geom_filename("foo/bar.stp")
        assert "\\" not in sanitize_geom_filename("foo\\bar.stp")

    def test_handles_leading_dots(self):
        assert sanitize_geom_filename(".hidden") == "hidden"
        assert sanitize_geom_filename("..twodots") == "twodots"

    def test_fallback_on_empty_or_dot_only(self):
        assert sanitize_geom_filename("") == "geom"
        assert sanitize_geom_filename("...") == "geom"
        assert sanitize_geom_filename("///") == "geom"

    def test_caps_at_64_chars(self):
        long = "x" * 200
        assert len(sanitize_geom_filename(long)) == 64

    def test_keeps_unicode_safely_collapsed(self):
        # German umlauts collapse to underscore — survivable on every FS.
        out = sanitize_geom_filename("Hauptrümpfle")
        assert "/" not in out
        assert "\\" not in out
        # Doesn't crash and produces a non-empty stem.
        assert len(out) > 0


class TestStepStorageDir:
    def test_creates_per_uuid_directory(self, tmp_path, monkeypatch):
        from app.core import config as core_config

        monkeypatch.setattr(core_config.settings, "ARTIFACTS_BASE_DIR", tmp_path)
        d = step_storage_dir("aaaa-bbbb-cccc")
        assert d.exists()
        assert d.is_dir()
        assert d.name == "aaaa-bbbb-cccc"
        assert d.parent.name == "openvsp_imports"

    def test_idempotent(self, tmp_path, monkeypatch):
        from app.core import config as core_config

        monkeypatch.setattr(core_config.settings, "ARTIFACTS_BASE_DIR", tmp_path)
        d1 = step_storage_dir("u1")
        d2 = step_storage_dir("u1")
        assert d1 == d2


class TestCleanup:
    def test_removes_existing_directory(self, tmp_path, monkeypatch):
        from app.core import config as core_config

        monkeypatch.setattr(core_config.settings, "ARTIFACTS_BASE_DIR", tmp_path)
        target = tmp_path / "openvsp_imports" / "u-delete-me"
        target.mkdir(parents=True)
        (target / "foo.stp").write_text("dummy")
        cleanup_aeroplane_step_files("u-delete-me")
        assert not target.exists()

    def test_silent_when_directory_missing(self, tmp_path, monkeypatch):
        from app.core import config as core_config

        monkeypatch.setattr(core_config.settings, "ARTIFACTS_BASE_DIR", tmp_path)
        # Should not raise.
        cleanup_aeroplane_step_files("never-existed")


# ---------------------------------------------------------------------------
# gh-732: STEPSettings.LenUnit FOOT → METRE override
# ---------------------------------------------------------------------------


class _FakeVsp:
    """Minimal stub of the OpenVSP API surface that
    ``_set_step_export_length_unit_metres`` interacts with. Tracks the
    LenUnit parm in an instance attribute so tests can assert it
    flipped from 4 (FOOT) to 2 (LEN_M).
    """

    LEN_M = 2
    LEN_FT = 4

    def __init__(self, *, vehicle_id: str = "VID", parm_id: str = "PARM-LU"):
        self._vehicle_id = vehicle_id
        self._parm_id = parm_id
        self.len_unit_value = float(self.LEN_FT)  # default like real VSP
        self.update_called = 0

    def FindContainer(self, name: str, _idx: int) -> str:  # noqa: N802
        return self._vehicle_id if name == "Vehicle" else ""

    def FindParm(self, vid: str, parm_name: str, group: str) -> str:  # noqa: N802
        if vid == self._vehicle_id and parm_name == "LenUnit" and group == "STEPSettings":
            return self._parm_id
        return ""

    def GetParmVal(self, pid: str) -> float:  # noqa: N802
        return self.len_unit_value if pid == self._parm_id else 0.0

    def SetParmVal(self, pid: str, val: float) -> None:  # noqa: N802
        if pid == self._parm_id:
            self.len_unit_value = float(val)

    def Update(self) -> None:  # noqa: N802
        self.update_called += 1


class TestSetStepExportLengthUnit:
    """gh-732: the export service must flip STEPSettings.LenUnit to
    METRE before each ExportFile call, otherwise OCC readers apply a
    spurious 0.3048× scale (the file declares FOOT but holds metres)."""

    def test_flips_from_foot_to_metre(self):
        from app.services.openvsp_step_export_service import (
            _set_step_export_length_unit_metres,
        )

        vsp = _FakeVsp()
        assert vsp.len_unit_value == 4.0  # default
        _set_step_export_length_unit_metres(vsp)
        assert vsp.len_unit_value == 2.0  # LEN_M
        assert vsp.update_called == 1

    def test_noop_when_already_metre(self):
        """Setting the parm a second time is cheap — no extra Update()
        call when value already matches."""
        from app.services.openvsp_step_export_service import (
            _set_step_export_length_unit_metres,
        )

        vsp = _FakeVsp()
        vsp.len_unit_value = 2.0  # already metres
        _set_step_export_length_unit_metres(vsp)
        assert vsp.len_unit_value == 2.0
        assert vsp.update_called == 0

    def test_silently_skips_when_container_missing(self):
        """If FindContainer returns "" (very old VSP), the helper
        bails without raising."""
        from app.services.openvsp_step_export_service import (
            _set_step_export_length_unit_metres,
        )

        class _Stub(_FakeVsp):
            def FindContainer(self, _name, _idx):  # noqa: N802
                return ""

        _set_step_export_length_unit_metres(_Stub())  # must not raise

    def test_silently_skips_when_parm_missing(self):
        """If FindParm returns "" (parm renamed in a future VSP version),
        the helper bails without raising."""
        from app.services.openvsp_step_export_service import (
            _set_step_export_length_unit_metres,
        )

        class _Stub(_FakeVsp):
            def FindParm(self, _vid, _name, _group):  # noqa: N802
                return ""

        _set_step_export_length_unit_metres(_Stub())  # must not raise

    def test_swallows_exceptions(self):
        """If something inside VSP throws (3.50 era ``FindParm`` known
        to print to stderr in some edge cases), the helper logs a
        warning and returns — never aborts the import."""
        from app.services.openvsp_step_export_service import (
            _set_step_export_length_unit_metres,
        )

        class _Boom(_FakeVsp):
            def SetParmVal(self, _pid, _val):  # noqa: N802
                raise RuntimeError("simulated VSP failure")

        _set_step_export_length_unit_metres(_Boom())  # must not raise
