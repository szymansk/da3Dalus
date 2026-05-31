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


# --------------------------------------------------------------------------- #
# gh-796 — morphing
# --------------------------------------------------------------------------- #


def _max_upper_y(coords):
    return max(y for _x, y in coords)


def test_raw_blend_thickness_is_between_anchors():
    # Pure NumPy fallback: blend a 6% and a 10% symmetric section at 0.5
    # → ~8% half-thickness, valid finite coords.
    out = oa._raw_blend(_sym(0.06), _sym(0.10), 0.5)
    assert out is not None
    assert _max_upper_y(out) == pytest.approx(0.08, abs=0.01)


def test_morph_falls_back_to_raw_blend_when_kulfan_fails(tmp_path, monkeypatch):
    # No AeroSandbox needed: resolve two .dat from disk, force the Kulfan
    # path to raise → raw-blend fallback still yields a content-hash file.
    monkeypatch.setattr(oa, "AIRFOILS_DIR", tmp_path)
    a = oa.write_imported_airfoil_dat(_sym(0.06), tag="anchor_a")
    b = oa.write_imported_airfoil_dat(_sym(0.10), tag="anchor_b")

    def _boom(*_a, **_k):
        raise RuntimeError("kulfan unavailable")

    monkeypatch.setattr(oa, "_kulfan_morph", _boom)
    rel = oa.morph_airfoils(Path(a).name, Path(b).name, 0.5)
    assert rel is not None
    assert Path(rel).name.startswith("vsp_morph_")
    assert (tmp_path / Path(rel).name).exists()


def test_morph_returns_none_when_anchor_unresolvable(tmp_path, monkeypatch):
    monkeypatch.setattr(oa, "AIRFOILS_DIR", tmp_path)
    assert oa.morph_airfoils("does_not_exist_a", "does_not_exist_b", 0.5) is None


def test_kulfan_morph_thickness_between_anchors(tmp_path, monkeypatch):
    """Real Kulfan interpolation between two symmetric NACA sections."""
    pytest.importorskip("aerosandbox")
    monkeypatch.setattr(oa, "AIRFOILS_DIR", tmp_path)
    # asb resolves bare NACA names; 18% and 8% symmetric → ~13% at t=0.5.
    rel = oa.morph_airfoils("naca0018", "naca0008", 0.5)
    assert rel is not None
    assert Path(rel).name.startswith("vsp_morph_")
    coords = oa._read_dat_coords(tmp_path / Path(rel).name)
    assert _max_upper_y(coords) == pytest.approx(0.065, abs=0.02)  # ~half of 13%
