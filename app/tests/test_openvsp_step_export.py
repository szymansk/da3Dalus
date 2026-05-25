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
