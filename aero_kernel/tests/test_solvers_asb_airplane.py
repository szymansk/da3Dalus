"""The one conversion of the geometry format to an AeroSandbox airplane (ADR 0022)."""

import pytest
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.solvers.asb_airplane import to_asb_airplane
from aero_kernel.tests.asb_fakes import FakeAirfoil, FakeAirplane, install_fake_aerosandbox

NACA = "naca2412"
CONTOUR = [[1.0, 0.0], [0.5, 0.05], [0.0, 0.0], [0.5, -0.04], [1.0, 0.0]]


def geometry() -> AirplaneGeometry:
    """Two wings: a symmetric one with a NACA root and an inline tip, and a fin on one side."""
    section = {"twist": 0.0, "dihedral": 3.0}
    return AirplaneGeometry.model_validate(
        {
            "name": "t",
            "xyz_ref": [0.1, 0.0, 0.02],
            "wings": {
                "Main": {
                    "name": "Main",
                    "symmetric": True,
                    "x_secs": [
                        {**section, "xyz_le": [0.0, 0.0, 0.0], "chord": 0.2, "airfoil": NACA},
                        {
                            **section,
                            "twist": -1.5,
                            "xyz_le": [0.02, 0.4, 0.01],
                            "chord": 0.1,
                            "airfoil": {"coordinates": CONTOUR},
                            "trailing_edge_device": {
                                "name": "ail",
                                "rel_chord_root": 0.8,
                                "rel_chord_tip": 0.8,
                                "positive_deflection_deg": 25.0,
                                "negative_deflection_deg": 25.0,
                                "deflection_deg": 12.0,
                            },
                        },
                        {**section, "xyz_le": [0.04, 0.8, 0.02], "chord": 0.05, "airfoil": NACA},
                    ],
                },
                "Fin": {
                    "name": "Fin",
                    "symmetric": False,
                    "x_secs": [
                        {**section, "xyz_le": [0.5, 0.0, 0.0], "chord": 0.1, "airfoil": NACA},
                        {**section, "xyz_le": [0.52, 0.0, 0.1], "chord": 0.05, "airfoil": NACA},
                    ],
                },
            },
        }
    )


@pytest.fixture(autouse=True)
def fake(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_aerosandbox(monkeypatch)


def converted() -> FakeAirplane:
    airplane = to_asb_airplane(geometry())
    assert isinstance(airplane, FakeAirplane)
    return airplane


def test_the_airplane_carries_name_and_reference_point() -> None:
    kwargs = converted().kwargs
    assert kwargs["name"] == "t"
    assert list(kwargs["xyz_ref"]) == [0.1, 0.0, 0.02]


def test_wings_keep_their_order_name_and_symmetry() -> None:
    wings = converted().kwargs["wings"]
    assert [(w.kwargs["name"], w.kwargs["symmetric"]) for w in wings] == [
        ("Main", True),
        ("Fin", False),
    ]


def test_each_section_keeps_leading_edge_chord_and_twist() -> None:
    (main, _) = converted().kwargs["wings"]
    sections = main.kwargs["xsecs"]
    assert [list(s.kwargs["xyz_le"]) for s in sections] == [
        [0.0, 0.0, 0.0],
        [0.02, 0.4, 0.01],
        [0.04, 0.8, 0.02],
    ]
    assert [s.kwargs["chord"] for s in sections] == [0.2, 0.1, 0.05]
    assert [s.kwargs["twist"] for s in sections] == [0.0, -1.5, 0.0]


def test_a_naca_designation_and_inline_coordinates_become_airfoils() -> None:
    (main, _) = converted().kwargs["wings"]
    root, tip, _ = (s.kwargs["airfoil"] for s in main.kwargs["xsecs"])
    assert isinstance(root, FakeAirfoil)
    assert (root.name, root.coordinates) == (NACA, None)
    assert isinstance(tip, FakeAirfoil)
    assert tip.coordinates.tolist() == CONTOUR


def test_only_the_geometry_is_passed_never_a_control_device_or_the_dihedral_field() -> None:
    """Devices stay at 0 deg (ch. 8.11); xyz_le already carries the dihedral."""
    (main, _) = converted().kwargs["wings"]
    for section in main.kwargs["xsecs"]:
        assert set(section.kwargs) == {"xyz_le", "chord", "twist", "airfoil"}


def test_an_airplane_without_wings_converts_to_an_airplane_without_wings() -> None:
    airplane = to_asb_airplane(AirplaneGeometry.model_validate({"name": "empty"}))
    assert isinstance(airplane, FakeAirplane)
    assert airplane.kwargs["wings"] == []
