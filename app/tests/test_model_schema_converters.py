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
    aeroplane_schema_to_airplane_configuration_async,
    aeroplane_schema_to_asb_airplane_async,
    fuselage_model_to_fuselage_config,
    wing_config_to_asb_wing_schema,
    wing_config_to_wing_model,
    wing_model_to_wing_config,
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

    result = wing_config_to_asb_wing_schema(wing_config=wing_config, wing_name="main-wing")

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

    wing_model = wing_config_to_wing_model(wing_config=wing_config, wing_name="main-wing")
    reconstructed = wing_model_to_wing_config(wing_model)

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
    """Unit-conversion (m → mm) regression test.

    Uses a purely planar wing (``z = 0`` on the tip xsec) so that
    the segment length recovered by ``WingConfiguration.from_asb``
    is exactly the y-component of the LE delta. A non-planar tip
    would trigger the ``from_asb`` cumulative-R_x heuristic (which
    interprets the z-offset as a dihedral rotation, by the
    convention that matches Case B / eHawk-style winglets) and
    report ``length = sqrt(dy² + dz²)`` with a corresponding
    non-zero ``dihedral_as_rotation_in_degrees``. That behaviour is
    exercised by the roundtrip harness in
    ``app/tests/test_wing_config_roundtrip.py``; this test focuses
    on the plain unit conversion.
    """
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
                xyz_le=[0.01, 0.5, 0.0],
                chord=0.15,
                twist=0.0,
                airfoil="./components/airfoils/mh32.dat",
            ),
        ],
    )
    wing_model = WingModel.from_dict(name="main-wing", data=wing_schema.model_dump())

    scaled_config = wing_model_to_wing_config(wing_model, scale=1000.0)

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

    config = wing_model_to_wing_config(wing_model, scale=1000.0)

    assert config.segments[0].spare_list is not None
    assert config.segments[0].spare_list[0].spare_vector is not None
    assert config.segments[0].spare_list[0].spare_origin is not None
    assert config.segments[1].spare_list is not None
    assert config.segments[1].spare_list[0].spare_vector is not None
    assert config.segments[1].spare_list[0].spare_origin is not None


def test_spare_origin_recomputed_when_scaled_gh352():
    """Regression for gh-352: spare_origin from DB (meters) must not leak into mm context.

    When _recompute_spare_vectors stores origin in meters and the CAD path
    rebuilds with scale=1000.0, the origin must be recomputed from mm-scale
    geometry — not used as-is from the DB.
    """
    wing_schema = schemas.AsbWingSchema(
        name="test-wing",
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
                        spare_origin=[0.05, 0.0, 0.003],
                    )
                ],
            ),
            schemas.WingXSecSchema(
                xyz_le=[0.0, 0.5, 0.0],
                chord=0.15,
                twist=0.0,
                airfoil="./components/airfoils/mh32.dat",
            ),
        ],
    )
    wing_model = WingModel.from_dict(name="test-wing", data=wing_schema.model_dump())

    config_mm = wing_model_to_wing_config(wing_model, scale=1000.0)
    spare = config_mm.segments[0].spare_list[0]

    assert spare.spare_origin is not None
    assert abs(spare.spare_origin.x) > 1.0, (
        f"spare_origin.x={spare.spare_origin.x} looks like meters, expected mm"
    )


def test_spare_origin_roundtrip_consistency_gh362():
    """Regression for gh-362: converting a wing twice must yield identical spare_origin.

    If spare_vector is not cleared alongside spare_origin before recomputation,
    the retained stale vector can cause the recomputed origin to drift.
    """
    wing_schema = schemas.AsbWingSchema(
        name="test-wing",
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
                xyz_le=[0.0, 0.5, 0.0],
                chord=0.15,
                twist=0.0,
                airfoil="./components/airfoils/mh32.dat",
            ),
        ],
    )
    wing_model = WingModel.from_dict(name="test-wing", data=wing_schema.model_dump())

    config_1 = wing_model_to_wing_config(wing_model, scale=1000.0)
    origin_1 = config_1.segments[0].spare_list[0].spare_origin
    vector_1 = config_1.segments[0].spare_list[0].spare_vector

    config_2 = wing_model_to_wing_config(wing_model, scale=1000.0)
    origin_2 = config_2.segments[0].spare_list[0].spare_origin
    vector_2 = config_2.segments[0].spare_list[0].spare_vector

    assert origin_1 is not None
    assert origin_2 is not None
    assert vector_1 is not None
    assert vector_2 is not None

    assert origin_1.x == pytest.approx(origin_2.x, abs=1e-6)
    assert origin_1.y == pytest.approx(origin_2.y, abs=1e-6)
    assert origin_1.z == pytest.approx(origin_2.z, abs=1e-6)

    assert vector_1.x == pytest.approx(vector_2.x, abs=1e-6)
    assert vector_1.y == pytest.approx(vector_2.y, abs=1e-6)
    assert vector_1.z == pytest.approx(vector_2.z, abs=1e-6)


def test_spare_origin_at_scale_1_matches_geometry_gh362():
    """Regression for gh-362: at scale=1.0 spare_origin must match meter-scale geometry.

    The spare at position_factor=0.25 on a 0.2m chord should have an x origin
    around 0.25 * 0.2 = 0.05m (at the quarter-chord).
    """
    wing_schema = schemas.AsbWingSchema(
        name="test-wing",
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
                xyz_le=[0.0, 0.5, 0.0],
                chord=0.15,
                twist=0.0,
                airfoil="./components/airfoils/mh32.dat",
            ),
        ],
    )
    wing_model = WingModel.from_dict(name="test-wing", data=wing_schema.model_dump())

    config = wing_model_to_wing_config(wing_model, scale=1.0)
    spare = config.segments[0].spare_list[0]

    assert spare.spare_origin is not None
    assert spare.spare_vector is not None

    # At scale=1.0, chord is 0.2m, position_factor=0.25 → x ≈ 0.05m
    assert spare.spare_origin.x == pytest.approx(0.05, abs=0.01), (
        f"spare_origin.x={spare.spare_origin.x}, expected ~0.05m at quarter-chord"
    )


def test_follow_mode_spare_roundtrip_consistency_gh362():
    """Regression for gh-362: follow-mode spares must be stable across repeated conversions."""
    wing_schema = schemas.AsbWingSchema(
        name="test-wing",
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
    wing_model = WingModel.from_dict(name="test-wing", data=wing_schema.model_dump())

    config_1 = wing_model_to_wing_config(wing_model, scale=1000.0)
    follow_1 = config_1.segments[1].spare_list[0]

    config_2 = wing_model_to_wing_config(wing_model, scale=1000.0)
    follow_2 = config_2.segments[1].spare_list[0]

    assert follow_1.spare_origin is not None
    assert follow_2.spare_origin is not None
    assert follow_1.spare_vector is not None
    assert follow_2.spare_vector is not None

    assert follow_1.spare_origin.x == pytest.approx(follow_2.spare_origin.x, abs=1e-6)
    assert follow_1.spare_origin.y == pytest.approx(follow_2.spare_origin.y, abs=1e-6)
    assert follow_1.spare_origin.z == pytest.approx(follow_2.spare_origin.z, abs=1e-6)

    assert follow_1.spare_vector.x == pytest.approx(follow_2.spare_vector.x, abs=1e-6)
    assert follow_1.spare_vector.y == pytest.approx(follow_2.spare_vector.y, abs=1e-6)
    assert follow_1.spare_vector.z == pytest.approx(follow_2.spare_vector.z, abs=1e-6)


def test_stale_spare_vector_discarded_on_recomputation_gh362():
    """Regression for gh-362: pre-populated spare_vector from DB must be discarded."""
    wing_schema = schemas.AsbWingSchema(
        name="test-wing",
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
                        spare_vector=[99.0, 99.0, 99.0],
                        spare_origin=[0.05, 0.0, 0.003],
                    )
                ],
            ),
            schemas.WingXSecSchema(
                xyz_le=[0.0, 0.5, 0.0],
                chord=0.15,
                twist=0.0,
                airfoil="./components/airfoils/mh32.dat",
            ),
        ],
    )
    wing_model = WingModel.from_dict(name="test-wing", data=wing_schema.model_dump())

    config = wing_model_to_wing_config(wing_model, scale=1000.0)
    spare = config.segments[0].spare_list[0]

    assert spare.spare_vector is not None
    assert spare.spare_vector.x != pytest.approx(99.0, abs=1.0), (
        "stale spare_vector was not discarded during recomputation"
    )
    assert abs(spare.spare_origin.x) > 1.0, (
        f"spare_origin.x={spare.spare_origin.x} looks like meters, expected mm"
    )


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

    asb_airplane = aeroplane_schema_to_asb_airplane_async(plane)
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
        aeroplane_schema_to_airplane_configuration_async(plane)


def test_aeroplane_schema_to_airplane_configuration_preserves_wing_details():
    wing_config = _create_test_wing_config()
    wing_schema = wing_config_to_asb_wing_schema(wing_config=wing_config, wing_name="main-wing")
    fuselage_schema = _create_test_fuselage_schema()
    plane = schemas.AeroplaneSchema(
        name="test-plane",
        total_mass_kg=3.0,
        wings={"main-wing": wing_schema},
        fuselages={"test-fuselage": fuselage_schema},
    )

    airplane_config = aeroplane_schema_to_airplane_configuration_async(plane)

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

    fuselage_config = fuselage_model_to_fuselage_config(fuselage_model)

    assert fuselage_config.name == "fuselage-a"
    assert fuselage_config.asb_fuselage is not None
    assert len(fuselage_config.asb_fuselage.xsecs) == 2
    assert fuselage_config.asb_fuselage.xsecs[1].height == pytest.approx(0.06)
