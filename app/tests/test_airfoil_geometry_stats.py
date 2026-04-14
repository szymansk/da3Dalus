"""Tests for the GET /airfoils/{airfoil_name}/geometry-stats endpoint."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.v2.endpoints import airfoils
from app.main import create_app

# Realistic Selig-format data: symmetric NACA-style with ~10% t/c, 0% camber.
_SYMMETRIC_DAT = """\
SYMMETRIC 10%
  1.00000  0.00000
  0.75000  0.03700
  0.50000  0.05000
  0.25000  0.04400
  0.00000  0.00000
  0.25000 -0.04400
  0.50000 -0.05000
  0.75000 -0.03700
  1.00000  0.00000
"""

# Cambered airfoil: upper thicker than lower -> positive camber.
_CAMBERED_DAT = """\
CAMBERED
  1.00000  0.00000
  0.75000  0.06000
  0.50000  0.08000
  0.25000  0.06000
  0.00000  0.00000
  0.25000 -0.02000
  0.50000 -0.02000
  0.75000 -0.01000
  1.00000  0.00000
"""


def _write_dat(tmp_path: Path, name: str, content: str) -> Path:
    airfoils_dir = tmp_path / "airfoils"
    airfoils_dir.mkdir(parents=True, exist_ok=True)
    dat_file = airfoils_dir / f"{name}.dat"
    dat_file.write_text(content, encoding="utf-8")
    return airfoils_dir


class TestGeometryStatsEndpoint:
    """Integration tests for the geometry-stats endpoint."""

    def test_symmetric_airfoil_has_zero_camber(self, tmp_path, monkeypatch):
        airfoils_dir = _write_dat(tmp_path, "symmetric", _SYMMETRIC_DAT)
        monkeypatch.setattr(airfoils, "AIRFOILS_DIR", airfoils_dir)

        with TestClient(create_app()) as client:
            resp = client.get("/airfoils/symmetric/geometry-stats")

        assert resp.status_code == 200
        data = resp.json()
        assert data["airfoil_name"] == "symmetric"
        # Symmetric -> camber should be ~0
        assert abs(data["max_camber_pct"]) < 0.5
        # Thickness should be ~10% (upper 0.05 - lower -0.05 = 0.10 -> 10%)
        assert 9.0 < data["max_thickness_pct"] < 11.0

    def test_cambered_airfoil_has_positive_camber(self, tmp_path, monkeypatch):
        airfoils_dir = _write_dat(tmp_path, "cambered", _CAMBERED_DAT)
        monkeypatch.setattr(airfoils, "AIRFOILS_DIR", airfoils_dir)

        with TestClient(create_app()) as client:
            resp = client.get("/airfoils/cambered/geometry-stats")

        assert resp.status_code == 200
        data = resp.json()
        assert data["max_camber_pct"] > 1.0  # clearly cambered
        assert data["max_thickness_pct"] > 0.0

    def test_returns_404_for_unknown_airfoil(self, tmp_path, monkeypatch):
        airfoils_dir = tmp_path / "airfoils"
        airfoils_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(airfoils, "AIRFOILS_DIR", airfoils_dir)

        with TestClient(create_app()) as client:
            resp = client.get("/airfoils/nonexistent/geometry-stats")

        assert resp.status_code == 404

    def test_response_fields_are_present(self, tmp_path, monkeypatch):
        airfoils_dir = _write_dat(tmp_path, "testfoil", _SYMMETRIC_DAT)
        monkeypatch.setattr(airfoils, "AIRFOILS_DIR", airfoils_dir)

        with TestClient(create_app()) as client:
            resp = client.get("/airfoils/testfoil/geometry-stats")

        data = resp.json()
        for field in [
            "airfoil_name",
            "max_thickness_pct",
            "max_thickness_x",
            "max_camber_pct",
            "max_camber_x",
        ]:
            assert field in data, f"Missing field: {field}"

    def test_thickness_within_sane_range(self, tmp_path, monkeypatch):
        airfoils_dir = _write_dat(tmp_path, "sanefoil", _CAMBERED_DAT)
        monkeypatch.setattr(airfoils, "AIRFOILS_DIR", airfoils_dir)

        with TestClient(create_app()) as client:
            resp = client.get("/airfoils/sanefoil/geometry-stats")

        data = resp.json()
        assert 0.0 < data["max_thickness_pct"] < 50.0

    def test_x_positions_within_chord(self, tmp_path, monkeypatch):
        airfoils_dir = _write_dat(tmp_path, "xcheck", _CAMBERED_DAT)
        monkeypatch.setattr(airfoils, "AIRFOILS_DIR", airfoils_dir)

        with TestClient(create_app()) as client:
            resp = client.get("/airfoils/xcheck/geometry-stats")

        data = resp.json()
        assert 0.0 <= data["max_thickness_x"] <= 1.0
        assert 0.0 <= data["max_camber_x"] <= 1.0


class TestGeometryStatsWithRealAirfoil:
    """Test against the real mh32.dat file if available."""

    @pytest.fixture()
    def real_airfoils_dir(self):
        real_dir = Path("components") / "airfoils"
        if not (real_dir / "mh32.dat").exists():
            pytest.skip("mh32.dat not available in components/airfoils")
        return real_dir

    def test_mh32_returns_valid_stats(self, real_airfoils_dir, monkeypatch):
        monkeypatch.setattr(airfoils, "AIRFOILS_DIR", real_airfoils_dir)

        with TestClient(create_app()) as client:
            resp = client.get("/airfoils/mh32/geometry-stats")

        assert resp.status_code == 200
        data = resp.json()
        assert data["airfoil_name"] == "mh32"
        # MH 32 header says 8.7%
        assert 7.0 < data["max_thickness_pct"] < 10.0
        assert 0.0 < data["max_thickness_pct"] < 50.0
        assert 0.0 <= data["max_thickness_x"] <= 1.0
        assert 0.0 <= data["max_camber_x"] <= 1.0
