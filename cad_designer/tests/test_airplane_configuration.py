"""Tests for AirplaneConfiguration data model."""
from __future__ import annotations

import json
import os
import zipfile

import aerosandbox as asb
import numpy as np
import pytest

from cad_designer.aerosandbox.wing_roundtrip_cases import (
    AIRFOIL_PATH,
    single_segment_flat,
)
from cad_designer.airplane.aircraft_topology.airplane.AirplaneConfiguration import (
    AirplaneConfiguration,
)
from cad_designer.airplane.aircraft_topology.fuselage.FuselageConfiguration import (
    FuselageConfiguration,
)
from cad_designer.airplane.aircraft_topology.wing.Airfoil import Airfoil
from cad_designer.airplane.aircraft_topology.wing.WingConfiguration import (
    WingConfiguration,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_wing() -> WingConfiguration:
    """Create a minimal WingConfiguration for testing."""
    return single_segment_flat()


def _make_fuselage() -> FuselageConfiguration:
    """Create a FuselageConfiguration with an ASB fuselage for testing."""
    fc = FuselageConfiguration(name="test_body")
    fc.asb_fuselage = asb.Fuselage(
        name="body",
        xsecs=[
            asb.FuselageXSec(
                xyz_c=np.array([0.0, 0.0, 0.0]),
                xyz_normal=np.array([1.0, 0.0, 0.0]),
                height=0.1,
                width=0.1,
            ),
            asb.FuselageXSec(
                xyz_c=np.array([1.0, 0.0, 0.0]),
                xyz_normal=np.array([1.0, 0.0, 0.0]),
                height=0.05,
                width=0.05,
            ),
        ],
    )
    return fc


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def wings_only() -> AirplaneConfiguration:
    """AirplaneConfiguration with one wing, no fuselages."""
    return AirplaneConfiguration(
        name="test_plane",
        total_mass_kg=2.5,
        wings=[_make_wing()],
    )


@pytest.fixture
def wings_and_fuselage() -> AirplaneConfiguration:
    """AirplaneConfiguration with one wing and one fuselage."""
    return AirplaneConfiguration(
        name="full_plane",
        total_mass_kg=3.0,
        wings=[_make_wing()],
        fuselages=[_make_fuselage()],
    )


# ---------------------------------------------------------------------------
# Constructor tests
# ---------------------------------------------------------------------------

class TestAirplaneConfigurationInit:
    """Tests for AirplaneConfiguration.__init__."""

    def test_name_stored(self, wings_only: AirplaneConfiguration) -> None:
        assert wings_only.name == "test_plane"

    def test_total_mass_stored(self, wings_only: AirplaneConfiguration) -> None:
        assert wings_only.total_mass == 2.5

    def test_wings_stored(self, wings_only: AirplaneConfiguration) -> None:
        assert len(wings_only.wings) == 1
        assert isinstance(wings_only.wings[0], WingConfiguration)

    def test_fuselages_default_none(self, wings_only: AirplaneConfiguration) -> None:
        assert wings_only.fuselages is None

    def test_fuselages_stored(
        self, wings_and_fuselage: AirplaneConfiguration
    ) -> None:
        assert wings_and_fuselage.fuselages is not None
        assert len(wings_and_fuselage.fuselages) == 1

    def test_main_wing_index_defaults_to_zero(
        self, wings_only: AirplaneConfiguration
    ) -> None:
        assert wings_only._main_wing_index == 0
        assert wings_only._main_wing is wings_only.wings[0]

    def test_multiple_wings(self) -> None:
        ac = AirplaneConfiguration(
            name="multi",
            total_mass_kg=5.0,
            wings=[_make_wing(), _make_wing()],
        )
        assert len(ac.wings) == 2
        assert ac._main_wing is ac.wings[0]

    def test_empty_wings_raises(self) -> None:
        """An empty wings list should raise IndexError when accessing
        _main_wing = self.wings[0]."""
        with pytest.raises(IndexError):
            AirplaneConfiguration(
                name="no_wings",
                total_mass_kg=1.0,
                wings=[],
            )


# ---------------------------------------------------------------------------
# Serialization: to_dict
# ---------------------------------------------------------------------------

class TestAirplaneConfigurationToDict:
    """Tests for to_dict serialization."""

    def test_contains_required_keys(
        self, wings_only: AirplaneConfiguration
    ) -> None:
        d = wings_only.to_dict()
        assert "name" in d
        assert "total_mass_kg" in d
        assert "wings" in d

    def test_name_and_mass_values(
        self, wings_only: AirplaneConfiguration
    ) -> None:
        d = wings_only.to_dict()
        assert d["name"] == "test_plane"
        assert d["total_mass_kg"] == 2.5

    def test_wings_serialized_as_list(
        self, wings_only: AirplaneConfiguration
    ) -> None:
        d = wings_only.to_dict()
        assert isinstance(d["wings"], list)
        assert len(d["wings"]) == 1

    def test_no_fuselages_key_when_none(
        self, wings_only: AirplaneConfiguration
    ) -> None:
        d = wings_only.to_dict()
        assert "fuselages" not in d

    def test_fuselages_included_when_present(
        self, wings_and_fuselage: AirplaneConfiguration
    ) -> None:
        d = wings_and_fuselage.to_dict()
        assert "fuselages" in d
        assert len(d["fuselages"]) == 1


# ---------------------------------------------------------------------------
# File I/O: save_to_json / from_json
# ---------------------------------------------------------------------------

class TestAirplaneConfigurationJsonIO:
    """Tests for JSON file save/load."""

    def test_save_creates_file(
        self, wings_only: AirplaneConfiguration, tmp_path
    ) -> None:
        path = str(tmp_path / "plane.json")
        wings_only.save_to_json(path)
        assert os.path.exists(path)

    def test_saved_file_is_valid_json(
        self, wings_only: AirplaneConfiguration, tmp_path
    ) -> None:
        path = str(tmp_path / "plane.json")
        wings_only.save_to_json(path)
        with open(path) as f:
            data = json.load(f)
        assert isinstance(data, dict)

    def test_roundtrip_wings_only(
        self, wings_only: AirplaneConfiguration, tmp_path
    ) -> None:
        path = str(tmp_path / "rt.json")
        wings_only.save_to_json(path)
        loaded = AirplaneConfiguration.from_json(path)
        assert loaded.name == wings_only.name
        assert loaded.total_mass == wings_only.total_mass
        assert len(loaded.wings) == len(wings_only.wings)
        assert loaded.fuselages is None

    def test_roundtrip_with_fuselage(
        self, wings_and_fuselage: AirplaneConfiguration, tmp_path
    ) -> None:
        path = str(tmp_path / "rt_fus.json")
        wings_and_fuselage.save_to_json(path)
        loaded = AirplaneConfiguration.from_json(path)
        assert loaded.name == wings_and_fuselage.name
        assert loaded.fuselages is not None
        assert len(loaded.fuselages) == 1
        assert loaded.fuselages[0].name == "test_body"

    def test_from_json_nonexistent_raises(self) -> None:
        with pytest.raises(FileNotFoundError):
            AirplaneConfiguration.from_json("/nonexistent/plane.json")


# ---------------------------------------------------------------------------
# Zip I/O: save_to_zip / from_zip
# ---------------------------------------------------------------------------

class TestAirplaneConfigurationZipIO:
    """Tests for zip file save/load."""

    def test_save_creates_zip(
        self, wings_only: AirplaneConfiguration, tmp_path
    ) -> None:
        path = str(tmp_path / "plane.zip")
        wings_only.save_to_zip(path)
        assert os.path.exists(path)
        assert zipfile.is_zipfile(path)

    def test_zip_contains_config_and_wings(
        self, wings_only: AirplaneConfiguration, tmp_path
    ) -> None:
        path = str(tmp_path / "plane.zip")
        wings_only.save_to_zip(path)
        with zipfile.ZipFile(path, "r") as zf:
            names = zf.namelist()
        assert "config.json" in names
        assert "wings/wing_0.json" in names

    def test_zip_contains_fuselages_when_present(
        self, wings_and_fuselage: AirplaneConfiguration, tmp_path
    ) -> None:
        path = str(tmp_path / "plane.zip")
        wings_and_fuselage.save_to_zip(path)
        with zipfile.ZipFile(path, "r") as zf:
            names = zf.namelist()
        assert "fuselages/fuselage_0.json" in names

    def test_roundtrip_via_zip(
        self, wings_and_fuselage: AirplaneConfiguration, tmp_path
    ) -> None:
        path = str(tmp_path / "roundtrip.zip")
        wings_and_fuselage.save_to_zip(path)
        loaded = AirplaneConfiguration.from_zip(path)
        assert loaded.name == wings_and_fuselage.name
        assert loaded.total_mass == wings_and_fuselage.total_mass
        assert len(loaded.wings) == 1
        assert loaded.fuselages is not None
        assert len(loaded.fuselages) == 1

    def test_zip_roundtrip_no_fuselages(
        self, wings_only: AirplaneConfiguration, tmp_path
    ) -> None:
        path = str(tmp_path / "nofus.zip")
        wings_only.save_to_zip(path)
        loaded = AirplaneConfiguration.from_zip(path)
        assert loaded.fuselages is None

    def test_zip_cleans_up_temp_dir(
        self, wings_only: AirplaneConfiguration, tmp_path
    ) -> None:
        path = str(tmp_path / "cleanup.zip")
        wings_only.save_to_zip(path)
        temp_dir = tmp_path / "temp_airplane_config"
        assert not temp_dir.exists(), "Temp directory should be cleaned up after save"

    def test_from_zip_cleans_up_temp_dir(
        self, wings_only: AirplaneConfiguration, tmp_path
    ) -> None:
        path = str(tmp_path / "cleanup2.zip")
        wings_only.save_to_zip(path)
        AirplaneConfiguration.from_zip(path)
        temp_dir = tmp_path / "temp_extract"
        assert not temp_dir.exists(), "Temp directory should be cleaned up after load"


# ---------------------------------------------------------------------------
# asb_airplane property
# ---------------------------------------------------------------------------

class TestAirplaneConfigurationAsbAirplane:
    """Tests for the cached asb_airplane property."""

    def test_returns_asb_airplane(
        self, wings_only: AirplaneConfiguration
    ) -> None:
        airplane = wings_only.asb_airplane
        assert isinstance(airplane, asb.Airplane)

    def test_airplane_has_correct_name(
        self, wings_only: AirplaneConfiguration
    ) -> None:
        assert wings_only.asb_airplane.name == "test_plane"

    def test_airplane_has_wings(
        self, wings_only: AirplaneConfiguration
    ) -> None:
        assert len(wings_only.asb_airplane.wings) == 1

    def test_airplane_with_fuselage(
        self, wings_and_fuselage: AirplaneConfiguration
    ) -> None:
        airplane = wings_and_fuselage.asb_airplane
        assert len(airplane.fuselages) == 1

    def test_airplane_no_fuselage_gives_empty_list(
        self, wings_only: AirplaneConfiguration
    ) -> None:
        airplane = wings_only.asb_airplane
        assert airplane.fuselages == []

    def test_cached_property_returns_same_object(
        self, wings_only: AirplaneConfiguration
    ) -> None:
        a1 = wings_only.asb_airplane
        a2 = wings_only.asb_airplane
        assert a1 is a2

    def test_main_wing_set_after_access(
        self, wings_only: AirplaneConfiguration
    ) -> None:
        _ = wings_only.asb_airplane
        assert wings_only._asb_main_wing is not None


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestAirplaneConfigurationEdgeCases:
    """Edge case and boundary tests."""

    def test_zero_mass(self) -> None:
        ac = AirplaneConfiguration(
            name="zero",
            total_mass_kg=0.0,
            wings=[_make_wing()],
        )
        assert ac.total_mass == 0.0

    def test_negative_mass_stored(self) -> None:
        """No validation prevents negative mass at this layer."""
        ac = AirplaneConfiguration(
            name="neg",
            total_mass_kg=-1.0,
            wings=[_make_wing()],
        )
        assert ac.total_mass == -1.0

    def test_multiple_fuselages(self) -> None:
        ac = AirplaneConfiguration(
            name="multi_fus",
            total_mass_kg=5.0,
            wings=[_make_wing()],
            fuselages=[_make_fuselage(), _make_fuselage()],
        )
        assert len(ac.fuselages) == 2

    def test_to_dict_multiple_wings(self) -> None:
        ac = AirplaneConfiguration(
            name="multi_wing",
            total_mass_kg=4.0,
            wings=[_make_wing(), _make_wing()],
        )
        d = ac.to_dict()
        assert len(d["wings"]) == 2

    def test_empty_fuselages_list_treated_as_falsy(self) -> None:
        """An empty fuselage list is falsy, so to_dict omits it."""
        ac = AirplaneConfiguration(
            name="empty_fus",
            total_mass_kg=2.0,
            wings=[_make_wing()],
            fuselages=[],
        )
        d = ac.to_dict()
        assert "fuselages" not in d
