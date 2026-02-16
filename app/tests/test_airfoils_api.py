import pytest
import numpy as np
from pathlib import Path
from urllib.parse import urlparse
from fastapi.testclient import TestClient

from app.api.v2.endpoints import airfoils
from app.core.exceptions import ConflictError
from app.main import create_app


def test_is_airfoil_known_returns_true_when_file_exists(tmp_path, monkeypatch):
    airfoils_dir = tmp_path / "airfoils"
    airfoils_dir.mkdir(parents=True)
    (airfoils_dir / "knownfoil.dat").write_text("KNOWNFOIL\n0.0 0.0\n1.0 0.0\n", encoding="utf-8")
    monkeypatch.setattr(airfoils, "AIRFOILS_DIR", airfoils_dir)

    with TestClient(create_app()) as client:
        response = client.get("/airfoils/knownfoil/known")

    assert response.status_code == 200
    payload = response.json()
    assert payload["known"] is True
    assert payload["file_name"] == "knownfoil.dat"
    assert payload["relative_path"].endswith("airfoils/knownfoil.dat")


def test_is_airfoil_known_returns_false_when_file_missing(tmp_path, monkeypatch):
    airfoils_dir = tmp_path / "airfoils"
    airfoils_dir.mkdir(parents=True)
    monkeypatch.setattr(airfoils, "AIRFOILS_DIR", airfoils_dir)

    with TestClient(create_app()) as client:
        response = client.get("/airfoils/missingfoil/known")

    assert response.status_code == 200
    payload = response.json()
    assert payload["known"] is False
    assert payload["file_name"] == "missingfoil.dat"
    assert payload["relative_path"] is None


def test_upload_airfoil_datfile_creates_file(tmp_path, monkeypatch):
    airfoils_dir = tmp_path / "airfoils"
    airfoils_dir.mkdir(parents=True)
    monkeypatch.setattr(airfoils, "AIRFOILS_DIR", airfoils_dir)

    with TestClient(create_app()) as client:
        response = client.post(
            "/airfoils/datfile",
            files={"file": ("customfoil.dat", b"CUSTOMFOIL\n0.0 0.0\n1.0 0.0\n", "text/plain")},
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["file_name"] == "customfoil.dat"
    assert payload["overwritten"] is False
    assert (airfoils_dir / "customfoil.dat").exists()


def test_upload_airfoil_datfile_overwrite_existing_file(tmp_path, monkeypatch):
    airfoils_dir = tmp_path / "airfoils"
    airfoils_dir.mkdir(parents=True)
    (airfoils_dir / "dupfoil.dat").write_text("OLD\n", encoding="utf-8")
    monkeypatch.setattr(airfoils, "AIRFOILS_DIR", airfoils_dir)

    with pytest.raises(ConflictError):
        airfoils.upload_airfoil_dat_content("dupfoil.dat", "NEW\n", overwrite=False)

    with TestClient(create_app()) as client:
        overwrite = client.post(
            "/airfoils/datfile?overwrite=true",
            files={"file": ("dupfoil.dat", b"NEW\n", "text/plain")},
        )

    assert overwrite.status_code == 200
    payload = overwrite.json()
    assert payload["overwritten"] is True
    assert (airfoils_dir / "dupfoil.dat").read_text(encoding="utf-8") == "NEW\n"


def test_list_airfoils_returns_sorted_dat_files_only(tmp_path, monkeypatch):
    airfoils_dir = tmp_path / "airfoils"
    airfoils_dir.mkdir(parents=True)
    (airfoils_dir / "zfoil.dat").write_text("Z\n", encoding="utf-8")
    (airfoils_dir / "afoil.dat").write_text("A\n", encoding="utf-8")
    (airfoils_dir / "ignore.txt").write_text("X\n", encoding="utf-8")
    monkeypatch.setattr(airfoils, "AIRFOILS_DIR", airfoils_dir)

    with TestClient(create_app()) as client:
        response = client.get("/airfoils")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 2
    assert [entry["file_name"] for entry in payload["airfoils"]] == ["afoil.dat", "zfoil.dat"]


def test_download_airfoil_datfile_returns_static_url(tmp_path, monkeypatch):
    airfoils_dir = tmp_path / "airfoils"
    airfoils_dir.mkdir(parents=True)
    (airfoils_dir / "mh32.dat").write_text("MH32\n0.0 0.0\n1.0 0.0\n", encoding="utf-8")
    monkeypatch.setattr(airfoils, "AIRFOILS_DIR", airfoils_dir)

    with TestClient(create_app()) as client:
        response = client.get("/airfoils/mh32/datfile")

    assert response.status_code == 200
    payload = response.json()
    assert payload["file_name"] == "mh32.dat"
    assert payload["mime_type"] == "text/plain"
    assert "/static/airfoils/downloads/" in payload["url"]

    static_path = Path(urlparse(payload["url"]).path.removeprefix("/static/"))
    assert (Path("tmp") / static_path).exists()


def test_analyze_airfoil_neuralfoil_returns_json(tmp_path, monkeypatch):
    airfoils_dir = tmp_path / "airfoils"
    airfoils_dir.mkdir(parents=True)
    (airfoils_dir / "mh32.dat").write_text("MH32\n0.0 0.0\n1.0 0.0\n", encoding="utf-8")
    monkeypatch.setattr(airfoils, "AIRFOILS_DIR", airfoils_dir)

    def _mock_run_neuralfoil_analysis(*_, **__):
        alpha = np.array([-4.0, 0.0, 4.0], dtype=float)
        return alpha, [
            {
                "reynolds_number": 100000.0,
                "cl": np.array([-0.4, 0.2, 0.8], dtype=float),
                "cd": np.array([0.04, 0.02, 0.03], dtype=float),
                "cm": np.array([-0.08, -0.05, -0.03], dtype=float),
                "cl_over_cd": np.array([-10.0, 10.0, 26.6667], dtype=float),
                "analysis_confidence": np.array([0.90, 0.95, 0.92], dtype=float),
                "cl_max": 0.8,
                "alpha_at_cl_max_deg": 4.0,
                "cd_min": 0.02,
                "alpha_at_cd_min_deg": 0.0,
            },
            {
                "reynolds_number": 300000.0,
                "cl": np.array([-0.5, 0.25, 0.9], dtype=float),
                "cd": np.array([0.03, 0.015, 0.022], dtype=float),
                "cm": np.array([-0.07, -0.04, -0.02], dtype=float),
                "cl_over_cd": np.array([-16.6667, 16.6667, 40.9091], dtype=float),
                "analysis_confidence": np.array([0.91, 0.96, 0.94], dtype=float),
                "cl_max": 0.9,
                "alpha_at_cl_max_deg": 4.0,
                "cd_min": 0.015,
                "alpha_at_cd_min_deg": 0.0,
            },
        ]

    monkeypatch.setattr(airfoils, "_run_neuralfoil_analysis", _mock_run_neuralfoil_analysis)

    with TestClient(create_app()) as client:
        response = client.post(
            "/airfoils/mh32/neuralfoil/analysis",
            json={"reynolds_numbers": [100000, 300000]},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["file_name"] == "mh32.dat"
    assert payload["alpha_deg"] == [-4.0, 0.0, 4.0]
    assert len(payload["reynolds_results"]) == 2
    assert payload["reynolds_results"][0]["reynolds_number"] == 100000.0
    assert payload["reynolds_results"][1]["cl_max"] == 0.9


def test_analyze_airfoil_neuralfoil_diagrams_returns_urls(tmp_path, monkeypatch):
    airfoils_dir = tmp_path / "airfoils"
    airfoils_dir.mkdir(parents=True)
    (airfoils_dir / "mh32.dat").write_text("MH32\n0.0 0.0\n1.0 0.0\n", encoding="utf-8")
    monkeypatch.setattr(airfoils, "AIRFOILS_DIR", airfoils_dir)

    def _mock_run_neuralfoil_analysis(*_, **__):
        alpha = np.array([-2.0, 0.0, 2.0], dtype=float)
        return alpha, [
            {
                "reynolds_number": 150000.0,
                "cl": np.array([-0.2, 0.1, 0.5], dtype=float),
                "cd": np.array([0.03, 0.018, 0.025], dtype=float),
                "cm": np.array([-0.05, -0.03, -0.02], dtype=float),
                "cl_over_cd": np.array([-6.6667, 5.5556, 20.0], dtype=float),
                "analysis_confidence": np.array([0.9, 0.9, 0.9], dtype=float),
                "cl_max": 0.5,
                "alpha_at_cl_max_deg": 2.0,
                "cd_min": 0.018,
                "alpha_at_cd_min_deg": 0.0,
            }
        ]

    monkeypatch.setattr(airfoils, "_run_neuralfoil_analysis", _mock_run_neuralfoil_analysis)

    with TestClient(create_app()) as client:
        response = client.post(
            "/airfoils/mh32/neuralfoil/analysis/diagrams",
            json={"reynolds_numbers": [150000]},
        )

    assert response.status_code == 200
    payload = response.json()
    for key in [
        "cl_vs_alpha_url",
        "cd_vs_alpha_url",
        "cm_vs_alpha_url",
        "cd_vs_cl_url",
        "cl_over_cd_vs_alpha_url",
    ]:
        assert "/static/airfoils/neuralfoil/mh32/" in payload[key]
        static_path = Path(urlparse(payload[key]).path.removeprefix("/static/"))
        assert (Path("tmp") / static_path).exists()
