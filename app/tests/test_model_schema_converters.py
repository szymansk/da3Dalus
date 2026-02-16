import asyncio
import os

import aerosandbox as asb
import pytest
from pydantic import ValidationError

from app import schemas
from app.converters.model_schema_converters import (
    aeroplaneSchemaToAirplaneConfiguration_async,
    aeroplaneSchemaToAsbAirplane_async,
    wingConfigToAsbWingSchema,
    wingConfigToWingModel,
    wingModelToWingConfig,
)
from cad_designer.airplane.aircraft_topology.wing import Spare, TrailingEdgeDevice, WingConfiguration


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
    wing_config = WingConfiguration.from_asb(xsecs=xsecs, symmetric=True)

    wing_config.segments[0].wing_segment_type = "root"
    wing_config.segments[0].number_interpolation_points = 123
    wing_config.segments[0].spare_list = [
        Spare(
            spare_support_dimension_width=4.42,
            spare_support_dimension_height=4.42,
            spare_position_factor=0.25,
            spare_length=120.0,
            spare_start=0.0,
            spare_vector=(0.0, 1.0, 0.0),
            spare_origin=(40.5, 0.0, 2.6),
            spare_mode="standard",
        )
    ]
    wing_config.segments[0].trailing_edge_device = TrailingEdgeDevice(
        name="aileron",
        rel_chord_root=0.78,
        rel_chord_tip=0.83,
        positive_deflection_deg=25.0,
        negative_deflection_deg=20.0,
        symmetric=False,
        servo=1,
    )
    return wing_config


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

    assert result.x_secs[0].x_sec_type == "root"
    assert result.x_secs[0].number_interpolation_points == 123
    assert result.x_secs[0].spare_list is not None
    assert result.x_secs[0].trailing_edge_device is not None
    assert result.x_secs[0].control_surface is not None

    # The terminal x-sec must not carry segment details.
    assert result.x_secs[-1].x_sec_type is None
    assert result.x_secs[-1].tip_type is None
    assert result.x_secs[-1].number_interpolation_points is None
    assert result.x_secs[-1].spare_list is None
    assert result.x_secs[-1].trailing_edge_device is None


def test_wing_config_to_wing_model_and_back_preserves_details():
    wing_config = _create_test_wing_config()

    wing_model = wingConfigToWingModel(wing_config=wing_config, wing_name="main-wing")
    reconstructed = wingModelToWingConfig(wing_model)

    assert reconstructed.symmetric is True
    assert len(reconstructed.segments) == 1

    segment = reconstructed.segments[0]
    assert segment.wing_segment_type == "root"
    assert segment.number_interpolation_points == 123

    assert segment.spare_list is not None
    assert len(segment.spare_list) == 1
    assert segment.spare_list[0].spare_support_dimension_width == pytest.approx(4.42)
    assert segment.spare_list[0].spare_mode == "standard"

    assert segment.trailing_edge_device is not None
    assert segment.trailing_edge_device.name == "aileron"
    assert segment.trailing_edge_device.rel_chord_root == pytest.approx(0.78)
    assert segment.trailing_edge_device.rel_chord_tip == pytest.approx(0.83)
    assert segment.trailing_edge_device.symmetric is False


def test_ted_projection_to_asb_uses_rel_chord_root():
    wing = schemas.AsbWingSchema(
        name="main-wing",
        symmetric=True,
        x_secs=[
            schemas.WingXSecSchema(
                xyz_le=[0.0, 0.0, 0.0],
                chord=0.2,
                twist=1.0,
                airfoil="./components/airfoils/mh32.dat",
                trailing_edge_device=schemas.TrailingEdgeDeviceDetailSchema(
                    name="aileron",
                    rel_chord_root=0.73,
                    rel_chord_tip=0.81,
                    symmetric=False,
                ),
                control_surface=schemas.ControlSurfaceSchema(
                    name="aileron",
                    hinge_point=0.9,
                    symmetric=False,
                    deflection=8.0,
                ),
            ),
            schemas.WingXSecSchema(
                xyz_le=[0.02, 0.4, 0.01],
                chord=0.15,
                twist=0.0,
                airfoil="./components/airfoils/mh32.dat",
            ),
        ],
    )
    plane = schemas.AeroplaneSchema(
        name="test-plane",
        total_mass_kg=2.5,
        wings={"main-wing": wing},
    )

    asb_airplane = asyncio.run(aeroplaneSchemaToAsbAirplane_async(plane))
    control_surface = asb_airplane.wings[0].xsecs[0].control_surfaces[0]
    assert control_surface.hinge_point == pytest.approx(0.73)


def test_asb_wing_schema_rejects_segment_details_on_last_xsec():
    with pytest.raises(ValidationError):
        schemas.AsbWingSchema(
            name="invalid-wing",
            symmetric=True,
            x_secs=[
                schemas.WingXSecSchema(
                    xyz_le=[0.0, 0.0, 0.0],
                    chord=0.2,
                    twist=1.0,
                    airfoil="./components/airfoils/mh32.dat",
                    x_sec_type="root",
                ),
                schemas.WingXSecSchema(
                    xyz_le=[0.02, 0.4, 0.01],
                    chord=0.15,
                    twist=0.0,
                    airfoil="./components/airfoils/mh32.dat",
                    x_sec_type="tip",
                ),
            ],
        )


def test_aeroplane_schema_to_airplane_configuration_requires_mass():
    wing = schemas.AsbWingSchema(
        name="main-wing",
        symmetric=True,
        x_secs=[
            schemas.WingXSecSchema(
                xyz_le=[0.0, 0.0, 0.0],
                chord=0.2,
                twist=1.0,
                airfoil="./components/airfoils/mh32.dat",
            ),
            schemas.WingXSecSchema(
                xyz_le=[0.02, 0.4, 0.01],
                chord=0.15,
                twist=0.0,
                airfoil="./components/airfoils/mh32.dat",
            ),
        ],
    )
    plane = schemas.AeroplaneSchema(name="test-plane", wings={"main-wing": wing})

    with pytest.raises(ValueError):
        asyncio.run(aeroplaneSchemaToAirplaneConfiguration_async(plane))


def test_aeroplane_schema_to_airplane_configuration_preserves_wing_details():
    wing_config = _create_test_wing_config()
    wing_schema = wingConfigToAsbWingSchema(wing_config=wing_config, wing_name="main-wing")
    plane = schemas.AeroplaneSchema(
        name="test-plane",
        total_mass_kg=3.0,
        wings={"main-wing": wing_schema},
    )

    airplane_config = asyncio.run(aeroplaneSchemaToAirplaneConfiguration_async(plane))

    assert airplane_config.total_mass == pytest.approx(3.0)
    assert len(airplane_config.wings) == 1
    segment = airplane_config.wings[0].segments[0]
    assert segment.spare_list is not None
    assert len(segment.spare_list) == 1
    assert segment.trailing_edge_device is not None
    assert segment.trailing_edge_device.rel_chord_tip == pytest.approx(0.83)
