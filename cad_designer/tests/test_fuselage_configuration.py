"""Tests for FuselageConfiguration data model."""
from __future__ import annotations

import json
import os

import aerosandbox as asb
import numpy as np
import pytest

from cad_designer.airplane.aircraft_topology.fuselage.FuselageConfiguration import (
    FuselageConfiguration,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def simple_fuselage() -> FuselageConfiguration:
    """A FuselageConfiguration with only a name (no ASB fuselage)."""
    return FuselageConfiguration(name="test_fuselage")


@pytest.fixture
def fuselage_with_asb() -> FuselageConfiguration:
    """A FuselageConfiguration populated with an aerosandbox Fuselage."""
    fc = FuselageConfiguration(name="asb_fuselage")
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
                xyz_c=np.array([0.5, 0.0, 0.0]),
                xyz_normal=np.array([1.0, 0.0, 0.0]),
                height=0.3,
                width=0.25,
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
# Constructor tests
# ---------------------------------------------------------------------------

class TestFuselageConfigurationInit:
    """Tests for FuselageConfiguration.__init__."""

    def test_name_is_stored(self, simple_fuselage: FuselageConfiguration) -> None:
        assert simple_fuselage.name == "test_fuselage"

    def test_asb_fuselage_defaults_to_none(
        self, simple_fuselage: FuselageConfiguration
    ) -> None:
        assert simple_fuselage.asb_fuselage is None

    def test_private_fields_default_to_none(
        self, simple_fuselage: FuselageConfiguration
    ) -> None:
        assert simple_fuselage._step_file is None
        assert simple_fuselage._step_scale is None
        assert simple_fuselage._number_of_slices is None

    def test_empty_name(self) -> None:
        fc = FuselageConfiguration(name="")
        assert fc.name == ""


# ---------------------------------------------------------------------------
# Serialization: __getstate__
# ---------------------------------------------------------------------------

class TestFuselageConfigurationGetState:
    """Tests for __getstate__ (dict serialization)."""

    def test_minimal_getstate(self, simple_fuselage: FuselageConfiguration) -> None:
        state = simple_fuselage.__getstate__()
        assert state["name"] == "test_fuselage"
        assert state["step_file"] is None
        assert state["step_scale"] is None
        assert state["number_of_slices"] is None
        assert "asb_fuselage" not in state

    def test_getstate_with_asb_fuselage(
        self, fuselage_with_asb: FuselageConfiguration
    ) -> None:
        state = fuselage_with_asb.__getstate__()
        assert "asb_fuselage" in state
        asb_data = state["asb_fuselage"]
        assert asb_data["name"] == "body"
        assert len(asb_data["xsecs"]) == 3

    def test_getstate_xsec_fields(
        self, fuselage_with_asb: FuselageConfiguration
    ) -> None:
        xsec = fuselage_with_asb.__getstate__()["asb_fuselage"]["xsecs"][1]
        assert xsec["height"] == 0.3
        assert xsec["width"] == 0.25
        np.testing.assert_array_almost_equal(xsec["xyz_c"], [0.5, 0.0, 0.0])
        np.testing.assert_array_almost_equal(xsec["xyz_normal"], [1.0, 0.0, 0.0])

    def test_getstate_is_json_serializable(
        self, fuselage_with_asb: FuselageConfiguration
    ) -> None:
        """__getstate__ output must be JSON-encodable."""
        state = fuselage_with_asb.__getstate__()
        serialized = json.dumps(state)
        assert isinstance(serialized, str)


# ---------------------------------------------------------------------------
# Deserialization: from_json_dict
# ---------------------------------------------------------------------------

class TestFuselageConfigurationFromJsonDict:
    """Tests for the static from_json_dict factory."""

    def test_roundtrip_minimal(self, simple_fuselage: FuselageConfiguration) -> None:
        state = simple_fuselage.__getstate__()
        restored = FuselageConfiguration.from_json_dict(state)
        assert restored.name == simple_fuselage.name
        assert restored.asb_fuselage is None

    def test_roundtrip_with_asb(
        self, fuselage_with_asb: FuselageConfiguration
    ) -> None:
        state = fuselage_with_asb.__getstate__()
        restored = FuselageConfiguration.from_json_dict(state)
        assert restored.name == fuselage_with_asb.name
        assert restored.asb_fuselage is not None
        assert len(restored.asb_fuselage.xsecs) == 3

    def test_roundtrip_preserves_xsec_geometry(
        self, fuselage_with_asb: FuselageConfiguration
    ) -> None:
        state = fuselage_with_asb.__getstate__()
        restored = FuselageConfiguration.from_json_dict(state)
        original_xsec = fuselage_with_asb.asb_fuselage.xsecs[1]
        restored_xsec = restored.asb_fuselage.xsecs[1]
        np.testing.assert_array_almost_equal(
            restored_xsec.xyz_c, original_xsec.xyz_c
        )
        assert restored_xsec.height == original_xsec.height
        assert restored_xsec.width == original_xsec.width

    def test_missing_name_defaults_to_empty(self) -> None:
        fc = FuselageConfiguration.from_json_dict({})
        assert fc.name == ""

    def test_empty_xsecs_list(self) -> None:
        data = {"name": "empty", "asb_fuselage": {"name": "f", "xsecs": []}}
        fc = FuselageConfiguration.from_json_dict(data)
        assert fc.asb_fuselage is not None
        assert len(fc.asb_fuselage.xsecs) == 0


# ---------------------------------------------------------------------------
# File I/O: save_to_json / from_json
# ---------------------------------------------------------------------------

class TestFuselageConfigurationFileIO:
    """Tests for JSON file save/load."""

    def test_save_and_load_minimal(
        self, simple_fuselage: FuselageConfiguration, tmp_path
    ) -> None:
        path = str(tmp_path / "fuselage.json")
        simple_fuselage.save_to_json(path)
        assert os.path.exists(path)

        loaded = FuselageConfiguration.from_json(path)
        assert loaded.name == simple_fuselage.name

    def test_save_and_load_with_asb(
        self, fuselage_with_asb: FuselageConfiguration, tmp_path
    ) -> None:
        path = str(tmp_path / "fuselage_asb.json")
        fuselage_with_asb.save_to_json(path)

        loaded = FuselageConfiguration.from_json(path)
        assert loaded.name == fuselage_with_asb.name
        assert loaded.asb_fuselage is not None
        assert len(loaded.asb_fuselage.xsecs) == 3

    def test_saved_file_is_valid_json(
        self, fuselage_with_asb: FuselageConfiguration, tmp_path
    ) -> None:
        path = str(tmp_path / "valid.json")
        fuselage_with_asb.save_to_json(path)
        with open(path) as f:
            data = json.load(f)
        assert isinstance(data, dict)
        assert data["name"] == "asb_fuselage"

    def test_from_json_nonexistent_file_raises(self) -> None:
        with pytest.raises(FileNotFoundError):
            FuselageConfiguration.from_json("/nonexistent/path.json")


# ---------------------------------------------------------------------------
# from_step_file (requires cadquery + real STEP file -- mark as xfail)
# ---------------------------------------------------------------------------

class TestFuselageConfigurationFromStep:
    """Tests for from_step_file. These require cadquery and a real STEP file."""

    @pytest.mark.slow
    def test_from_step_file_missing_file_raises(self) -> None:
        """from_step_file should raise when the STEP file does not exist."""
        with pytest.raises(Exception):
            FuselageConfiguration.from_step_file(
                step_file="/nonexistent/fuselage.step"
            )
