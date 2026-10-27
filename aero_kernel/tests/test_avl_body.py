"""The fuselages as AVL bodies: area-equivalent round sections, the body file and the BODY text."""

import math
from typing import Any

import pytest
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.geometry import AirplaneGeometry, FuselageXSecSuperEllipse
from aero_kernel.solvers.avl_body import (
    body_file_text,
    equivalent_radius,
    mesh_bodies,
    section_area,
)
from aero_kernel.solvers.avl_writer import (
    BODY_NODES,
    BODY_SPACING,
    LateralOutput,
    avl_geometry,
    body_file_name,
    parse_lateral_output,
)
from aero_kernel.tests.formula_builders import all_near, close, near
from aero_kernel.tests.mesh_helpers import mesh_surfaces
from aero_kernel.tests.np_builders import CONVENTIONAL, airplane_with


def section(
    x: float,
    a: float,
    b: float,
    n: float,
    n_lower: float | None = None,
    y: float = 0.0,
    z: float = 0.0,
) -> dict[str, Any]:
    document: dict[str, Any] = {"xyz": [x, y, z], "a": a, "b": b, "n": n}
    if n_lower is not None:
        document["n_lower"] = n_lower
    return document


def with_fuselages(**fuselages: Any) -> AirplaneGeometry:
    dumped = airplane_with(*CONVENTIONAL).model_dump(mode="json")
    dumped["fuselages"] = {
        name: {"name": name, "x_secs": sections, "symmetric": symmetric}
        for name, (sections, symmetric) in fuselages.items()
    }
    return AirplaneGeometry.model_validate(dumped)


def sec(**kwargs: Any) -> FuselageXSecSuperEllipse:
    return FuselageXSecSuperEllipse.model_validate(section(**kwargs))


def test_an_ellipse_has_the_area_pi_a_b_and_a_circle_pi_r_squared() -> None:
    assert close(section_area(sec(x=0.0, a=0.03, b=0.02, n=2.0)), math.pi * 0.03 * 0.02, 1e-12)
    assert close(equivalent_radius(sec(x=0.0, a=0.03, b=0.03, n=2.0)), 0.03, 1e-12)


def test_a_rectangle_like_section_has_the_area_4_a_b_in_the_limit_of_a_large_exponent() -> None:
    assert close(section_area(sec(x=0.0, a=0.03, b=0.02, n=400.0)), 4 * 0.03 * 0.02, 5e-3)


def test_a_diamond_has_the_area_2_a_b() -> None:
    """n = 1: |y/a| + |z/b| = 1 is a rhombus of the diagonals 2a and 2b."""
    assert close(section_area(sec(x=0.0, a=0.03, b=0.02, n=1.0)), 2 * 0.03 * 0.02, 1e-12)


def test_the_two_halves_have_their_own_exponents() -> None:
    """Upper half an ellipse (n = 2), lower half a diamond (n = 1): half of each area."""
    found = section_area(sec(x=0.0, a=0.03, b=0.02, n=2.0, n_lower=1.0))
    assert close(found, 0.5 * (math.pi * 0.03 * 0.02 + 2 * 0.03 * 0.02), 1e-12)


def test_a_point_section_has_no_area_and_no_radius() -> None:
    assert equivalent_radius(sec(x=0.0, a=0.0, b=0.0, n=2.0)) == 0.0


def test_a_fuselage_becomes_a_body_with_stations_from_the_nose_and_the_area_weighted_axis() -> None:
    plane = with_fuselages(
        Rumpf=(
            [
                section(0.1, 0.0, 0.0, 2.0, z=0.0),
                section(0.3, 0.02, 0.02, 2.0, z=0.01),
                section(0.5, 0.02, 0.02, 2.0, z=0.03),
                section(0.7, 0.0, 0.0, 2.0, z=0.0),
            ],
            False,
        )
    )
    (body,) = mesh_bodies(plane)
    assert body.name == "Rumpf"
    assert body.stations[0] == (0.0, 0.0)
    assert all_near([x for x, _ in body.stations], [0.0, 0.2, 0.4, 0.6])
    assert near(body.stations[1][1], 0.02)
    # the two nose and tail points have no area: the axis is the mean of the two round sections
    assert all_near(body.origin, (0.1, 0.0, 0.02))
    assert near(body.axis_offset, 0.02)  # the point sections lie 0.02 off the axis


def test_sections_stored_tail_first_are_sorted_by_x() -> None:
    plane = with_fuselages(
        Rumpf=([section(0.5, 0.0, 0.0, 2.0), section(0.2, 0.02, 0.02, 2.0)], False)
    )
    (body,) = mesh_bodies(plane)
    assert body.origin[0] == 0.2
    assert near(body.stations[1][0], 0.3)


def test_an_airplane_without_fuselages_has_no_bodies() -> None:
    assert mesh_bodies(airplane_with(*CONVENTIONAL)) == ()


@pytest.mark.parametrize(
    ("sections", "symmetric", "match"),
    [
        ([section(0.0, 0.02, 0.02, 2.0), section(0.0, 0.01, 0.01, 2.0)], False, "same x"),
        ([section(0.0, 0.0, 0.0, 2.0), section(0.1, 0.0, 0.0, 2.0)], False, "no cross-section"),
        ([section(0.0, 0.02, 0.02, 2.0), section(0.1, 0.01, 0.01, 2.0)], True, "mirrored"),
    ],
)
def test_a_fuselage_avl_cannot_hold_is_unsupported(
    sections: list[dict[str, Any]], symmetric: bool, match: str
) -> None:
    plane = with_fuselages(Rumpf=(sections, symmetric))
    with pytest.raises(FormulaError, match=match) as raised:
        mesh_bodies(plane)
    assert raised.value.category is ErrorCategory.UNSUPPORTED_CONFIGURATION


def test_the_body_file_runs_from_the_tail_over_the_top_to_the_nose_and_back_underneath() -> None:
    plane = with_fuselages(
        Rumpf=(
            [
                section(0.0, 0.0, 0.0, 2.0),
                section(0.2, 0.02, 0.02, 2.0),
                section(0.4, 0.0, 0.0, 2.0),
            ],
            False,
        )
    )
    (body,) = mesh_bodies(plane)
    lines = body_file_text(body).splitlines()
    assert lines[0] == "Rumpf"
    rows = [[float(v) for v in line.split()] for line in lines[1:]]
    expected = [(0.4, 0.0), (0.2, 0.02), (0.0, 0.0), (0.2, -0.02), (0.4, 0.0)]
    assert len(rows) == len(expected)
    for row, wanted in zip(rows, expected, strict=True):
        assert all_near(row, wanted)


def test_the_geometry_file_names_the_body_its_nodes_its_nose_and_its_outline_file() -> None:
    plane = with_fuselages(
        Rumpf=([section(0.1, 0.0, 0.0, 2.0), section(0.5, 0.0, 0.0, 2.0)], False)
    )
    plane = AirplaneGeometry.model_validate(
        {
            **plane.model_dump(mode="json"),
            "fuselages": {
                "Rumpf": {
                    "name": "Rumpf",
                    "x_secs": [
                        section(0.1, 0.0, 0.0, 2.0, z=0.01),
                        section(0.3, 0.02, 0.02, 2.0, z=0.01),
                        section(0.5, 0.0, 0.0, 2.0, z=0.01),
                    ],
                }
            },
        }
    )
    surfaces = mesh_surfaces(plane, 4, lambda _a: 0)
    text = avl_geometry(
        surfaces,
        [1.09],
        n_chord=10,
        s_ref=0.28,
        c_ref=0.2,
        b_ref=1.4,
        bodies=mesh_bodies(plane),
    )
    lines = text.splitlines()
    at = lines.index("BODY")
    assert lines[at + 1] == "Rumpf"
    assert lines[at + 3] == f"{BODY_NODES}   {BODY_SPACING}"
    assert lines[at + 4 : at + 8] == ["TRANSLATE", "0.1 0.0 0.01", "BFIL", body_file_name(0)]
    assert "BODY" not in avl_geometry(
        surfaces, [1.09], n_chord=10, s_ref=0.28, c_ref=0.2, b_ref=1.4
    )


LATERAL = """
  CLtot =   0.50000
 x' mom.  Cl'|    Cla =  -0.000000    Clb =  -0.049200
 z' mom.  Cn'|    Cna =  -0.000000    Cnb =   0.070835
 x' mom.  Cl'|    Clp =  -0.548576    Clq =  -0.000000    Clr =   0.109040
 z' mom.  Cn'|    Cnp =  -0.041814    Cnq =   0.000000    Cnr =  -0.057228
 Clb Cnr / Clr Cnb  =   0.364537    (  > 1 if spirally stable )
"""


def test_the_lateral_derivatives_are_read_from_the_stability_axis_block() -> None:
    assert parse_lateral_output(LATERAL) == LateralOutput(
        cl=0.5,
        c_l_beta=-0.0492,
        c_n_beta=0.070835,
        c_l_p=-0.548576,
        c_n_p=-0.041814,
        c_l_r=0.10904,
        c_n_r=-0.057228,
    )


def test_a_missing_derivative_is_no_result() -> None:
    assert parse_lateral_output(LATERAL.replace("Cnr", "Cxx")) is None
