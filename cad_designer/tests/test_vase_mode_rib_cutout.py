"""The vase-mode rib layout loop ends for every input (gh-1481).

``VaseModeWingCreator._rib_cutout`` lays rib rows from root to tip until a row
reaches the end of the segment. When the spar support is wider than the rib
field between spar and trailing-edge offset line, each row lies inboard of the
one before; the loop then never reaches the tip. It has to stop with an error
that names the cause instead of running forever.
"""

from pathlib import Path

import pytest

pytestmark = [pytest.mark.requires_cadquery]

REPO_ROOT = Path(__file__).resolve().parents[2]
AIRFOIL = str(REPO_ROOT / "components" / "airfoils" / "mh32.dat")

CHORD_MM = 162.0
LENGTH_MM = 200.0
PRINTER_WALL_THICKNESS_MM = 0.42
LEADING_EDGE_OFFSET_MM = 0.1 * CHORD_MM
TRAILING_EDGE_OFFSET_MM = 0.15 * CHORD_MM

# A spar parallel to the trailing edge: every row steps back by the same
# amount, so the loop ran without end.
SPAR_PARALLEL = (0.0, 1.0, 0.0)
# A spar inclined to the trailing edge: the steps shrink, the loop ended only
# when an edge became too short for OCCT ("BRepAdaptor_Curve::No geometry").
SPAR_INCLINED = (0.0368, 0.9992, 0.0)


def _rectangular_wing(spar_width: float, spar_vector: tuple[float, float, float]):
    from cad_designer.airplane.aircraft_topology.wing.Airfoil import Airfoil
    from cad_designer.airplane.aircraft_topology.wing.Spare import Spare
    from cad_designer.airplane.aircraft_topology.wing.WingConfiguration import WingConfiguration

    return WingConfiguration(
        nose_pnt=(0, 0, 0),
        root_airfoil=Airfoil(airfoil=AIRFOIL, chord=CHORD_MM, incidence=0),
        length=LENGTH_MM,
        sweep=0,
        tip_airfoil=Airfoil(chord=CHORD_MM, incidence=0),
        spare_list=[
            Spare(
                spare_support_dimension_width=spar_width,
                spare_support_dimension_height=4.42,
                spare_position_factor=0.25,
                spare_vector=spar_vector,
            )
        ],
    )


def _rib_cutout(wing_config):
    import cad_designer.cq_plugins  # noqa: F401 — registers Sketch.segmentToEdge
    from cad_designer.airplane.creator.wing.VaseModeWingCreator import VaseModeWingCreator

    return VaseModeWingCreator._rib_cutout(
        segment=0,
        wing_config=wing_config,
        printer_wall_thickness=PRINTER_WALL_THICKNESS_MM,
        leading_edge_offset=LEADING_EDGE_OFFSET_MM,
        trailing_edge_offset=TRAILING_EDGE_OFFSET_MM,
        minimum_rib_angle=45,
    )


@pytest.mark.timeout(20)
@pytest.mark.parametrize("spar_vector", [SPAR_PARALLEL, SPAR_INCLINED], ids=["parallel", "inclined"])
@pytest.mark.parametrize("spar_width", [200.0, 4420.0], ids=["200mm", "4420mm"])
def test_rib_layout_that_cannot_reach_the_tip_is_an_error(spar_width, spar_vector):
    """4420 mm is the eHawk spar of 4.42 mm stored a thousand times too large."""
    wing_config = _rectangular_wing(spar_width, spar_vector)

    with pytest.raises(ValueError, match="segment 0.*no progress") as error:
        _rib_cutout(wing_config)

    assert f"{spar_width:.2f} mm" in str(error.value)


# spar width [mm] -> (edges in the sketch, leading_edge_start [mm], trailing_edge_start [mm]),
# measured on main d0237407 before the guard was added.
VALID_LAYOUTS = {
    4.42: (12, 18.840732873074867, 126.00000000000007),
    40.0: (12, 18.342336301728654, 90.42000000000003),
}


@pytest.mark.timeout(20)
@pytest.mark.parametrize("spar_width", sorted(VALID_LAYOUTS), ids=["regular-spar", "wide-spar"])
def test_rib_layout_that_reaches_the_tip_is_unchanged(spar_width):
    expected_edges, expected_leading_edge_start, expected_trailing_edge_start = VALID_LAYOUTS[spar_width]
    wing_config = _rectangular_wing(spar_width, SPAR_PARALLEL)

    sketch, leading_edge_start, trailing_edge_start, lower_part, _ = _rib_cutout(wing_config)

    assert len(sketch._edges) == expected_edges
    assert lower_part is True
    assert leading_edge_start == pytest.approx(expected_leading_edge_start, abs=1e-9)
    assert trailing_edge_start == pytest.approx(expected_trailing_edge_start, abs=1e-9)
