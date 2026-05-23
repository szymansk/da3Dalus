"""Unit tests for the OpenVSP BLANK + Vehicle CG handler (gh-645).

Covers:

* BLANK geom with explicit Mass>0 → WeightItemWrite at XForm position
* BLANK without mass → skipped silently
* Vehicle CG: X_CG/Y_CG/Z_CG in `Mass_Props` group → aeroplane.xyz_ref
* Fallback: compute CG from collected weight items when Vehicle CG
  is missing
* Total-mass consistency (sum vs declared) within 1%

All tests mock the `openvsp` module — no real install required.
"""

from __future__ import annotations

from types import ModuleType, SimpleNamespace
from typing import cast

import pytest

from app.converters import openvsp_adapter, openvsp_importer
from app.converters.openvsp_blank_handler import register
from app.converters.openvsp_importer import import_vsp3


# ---------------------------------------------------------------------------
# Fake VSP factory
# ---------------------------------------------------------------------------


def _make_blank_vsp(
    *,
    geoms: list[dict] | None = None,
    vehicle_total_mass: float = 0.0,
    vehicle_cg: tuple[float, float, float] | None = None,
    vehicle_id: str = "VEH",
) -> ModuleType:
    """Build a fake `openvsp` module with BLANK geoms and a vehicle CG.

    Each geom dict: ``{id, name, mass, x, y, z}``. Mass omitted → no
    mass parm (simulates a pure-transform BLANK).
    """
    geoms = geoms or []

    fake = SimpleNamespace()  # see test_openvsp_importer for rationale
    fake.LEN_M = 2
    fake.SYM_XZ = 2

    fake.ClearVSPModel = lambda *a, **k: None
    fake.ReadVSPFile = lambda *a, **k: None
    fake.SetLengthUnit = lambda *a, **k: None
    fake.Update = lambda *a, **k: None
    fake.GetVehicleID = lambda: vehicle_id
    fake.FindGeoms = lambda: [g["id"] for g in geoms]
    fake.GetGeomName = lambda gid: next((g["name"] for g in geoms if g["id"] == gid), "")
    fake.GetGeomTypeName = lambda gid: next(
        (g.get("type", "BLANK") for g in geoms if g["id"] == gid), ""
    )

    def _find_parm(container, parm, group):
        # Vehicle Mass_Props parms
        if container == vehicle_id and group == "Mass_Props":
            if vehicle_cg is None and parm in ("X_CG", "Y_CG", "Z_CG"):
                return ""
            if vehicle_total_mass <= 0 and parm == "TotalMass":
                return ""
            return f"VEH::{parm}"
        # BLANK Mass_Props.Mass
        for g in geoms:
            if container == g["id"]:
                if group == "Mass_Props" and parm == "Mass":
                    return f"{g['id']}::Mass" if "mass" in g else ""
                if group == "XForm" and parm in ("X_Location", "Y_Location", "Z_Location"):
                    return f"{g['id']}::{parm}"
        return ""

    def _get_parm_val(pid):
        if not pid:
            return 0.0
        if pid.startswith("VEH::"):
            parm = pid.split("::", 1)[1]
            if parm == "TotalMass":
                return float(vehicle_total_mass)
            mapping = {
                "X_CG": (vehicle_cg or (0, 0, 0))[0],
                "Y_CG": (vehicle_cg or (0, 0, 0))[1],
                "Z_CG": (vehicle_cg or (0, 0, 0))[2],
            }
            return float(mapping.get(parm, 0.0))
        gid, parm = pid.split("::", 1)
        for g in geoms:
            if g["id"] == gid:
                if parm == "Mass":
                    return float(g.get("mass", 0.0))
                if parm == "X_Location":
                    return float(g.get("x", 0.0))
                if parm == "Y_Location":
                    return float(g.get("y", 0.0))
                if parm == "Z_Location":
                    return float(g.get("z", 0.0))
        return 0.0

    fake.FindParm = _find_parm
    fake.GetParmVal = _get_parm_val
    return cast(ModuleType, fake)


# ---------------------------------------------------------------------------
# Registration: handler + post-pass for vehicle CG
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clean_handlers():
    openvsp_importer._HANDLERS.clear()
    openvsp_importer._POST_PASSES.clear()
    register()
    yield
    openvsp_importer._HANDLERS.clear()
    openvsp_importer._POST_PASSES.clear()


# ---------------------------------------------------------------------------
# BLANK → WeightItem
# ---------------------------------------------------------------------------


class TestBlankHandler:
    def test_blank_with_mass_creates_weight_item(self, tmp_path, monkeypatch):
        f = tmp_path / "x.vsp3"
        f.write_text("")
        fake = _make_blank_vsp(
            geoms=[
                {
                    "id": "G1",
                    "name": "Battery",
                    "type": "BLANK",
                    "mass": 2.5,
                    "x": 0.3,
                    "y": 0.0,
                    "z": -0.05,
                }
            ]
        )
        monkeypatch.setattr(openvsp_adapter, "get_vsp", lambda: fake)
        result = import_vsp3(f)
        assert len(result.weight_items) == 1
        wi = result.weight_items[0]
        assert wi.name == "Battery"
        assert wi.mass_kg == pytest.approx(2.5)
        assert wi.x_m == pytest.approx(0.3)
        assert wi.z_m == pytest.approx(-0.05)

    def test_blank_without_mass_is_skipped(self, tmp_path, monkeypatch):
        f = tmp_path / "x.vsp3"
        f.write_text("")
        fake = _make_blank_vsp(
            geoms=[
                {"id": "G1", "name": "Origin", "type": "BLANK"}  # no mass
            ]
        )
        monkeypatch.setattr(openvsp_adapter, "get_vsp", lambda: fake)
        result = import_vsp3(f)
        assert result.weight_items == []

    def test_blank_with_zero_mass_is_skipped(self, tmp_path, monkeypatch):
        f = tmp_path / "x.vsp3"
        f.write_text("")
        fake = _make_blank_vsp(geoms=[{"id": "G1", "name": "Origin", "type": "BLANK", "mass": 0.0}])
        monkeypatch.setattr(openvsp_adapter, "get_vsp", lambda: fake)
        result = import_vsp3(f)
        assert result.weight_items == []

    def test_negative_mass_is_skipped_with_warning(self, tmp_path, monkeypatch):
        f = tmp_path / "x.vsp3"
        f.write_text("")
        fake = _make_blank_vsp(geoms=[{"id": "G1", "name": "Bogus", "type": "BLANK", "mass": -1.0}])
        monkeypatch.setattr(openvsp_adapter, "get_vsp", lambda: fake)
        result = import_vsp3(f)
        assert result.weight_items == []
        assert any("negative" in w.reason.lower() or "<=0" in w.reason for w in result.warnings)


# ---------------------------------------------------------------------------
# Vehicle CG
# ---------------------------------------------------------------------------


class TestVehicleCG:
    def test_vehicle_cg_overrides_default(self, tmp_path, monkeypatch):
        f = tmp_path / "x.vsp3"
        f.write_text("")
        fake = _make_blank_vsp(
            geoms=[],
            vehicle_total_mass=10.0,
            vehicle_cg=(0.5, 0.0, 0.1),
        )
        monkeypatch.setattr(openvsp_adapter, "get_vsp", lambda: fake)
        result = import_vsp3(f)
        assert result.aeroplane.xyz_ref == pytest.approx([0.5, 0.0, 0.1])
        assert result.aeroplane.total_mass_kg == pytest.approx(10.0)

    def test_cg_falls_back_to_weighted_average_of_items(self, tmp_path, monkeypatch):
        """When vehicle CG is not declared, compute from weight items."""
        f = tmp_path / "x.vsp3"
        f.write_text("")
        fake = _make_blank_vsp(
            geoms=[
                {
                    "id": "G1",
                    "name": "A",
                    "type": "BLANK",
                    "mass": 1.0,
                    "x": 0.0,
                    "y": 0.0,
                    "z": 0.0,
                },
                {
                    "id": "G2",
                    "name": "B",
                    "type": "BLANK",
                    "mass": 3.0,
                    "x": 1.0,
                    "y": 0.0,
                    "z": 0.0,
                },
            ],
            vehicle_cg=None,
            vehicle_total_mass=0.0,
        )
        monkeypatch.setattr(openvsp_adapter, "get_vsp", lambda: fake)
        result = import_vsp3(f)
        # CG = (1*0 + 3*1) / (1+3) = 0.75
        assert result.aeroplane.xyz_ref[0] == pytest.approx(0.75)
        assert result.aeroplane.xyz_ref[1] == pytest.approx(0.0)

    def test_no_items_no_cg_yields_default_origin(self, tmp_path, monkeypatch):
        f = tmp_path / "x.vsp3"
        f.write_text("")
        fake = _make_blank_vsp(geoms=[], vehicle_cg=None)
        monkeypatch.setattr(openvsp_adapter, "get_vsp", lambda: fake)
        result = import_vsp3(f)
        # Stays at the AeroplaneSchema default [0, 0, 0]
        assert result.aeroplane.xyz_ref == [0, 0, 0]

    def test_total_mass_consistency_warning(self, tmp_path, monkeypatch):
        f = tmp_path / "x.vsp3"
        f.write_text("")
        fake = _make_blank_vsp(
            geoms=[
                {
                    "id": "G1",
                    "name": "A",
                    "type": "BLANK",
                    "mass": 1.0,
                    "x": 0.0,
                    "y": 0.0,
                    "z": 0.0,
                },
                {
                    "id": "G2",
                    "name": "B",
                    "type": "BLANK",
                    "mass": 1.0,
                    "x": 0.0,
                    "y": 0.0,
                    "z": 0.0,
                },
            ],
            vehicle_total_mass=5.0,  # mismatches sum (=2) by 150%
        )
        monkeypatch.setattr(openvsp_adapter, "get_vsp", lambda: fake)
        result = import_vsp3(f)
        assert any(
            "total mass" in w.reason.lower() and "mismatch" in w.reason.lower()
            for w in result.warnings
        )
