"""Tests for cad_designer.airplane.aircraft_topology.wing.Airfoil."""

import math
from pathlib import Path

import pytest
from cadquery import Plane, Vector

from cad_designer.airplane.aircraft_topology.wing.Airfoil import Airfoil

REPO_ROOT = Path(__file__).resolve().parents[2]
AIRFOILS_DIR = REPO_ROOT / "components" / "airfoils"


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

class TestAirfoilInit:
    """Test Airfoil constructor and default values."""

    def test_defaults(self):
        af = Airfoil()
        assert af.airfoil is None
        assert af.chord is None
        assert af.dihedral_as_rotation_in_degrees == 0
        assert af.incidence == 0
        assert af.coordinate_system is None

    def test_all_params(self):
        af = Airfoil(
            airfoil="naca2415",
            chord=200.0,
            dihedral_as_rotation_in_degrees=5.0,
            incidence=2.5,
        )
        assert af.airfoil == "naca2415"
        assert af.chord == 200.0
        assert af.dihedral_as_rotation_in_degrees == 5.0
        assert af.incidence == 2.5

    @pytest.mark.parametrize(
        "dihedral",
        [-180.0, -90.0, 0.0, 45.0, 90.0, 180.0],
        ids=lambda d: f"dihedral_{d}",
    )
    def test_various_dihedral_values(self, dihedral):
        af = Airfoil(dihedral_as_rotation_in_degrees=dihedral)
        assert af.dihedral_as_rotation_in_degrees == dihedral

    def test_negative_incidence(self):
        af = Airfoil(incidence=-3.0)
        assert af.incidence == -3.0


# ---------------------------------------------------------------------------
# Coordinate system
# ---------------------------------------------------------------------------

class TestAirfoilCoordinateSystem:
    """Test set_airfoil_coordinate_system."""

    def test_set_coordinate_system_from_xy_plane(self):
        af = Airfoil(airfoil="test", chord=100.0)
        plane = Plane.XY()
        af.set_airfoil_coordinate_system(plane)

        cs = af.coordinate_system
        assert cs is not None
        assert cs.origin == pytest.approx([0.0, 0.0, 0.0])
        assert cs.xDir == pytest.approx([1.0, 0.0, 0.0])
        assert cs.yDir == pytest.approx([0.0, 1.0, 0.0])
        assert cs.zDir == pytest.approx([0.0, 0.0, 1.0])

    def test_set_coordinate_system_from_offset_plane(self):
        af = Airfoil(airfoil="test", chord=100.0)
        plane = Plane(origin=(10.0, 20.0, 30.0), xDir=(1, 0, 0), normal=(0, 0, 1))
        af.set_airfoil_coordinate_system(plane)

        cs = af.coordinate_system
        assert cs.origin == pytest.approx([10.0, 20.0, 30.0])

    def test_coordinate_system_initially_none(self):
        af = Airfoil()
        assert af.coordinate_system is None


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

class TestAirfoilSerialization:
    """Test __getstate__ and from_json_dict round-trip."""

    def test_getstate_excludes_coordinate_system(self):
        af = Airfoil(airfoil="naca2415", chord=150.0, incidence=1.5)
        af.set_airfoil_coordinate_system(Plane.XY())

        state = af.__getstate__()
        assert "coordinate_system" not in state
        assert state["airfoil"] == "naca2415"
        assert state["chord"] == 150.0
        assert state["incidence"] == 1.5
        assert state["dihedral_as_rotation_in_degrees"] == 0

    def test_getstate_contains_all_fields_except_cs(self):
        af = Airfoil(airfoil="rg15", chord=200.0, dihedral_as_rotation_in_degrees=3.0, incidence=-1.0)
        state = af.__getstate__()
        expected_keys = {"airfoil", "chord", "dihedral_as_rotation_in_degrees", "incidence"}
        assert expected_keys == set(state.keys())

    def test_from_json_dict_full(self):
        data = {
            "airfoil": "rg15",
            "chord": 185.0,
            "dihedral_as_rotation_in_degrees": 5.0,
            "incidence": 2.0,
        }
        af = Airfoil.from_json_dict(data)
        assert af.airfoil == "rg15"
        assert af.chord == 185.0
        assert af.dihedral_as_rotation_in_degrees == 5.0
        assert af.incidence == 2.0
        assert af.coordinate_system is None

    def test_from_json_dict_defaults(self):
        data = {"airfoil": "naca0010"}
        af = Airfoil.from_json_dict(data)
        assert af.chord is None
        assert af.dihedral_as_rotation_in_degrees == 0
        assert af.incidence == 0

    def test_roundtrip(self):
        original = Airfoil(airfoil="naca2415", chord=250.0, dihedral_as_rotation_in_degrees=-10.0, incidence=3.5)
        state = original.__getstate__()
        restored = Airfoil.from_json_dict(state)

        assert restored.airfoil == original.airfoil
        assert restored.chord == original.chord
        assert restored.dihedral_as_rotation_in_degrees == original.dihedral_as_rotation_in_degrees
        assert restored.incidence == original.incidence


# ---------------------------------------------------------------------------
# repr
# ---------------------------------------------------------------------------

class TestAirfoilRepr:
    def test_repr_does_not_raise(self):
        af = Airfoil(airfoil="naca2415", chord=100.0)
        result = repr(af)
        assert "naca2415" in result
        assert "100.0" in result


# ---------------------------------------------------------------------------
# Airfoil file I/O via cq_plugins (read_airfoil_file)
# ---------------------------------------------------------------------------

class TestReadAirfoilFile:
    """Test the read_airfoil_file utility with real .dat files."""

    @pytest.fixture()
    def reader(self):
        from cad_designer.cq_plugins.wing.airfoil import read_airfoil_file
        return read_airfoil_file

    @pytest.mark.parametrize("filename", ["naca2415.dat", "rg15.dat"])
    def test_read_returns_list_of_tuples(self, reader, filename):
        path = str(AIRFOILS_DIR / filename)
        data = reader(path)
        assert isinstance(data, list)
        assert len(data) > 10
        for pt in data:
            assert len(pt) == 2

    def test_naca2415_starts_near_trailing_edge(self, reader):
        data = reader(str(AIRFOILS_DIR / "naca2415.dat"))
        # Selig format: first point is near x=1.0 (trailing edge)
        assert data[0][0] == pytest.approx(1.0, abs=0.01)

    def test_rg15_starts_near_trailing_edge(self, reader):
        data = reader(str(AIRFOILS_DIR / "rg15.dat"))
        assert data[0][0] == pytest.approx(1.0, abs=0.01)

    def test_all_coordinates_in_unit_range(self, reader):
        """Selig-format airfoil x-coords should be in [0, 1]."""
        data = reader(str(AIRFOILS_DIR / "naca2415.dat"))
        xs = [p[0] for p in data]
        assert min(xs) >= -0.01
        assert max(xs) <= 1.01

    def test_nonexistent_file_raises(self, reader):
        with pytest.raises(Exception):
            reader("/tmp/nonexistent_airfoil_xyz.dat")
