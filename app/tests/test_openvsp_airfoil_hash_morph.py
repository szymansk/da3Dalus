"""Content-hash airfoil naming (gh-795) + Kulfan morph (gh-796).

The naming/IO helpers are pure-Python (no OpenVSP/AeroSandbox) so they run
in the fast CI tier and contribute coverage. The morph tests gate on
``aerosandbox`` via ``importorskip`` (installed in the fast tier).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.converters import openvsp_airfoil as oa


# --------------------------------------------------------------------------- #
# gh-795 — content-hash naming + dedup
# --------------------------------------------------------------------------- #


def _sym(thick: float) -> list[tuple[float, float]]:
    """A tiny symmetric 'airfoil' of given half-thickness, valid coords."""
    return [(1.0, 0.0), (0.5, thick), (0.0, 0.0), (0.5, -thick), (1.0, 0.0)]


def test_coords_hash_deterministic_and_distinct():
    assert oa._coords_hash(_sym(0.06)) == oa._coords_hash(_sym(0.06))
    assert oa._coords_hash(_sym(0.06)) != oa._coords_hash(_sym(0.09))


def test_coords_hash_rounds_to_six_decimals():
    a = [(0.5, 0.0600001), (0.0, 0.0)]
    b = [(0.5, 0.0600002), (0.0, 0.0)]  # same to 6 dp
    assert oa._coords_hash(a) == oa._coords_hash(b)


def test_write_imported_airfoil_dedup_and_distinct(tmp_path, monkeypatch):
    monkeypatch.setattr(oa, "AIRFOILS_DIR", tmp_path)

    p1 = oa.write_imported_airfoil_dat(_sym(0.06))
    assert Path(p1).name.startswith("vsp_imported_")
    assert p1.startswith("./components/airfoils/")
    assert (tmp_path / Path(p1).name).exists()

    # Same geometry → same name, no second file written.
    p2 = oa.write_imported_airfoil_dat(_sym(0.06))
    assert p2 == p1
    assert len(list(tmp_path.glob("*.dat"))) == 1

    # Different geometry → different file.
    p3 = oa.write_imported_airfoil_dat(_sym(0.09))
    assert p3 != p1
    assert len(list(tmp_path.glob("*.dat"))) == 2


def test_write_then_read_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(oa, "AIRFOILS_DIR", tmp_path)
    coords = _sym(0.08)
    rel = oa.write_imported_airfoil_dat(coords)
    read_back = oa._read_dat_coords(tmp_path / Path(rel).name)
    assert read_back == [(round(x, 6), round(y, 6)) for x, y in coords]


def test_custom_tag_prefix(tmp_path, monkeypatch):
    monkeypatch.setattr(oa, "AIRFOILS_DIR", tmp_path)
    rel = oa.write_imported_airfoil_dat(_sym(0.05), tag="vsp_morph")
    assert Path(rel).name.startswith("vsp_morph_")
