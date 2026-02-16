import os

import aerosandbox as asb
import pytest

from app.converters.model_schema_converters import (
    wingConfigToAsbWingSchema,
    wingConfigToWingModel,
)
from cad_designer.airplane.aircraft_topology.wing import WingConfiguration


def _create_test_wing_config() -> WingConfiguration:
    airfoil_path = os.path.abspath("components/airfoils/mh32.dat")
    xsecs = [
        asb.WingXSec(
            xyz_le=[0.0, 0.0, 0.0],
            chord=0.18,
            twist=2.0,
            airfoil=asb.Airfoil(name=airfoil_path),
        ),
        asb.WingXSec(
            xyz_le=[0.02, 0.5, 0.03],
            chord=0.14,
            twist=0.5,
            airfoil=asb.Airfoil(name=airfoil_path),
        ),
    ]
    return WingConfiguration.from_asb(xsecs=xsecs, symmetric=True)


def test_wing_config_to_asb_wing_schema():
    wing_config = _create_test_wing_config()

    result = wingConfigToAsbWingSchema(wing_config=wing_config, wing_name="main-wing")

    assert result.name == "main-wing"
    assert result.symmetric is True
    assert len(result.x_secs) == 2
    assert result.x_secs[0].xyz_le[0] == pytest.approx(0.0, abs=1e-3)
    assert result.x_secs[1].xyz_le[1] == pytest.approx(0.5, abs=1e-3)
    assert result.x_secs[0].chord == pytest.approx(0.18)
    assert result.x_secs[0].airfoil == "./components/airfoils/mh32.dat"


def test_wing_config_to_wing_model():
    wing_config = _create_test_wing_config()

    wing_model = wingConfigToWingModel(wing_config=wing_config, wing_name="main-wing")

    assert wing_model.name == "main-wing"
    assert wing_model.symmetric is True
    assert len(wing_model.x_secs) == 2
    assert wing_model.x_secs[0].airfoil == "./components/airfoils/mh32.dat"
    assert wing_model.x_secs[1].chord == pytest.approx(0.14)


def test_roundtrip_asb_wing_to_wing_config_and_back():
    airfoil_path = os.path.abspath("components/airfoils/mh32.dat")
    original_xsecs = [
        asb.WingXSec(
            xyz_le=[0.0, 0.0, 0.0],
            chord=0.24,
            twist=2.5,
            airfoil=asb.Airfoil(name=airfoil_path),
        ),
        asb.WingXSec(
            xyz_le=[0.006, 0.18, 0.008],
            chord=0.21,
            twist=1.8,
            airfoil=asb.Airfoil(name=airfoil_path),
        ),
        asb.WingXSec(
            xyz_le=[0.020, 0.38, 0.018],
            chord=0.18,
            twist=0.9,
            airfoil=asb.Airfoil(name=airfoil_path),
        ),
        asb.WingXSec(
            xyz_le=[0.045, 0.62, 0.038],
            chord=0.14,
            twist=-0.2,
            airfoil=asb.Airfoil(name=airfoil_path),
        ),
        asb.WingXSec(
            xyz_le=[0.075, 0.92, 0.075],
            chord=0.11,
            twist=-1.0,
            airfoil=asb.Airfoil(name=airfoil_path),
        ),
    ]
    wing_config = WingConfiguration.from_asb(xsecs=original_xsecs, symmetric=True)

    result = wingConfigToAsbWingSchema(wing_config=wing_config, wing_name="roundtrip-wing")

    assert result.name == "roundtrip-wing"
    assert result.symmetric is True
    assert len(result.x_secs) == len(original_xsecs)

    for idx, original in enumerate(original_xsecs):
        converted = result.x_secs[idx]
        assert converted.chord == pytest.approx(float(original.chord), abs=2e-3)
        assert converted.twist == pytest.approx(float(original.twist), abs=2e-2)
        assert converted.xyz_le[0] == pytest.approx(float(original.xyz_le[0]), abs=2e-3)
        assert converted.xyz_le[1] == pytest.approx(float(original.xyz_le[1]), abs=2e-3)
        assert converted.xyz_le[2] == pytest.approx(float(original.xyz_le[2]), abs=4e-3)

    # Structural sanity checks after roundtrip: spanwise stations increase and chord tapers.
    y_positions = [xs.xyz_le[1] for xs in result.x_secs]
    chords = [xs.chord for xs in result.x_secs]
    assert y_positions == sorted(y_positions)
    assert chords == sorted(chords, reverse=True)
