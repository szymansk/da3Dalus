"""gh-1481: backward-mode spars survive WingConfiguration -> DB model -> WingConfiguration.

A ``standard_backward`` / ``orthogonal_backward`` spar re-aims the spar it
continues: ``WingConfiguration.add_segment`` points the anchor spar (the last
spar of that index that is not ``follow``) at the tip of the backward segment
and lets every segment in between follow it. The model -> config converter
rebuilds spar geometry from the stored ``spare_mode``, so it has to apply the
same rule; treating a backward spar as a plain ``standard`` spar of its own
segment bends the whole spar run.

No CAD shapes are built here, only spar origins and vectors.
"""

import os

import pytest

pytest.importorskip("aerosandbox")
pytest.importorskip("cadquery")

pytestmark = [
    pytest.mark.requires_cadquery,
    pytest.mark.requires_aerosandbox,
]

from app.converters.model_schema_converters import (  # noqa: E402
    wing_config_to_wing_model,
    wing_model_to_wing_config,
)
from cad_designer.airplane.aircraft_topology.wing import (  # noqa: E402
    Spare,
    WingConfiguration,
)
from cad_designer.airplane.aircraft_topology.wing.Airfoil import Airfoil  # noqa: E402

_SPAR_SIZE_MM = 4.42
# mm: far below any spar tolerance, far above float noise of the two builds.
_ORIGIN_TOLERANCE_MM = 1e-3
_VECTOR_TOLERANCE = 1e-6


def _spar(**kwargs) -> Spare:
    return Spare(
        spare_support_dimension_width=_SPAR_SIZE_MM,
        spare_support_dimension_height=_SPAR_SIZE_MM,
        **kwargs,
    )


def _swept_wing_with_backward_spar(backward_mode: str) -> WingConfiguration:
    """Four swept, tapered segments (mm); the last one closes the spar run backwards."""
    airfoil_path = os.path.abspath("components/airfoils/mh32.dat")
    wing_config = WingConfiguration(
        nose_pnt=(0, 0, 0),
        root_airfoil=Airfoil(
            airfoil=airfoil_path, chord=160.0, dihedral_as_rotation_in_degrees=1, incidence=0
        ),
        length=20.0,
        sweep=0,
        tip_airfoil=Airfoil(chord=160.0, incidence=0),
        spare_list=[_spar(spare_position_factor=0.25)],
    )
    wing_config.add_segment(
        length=200,
        sweep=5,
        tip_airfoil=Airfoil(chord=150, incidence=0),
        spare_list=[_spar(spare_mode="follow")],
    )
    wing_config.add_segment(
        length=250,
        sweep=15,
        tip_airfoil=Airfoil(chord=120, incidence=0),
        spare_list=[_spar(spare_mode="follow")],
    )
    wing_config.add_segment(
        length=100,
        sweep=20,
        tip_airfoil=Airfoil(chord=90, incidence=0),
        spare_list=[_spar(spare_mode=backward_mode)],
    )
    return wing_config


def _round_trip(wing_config: WingConfiguration) -> WingConfiguration:
    """Same conversions as POST /from-wingconfig followed by the CAD worker's rebuild."""
    wing_model = wing_config_to_wing_model(
        wing_config=wing_config, wing_name="main_wing", surface_type="main_wing", scale=0.001
    )
    return wing_model_to_wing_config(wing_model, scale=1000.0)


@pytest.mark.parametrize("backward_mode", ["standard_backward", "orthogonal_backward"])
def test_backward_spar_run_survives_the_model_round_trip(backward_mode: str):
    original = _swept_wing_with_backward_spar(backward_mode)

    rebuilt = _round_trip(original)

    assert len(rebuilt.segments) == len(original.segments)
    for segment_index, (before, after) in enumerate(
        zip(original.segments, rebuilt.segments, strict=True)
    ):
        spar_before = before.spare_list[0]
        spar_after = after.spare_list[0]
        assert spar_after.spare_mode == spar_before.spare_mode
        vector_error = (spar_after.spare_vector - spar_before.spare_vector).Length
        origin_error = (spar_after.spare_origin - spar_before.spare_origin).Length
        assert vector_error < _VECTOR_TOLERANCE, (
            f"segment {segment_index}: spar vector {spar_before.spare_vector.toTuple()} "
            f"became {spar_after.spare_vector.toTuple()}"
        )
        assert origin_error < _ORIGIN_TOLERANCE_MM, (
            f"segment {segment_index}: spar origin {spar_before.spare_origin.toTuple()} "
            f"became {spar_after.spare_origin.toTuple()}"
        )


def test_backward_spar_run_is_one_straight_line_after_the_round_trip():
    """The property the rib cut relies on: one spar axis through all segments."""
    rebuilt = _round_trip(_swept_wing_with_backward_spar("standard_backward"))

    spars = [segment.spare_list[0] for segment in rebuilt.segments]
    anchor = spars[0]
    for segment_index, spar in enumerate(spars[1:], start=1):
        assert (spar.spare_vector - anchor.spare_vector).Length < _VECTOR_TOLERANCE
        off_axis = (spar.spare_origin - anchor.spare_origin).cross(anchor.spare_vector).Length
        assert off_axis < _ORIGIN_TOLERANCE_MM, (
            f"segment {segment_index}: spar origin lies {off_axis} mm off the spar axis"
        )


def test_backward_spar_without_a_spar_to_continue_is_placed_as_standard():
    """A backward spar in the root segment has nothing to re-aim; it stays a standard spar."""
    original = _swept_wing_with_backward_spar("standard_backward")
    original.segments[0].spare_list[0].spare_mode = "standard_backward"
    for segment in original.segments[1:]:
        segment.spare_list = None

    rebuilt = _round_trip(original)

    root_plane_y = rebuilt.get_wing_workplane(0).plane.yDir
    spar = rebuilt.segments[0].spare_list[0]
    assert spar.spare_origin is not None
    assert spar.spare_vector.dot(root_plane_y) > 0.99
