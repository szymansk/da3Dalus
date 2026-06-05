"""gh-789: imported airfoil .dat files must not contain duplicate adjacent
points.

OpenVSP exports can emit consecutive identical coordinates. AeroSandbox's
``Airfoil.repanel()`` (called during VLM section subdivision) raises
"It looks like your Airfoil has a duplicate point" and crashes the solve.
The importer must de-duplicate consecutive points when writing
``vsp_imported_*.dat``.

These tests are pure-Python (no aerosandbox / cadquery) so they run in the
PR-fast / coverage tier.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.converters import openvsp_airfoil
from app.converters.openvsp_airfoil import (
    _dedup_consecutive_points,
    _read_dat_coords,
    write_imported_airfoil_dat,
)


@pytest.fixture
def airfoils_dir(tmp_path, monkeypatch):
    d = tmp_path / "airfoils"
    d.mkdir(parents=True)
    monkeypatch.setattr(openvsp_airfoil, "AIRFOILS_DIR", d)
    return d


def _has_consecutive_duplicates(coords, tol: float = 1e-9) -> bool:
    for a, b in zip(coords, coords[1:], strict=False):
        if abs(a[0] - b[0]) <= tol and abs(a[1] - b[1]) <= tol:
            return True
    return False


class TestDedupConsecutivePoints:
    def test_removes_adjacent_duplicate(self):
        coords = [(1.0, 0.0), (0.5, 0.05), (0.5, 0.05), (0.0, 0.0), (1.0, 0.0)]
        out = _dedup_consecutive_points(coords)
        assert out == [(1.0, 0.0), (0.5, 0.05), (0.0, 0.0), (1.0, 0.0)]

    def test_collapses_runs_of_more_than_two(self):
        coords = [(0.0, 0.0), (0.0, 0.0), (0.0, 0.0), (1.0, 0.0)]
        assert _dedup_consecutive_points(coords) == [(0.0, 0.0), (1.0, 0.0)]

    def test_keeps_non_consecutive_repeat(self):
        # First and last point legitimately coincide (closed contour) — only
        # *adjacent* duplicates are removed, so the endpoints survive.
        coords = [(1.0, 0.0), (0.0, 0.0), (1.0, 0.0)]
        assert _dedup_consecutive_points(coords) == coords

    def test_near_duplicate_within_tolerance_removed(self):
        coords = [(0.5, 0.05), (0.5 + 1e-12, 0.05 - 1e-12), (0.4, 0.04)]
        assert _dedup_consecutive_points(coords) == [(0.5, 0.05), (0.4, 0.04)]

    def test_clean_input_unchanged(self):
        coords = [(1.0, 0.0), (0.5, 0.05), (0.0, 0.0)]
        assert _dedup_consecutive_points(coords) == coords

    def test_empty_and_single(self):
        assert _dedup_consecutive_points([]) == []
        assert _dedup_consecutive_points([(0.0, 0.0)]) == [(0.0, 0.0)]


class TestWriteImportedAirfoilDatDedups:
    def test_written_file_has_no_adjacent_duplicates(self, airfoils_dir):
        dirty = [(1.0, 0.0), (0.5, 0.05), (0.5, 0.05), (0.0, 0.0), (0.5, -0.05), (1.0, 0.0)]
        rel = write_imported_airfoil_dat(dirty)
        written = _read_dat_coords(airfoils_dir / Path(rel).name)
        assert not _has_consecutive_duplicates(written), written
        # the one duplicated point was dropped
        assert len(written) == len(dirty) - 1

    def test_dirty_and_clean_map_to_same_hash_file(self, airfoils_dir):
        clean = [(1.0, 0.0), (0.5, 0.05), (0.0, 0.0), (0.5, -0.05), (1.0, 0.0)]
        dirty = [(1.0, 0.0), (0.5, 0.05), (0.5, 0.05), (0.0, 0.0), (0.5, -0.05), (1.0, 0.0)]
        r_clean = write_imported_airfoil_dat(clean)
        r_dirty = write_imported_airfoil_dat(dirty)
        # de-dup happens before hashing → both resolve to one file
        assert r_clean == r_dirty
        assert len(list(airfoils_dir.glob("vsp_imported_*.dat"))) == 1
