import asyncio
import os

import pytest

# Heavy libraries — skip the whole module cleanly on systems where they
# are not installed (e.g. linux/aarch64 per pyproject.toml markers).
asb = pytest.importorskip("aerosandbox")
pytest.importorskip("cadquery")

pytestmark = [
    pytest.mark.requires_cadquery,
    pytest.mark.requires_aerosandbox,
]

from pydantic import ValidationError  # noqa: E402

from app import schemas  # noqa: E402
from app.converters.model_schema_converters import (  # noqa: E402
    aeroplaneSchemaToAirplaneConfiguration_async,
    aeroplaneSchemaToAsbAirplane_async,
    fuselageModelToFuselageConfig,
    wingConfigToAsbWingSchema,
    wingConfigToWingModel,
    wingModelToWingConfig,
)
from app.models.aeroplanemodel import FuselageModel, WingModel  # noqa: E402
from cad_designer.airplane.aircraft_topology.wing import (  # noqa: E402
    Spare,
    TrailingEdgeDevice,
    WingConfiguration,
)


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


def _create_test_fuselage_schema() -> schemas.FuselageSchema:
    return schemas.FuselageSchema(
        name="test-fuselage",
        x_secs=[
            schemas.FuselageXSecSuperEllipseSchema(
                xyz=[0.0, 0.0, 0.0],
                a=0.08,
                b=0.08,
                n=2.0,
            ),
            schemas.FuselageXSecSuperEllipseSchema(
                xyz=[0.4, 0.0, 0.0],
                a=0.05,
                b=0.05,
                n=2.0,
            ),
        ],
    )


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
    assert segment.root_airfoil.airfoil == "./components/airfoils/mh32.dat"
    assert segment.tip_airfoil.airfoil == "./components/airfoils/mh32.dat"

    assert segment.spare_list is not None
    assert len(segment.spare_list) == 1
    assert segment.spare_list[0].spare_support_dimension_width == pytest.approx(4.42)
    assert segment.spare_list[0].spare_mode == "standard"

    assert segment.trailing_edge_device is not None
    assert segment.trailing_edge_device.name == "aileron"
    assert segment.trailing_edge_device.rel_chord_root == pytest.approx(0.78)
    assert segment.trailing_edge_device.rel_chord_tip == pytest.approx(0.83)
    assert segment.trailing_edge_device.symmetric is False


def test_wing_model_to_wing_config_scales_geometry_for_cad():
    wing_schema = schemas.AsbWingSchema(
        name="main-wing",
        symmetric=True,
        x_secs=[
            schemas.WingXSecSchema(
                xyz_le=[0.0, 0.0, 0.0],
                chord=0.2,
                twist=0.0,
                airfoil="./components/airfoils/mh32.dat",
            ),
            schemas.WingXSecSchema(
                xyz_le=[0.01, 0.5, 0.02],
                chord=0.15,
                twist=0.0,
                airfoil="./components/airfoils/mh32.dat",
            ),
        ],
    )
    wing_model = WingModel.from_dict(name="main-wing", data=wing_schema.model_dump())

    scaled_config = wingModelToWingConfig(wing_model, scale=1000.0)

    assert scaled_config.segments[0].root_airfoil.chord == pytest.approx(200.0)
    assert scaled_config.segments[0].tip_airfoil.chord == pytest.approx(150.0)
    assert scaled_config.segments[0].length == pytest.approx(500.0)


def test_wing_model_to_wing_config_resolves_sparse_vectors_for_standard_and_follow():
    wing_schema = schemas.AsbWingSchema(
        name="main-wing",
        symmetric=True,
        x_secs=[
            schemas.WingXSecSchema(
                xyz_le=[0.0, 0.0, 0.0],
                chord=0.2,
                twist=0.0,
                airfoil="./components/airfoils/mh32.dat",
                spare_list=[
                    schemas.SpareDetailSchema(
                        spare_support_dimension_width=4.42,
                        spare_support_dimension_height=4.42,
                        spare_position_factor=0.25,
                        spare_mode="standard",
                    )
                ],
            ),
            schemas.WingXSecSchema(
                xyz_le=[0.01, 0.4, 0.01],
                chord=0.16,
                twist=0.0,
                airfoil="./components/airfoils/mh32.dat",
                spare_list=[
                    schemas.SpareDetailSchema(
                        spare_support_dimension_width=4.42,
                        spare_support_dimension_height=4.42,
                        spare_position_factor=0.25,
                        spare_mode="follow",
                    )
                ],
            ),
            schemas.WingXSecSchema(
                xyz_le=[0.02, 0.7, 0.02],
                chord=0.12,
                twist=0.0,
                airfoil="./components/airfoils/mh32.dat",
            ),
        ],
    )
    wing_model = WingModel.from_dict(name="main-wing", data=wing_schema.model_dump())

    config = wingModelToWingConfig(wing_model, scale=1000.0)

    assert config.segments[0].spare_list is not None
    assert config.segments[0].spare_list[0].spare_vector is not None
    assert config.segments[0].spare_list[0].spare_origin is not None
    assert config.segments[1].spare_list is not None
    assert config.segments[1].spare_list[0].spare_vector is not None
    assert config.segments[1].spare_list[0].spare_origin is not None


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
                    deflection_deg=6.0,
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
    assert control_surface.deflection == pytest.approx(6.0)


def test_control_surface_only_input_is_persisted_as_ted():
    wing_schema = schemas.AsbWingSchema(
        name="main-wing",
        symmetric=True,
        x_secs=[
            schemas.WingXSecSchema(
                xyz_le=[0.0, 0.0, 0.0],
                chord=0.2,
                twist=1.0,
                airfoil="./components/airfoils/mh32.dat",
                control_surface=schemas.ControlSurfaceSchema(
                    name="flap",
                    hinge_point=0.67,
                    symmetric=True,
                    deflection=9.5,
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

    wing_model = WingModel.from_dict(name="main-wing", data=wing_schema.model_dump())
    ted = wing_model.x_secs[0].detail.trailing_edge_device

    assert ted is not None
    assert ted.name == "flap"
    assert ted.rel_chord_root == pytest.approx(0.67)
    assert ted.rel_chord_tip == pytest.approx(0.67)
    assert ted.deflection_deg == pytest.approx(9.5)
    assert wing_model.x_secs[0].control_surface is not None
    assert wing_model.x_secs[0].control_surface.deflection == pytest.approx(9.5)


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
    fuselage_schema = _create_test_fuselage_schema()
    plane = schemas.AeroplaneSchema(
        name="test-plane",
        total_mass_kg=3.0,
        wings={"main-wing": wing_schema},
        fuselages={"test-fuselage": fuselage_schema},
    )

    airplane_config = asyncio.run(aeroplaneSchemaToAirplaneConfiguration_async(plane))

    assert airplane_config.total_mass == pytest.approx(3.0)
    assert len(airplane_config.wings) == 1
    segment = airplane_config.wings[0].segments[0]
    assert segment.spare_list is not None
    assert len(segment.spare_list) == 1
    assert segment.trailing_edge_device is not None
    assert segment.trailing_edge_device.rel_chord_tip == pytest.approx(0.83)
    assert airplane_config.fuselages is not None
    assert len(airplane_config.fuselages) == 1
    assert airplane_config.fuselages[0].name == "test-fuselage"
    assert airplane_config.fuselages[0].asb_fuselage is not None
    assert len(airplane_config.fuselages[0].asb_fuselage.xsecs) == 2


def test_fuselage_model_to_fuselage_config():
    fuselage_model = FuselageModel.from_dict(
        name="fuselage-a",
        data={
            "x_secs": [
                {"xyz": [0.0, 0.0, 0.0], "a": 0.1, "b": 0.08, "n": 2.0},
                {"xyz": [0.5, 0.0, 0.0], "a": 0.06, "b": 0.05, "n": 2.0},
            ]
        },
    )

    fuselage_config = fuselageModelToFuselageConfig(fuselage_model)

    assert fuselage_config.name == "fuselage-a"
    assert fuselage_config.asb_fuselage is not None
    assert len(fuselage_config.asb_fuselage.xsecs) == 2
    assert fuselage_config.asb_fuselage.xsecs[1].height == pytest.approx(0.06)
