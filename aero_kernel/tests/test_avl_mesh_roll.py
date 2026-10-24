"""The AVL mesh with the roll devices driven: breaks, controls, hinges (ARCHITECTURE ch. 8.8)."""

import math
from itertools import pairwise
from typing import Any

import pytest
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.solvers.avl_mesh import MeshSurface, mesh_surfaces
from aero_kernel.tests.reference_fleet import FleetMember, reference_document


def fleet(member: FleetMember) -> AirplaneGeometry:
    return AirplaneGeometry.model_validate(reference_document(member))


def surfaces(airplane: AirplaneGeometry, n_wing: int, *, drive: bool) -> dict[str, MeshSurface]:
    return {s.name: s for s in mesh_surfaces(airplane, n_wing, lambda _a: 0, drive_roll=drive)}


def stations(surface: MeshSurface) -> list[float]:
    return [s.y for s in surface.sections]


def has(values: list[float], y: float) -> bool:
    return any(math.isclose(v, y, abs_tol=1e-6) for v in values)


def widths(values: list[float]) -> list[float]:
    return [b - a for a, b in pairwise(values)]


@pytest.mark.parametrize(
    ("member", "ends"),
    [(FleetMember.BRYAN, (0.063151, 0.2265)), (FleetMember.JAGUAR, (0.020446, 0.285559))],
)
@pytest.mark.parametrize("n", [24, 48])
def test_driven_stations_are_sine_to_tip_with_the_device_ends_exact(
    member: FleetMember, ends: tuple[float, float], n: int
) -> None:
    """One sine-to-tip distribution over the half span (Sspace -2 from root to tip, avl_doc 1043-1048)
    with n strips, the device ends exact, and strip widths that stay continuous across the ends."""
    main = stations(surfaces(fleet(member), n, drive=True)["Tragflaeche"])
    assert len(main) == n + 1
    assert main[0] == 0.0
    for y in ends:
        assert has(main, y)
    step = widths(main)
    assert all(w > 0.0 for w in step)
    for y in ends:
        index = next(i for i, v in enumerate(main) if math.isclose(v, y, abs_tol=1e-6))
        assert 0.8 < step[index] / step[index - 1] < 1.25  # no width jump at the end (Rule 2)
    assert step[-1] < step[0] / 3.0  # the strips bunch toward the tip


def test_sine_to_tip_hand_values() -> None:
    """Half span 0.6, 12 strips, device 0.2 .. 0.4: t of the ends is 2/pi asin(1/3) = 0.216321 and
    2/pi asin(2/3) = 0.464557, so the pieces get round(2.596) = 3, round(5.575) - 3 = 3 and 6 strips,
    t runs evenly in each, y = 0.6 sin(pi/2 t): y(1) = 0.6 sin(pi/2 0.216321/3) = 0.067822, in the
    device t = 0.216321 + 0.248236/3 = 0.299067 gives y = 0.271625 and t = 0.381812 y = 0.338669."""
    main = stations(surfaces(simple(), 12, drive=True)["Main"])
    assert len(main) == 13
    assert math.isclose(main[1], 0.067822, abs_tol=1e-6)
    assert math.isclose(main[3], 0.2, abs_tol=1e-9)
    assert math.isclose(main[4], 0.271625, abs_tol=1e-6)
    assert math.isclose(main[5], 0.338669, abs_tol=1e-6)
    assert math.isclose(main[6], 0.4, abs_tol=1e-9)
    assert math.isclose(main[-1], 0.6, abs_tol=1e-9)


@pytest.mark.parametrize(
    ("member", "y"), [(FleetMember.BRYAN, 0.063151), (FleetMember.JAGUAR, 0.020446)]
)
def test_tail_takes_the_wing_break_stations_inside_its_span(member: FleetMember, y: float) -> None:
    tail = stations(surfaces(fleet(member), 24, drive=True)["Hoehenleitwerk"])
    assert has(tail, y)
    clean = stations(surfaces(fleet(member), 24, drive=False)["Hoehenleitwerk"])
    assert not has(clean, y)


def wing_document(
    ys: list[float],
    device_at: list[int],
    hinges: list[tuple[float, float]],
    *,
    chords: list[float] | None = None,
    role: str = "aileron",
) -> dict[str, Any]:
    """A mirrored main wing; the devices sit on the given ribs with the given (root, tip) hinges."""
    sizes = chords or [0.2] * len(ys)
    sections: list[dict[str, Any]] = [
        {"xyz_le": [0.02 * k, y, 0.0], "chord": c, "twist": 0.0, "airfoil": "naca0012"}
        for k, (y, c) in enumerate(zip(ys, sizes, strict=True))
    ]
    for rib, (root, tip) in zip(device_at, hinges, strict=True):
        sections[rib]["trailing_edge_device"] = {
            "name": "ail",
            "role": role,
            "rel_chord_root": root,
            "rel_chord_tip": tip,
        }
    wing = {"name": "Main", "surface_type": "main_wing", "symmetric": True, "x_secs": sections}
    return {"name": "t", "wings": {"Main": wing}}


def simple(**kwargs: Any) -> AirplaneGeometry:
    return AirplaneGeometry.model_validate(
        wing_document([0.0, 0.2, 0.4, 0.6], [1], [(0.78, 0.80)], **kwargs)
    )


def test_break_inside_tail_tip_sliver_is_dropped_from_the_tail_only() -> None:
    """Wing half span 0.6 at 12 strips (step 0.05); tail half span 0.2, so its stations stop 0.015
    short of the tip (0.185). A device end at 0.19 is a wing station but never a tail station."""
    document = wing_document([0.0, 0.19, 0.4, 0.6], [1], [(0.78, 0.80)])
    tail = [
        {"xyz_le": [0.6, y, 0.0], "chord": 0.1, "twist": 0.0, "airfoil": "naca0012"}
        for y in (0.0, 0.2)
    ]
    document["wings"]["Tail"] = {
        "name": "Tail",
        "surface_type": "horizontal_tail",
        "symmetric": True,
        "x_secs": tail,
    }
    found = surfaces(AirplaneGeometry.model_validate(document), 12, drive=True)
    assert has(stations(found["Main"]), 0.19)
    assert not has(stations(found["Tail"]), 0.19)
    assert has(stations(found["Tail"]), 0.2)


def test_control_lines_on_every_station_of_the_device_span_inclusive() -> None:
    """The aileron covers y 0.2 .. 0.4 (rib 1, one segment): its two end stations and the ones
    between carry the control, the others none (AVL controls a strip only if both sections do)."""
    main = surfaces(simple(), 12, drive=True)["Main"]
    controlled = [s.y for s in main.sections if s.control is not None]
    assert has(controlled, 0.2)
    assert has(controlled, 0.4)
    assert all(0.2 - 1e-6 <= y <= 0.4 + 1e-6 for y in controlled)
    assert len(controlled) == sum(1 for y in stations(main) if 0.2 - 1e-6 <= y <= 0.4 + 1e-6)


def test_x_hinge_from_the_absolute_hinge_line_over_local_chord() -> None:
    """Tapered segment 0.2 -> 0.4: chords 0.20 / 0.10, leading edges x = 0.02 / 0.04, hinge 0.78 / 0.80.
    The hinge line runs from x = 0.02 + 0.78 * 0.20 = 0.176 to 0.04 + 0.80 * 0.10 = 0.120. At the
    station y = 0.3 the line is at 0.148, the leading edge at 0.03 and the chord 0.15, so
    x_hinge = (0.148 - 0.03) / 0.15 = 0.78666...; at the ends it is the stored hinge."""
    document = wing_document([0.0, 0.2, 0.4, 0.6], [1], [(0.78, 0.80)], chords=[0.2, 0.2, 0.1, 0.1])
    main = surfaces(AirplaneGeometry.model_validate(document), 12, drive=True)["Main"]
    by_y = {round(s.y, 5): s for s in main.sections if s.control is not None}
    for y, hinge in ((0.2, 0.78), (0.4, 0.80)):
        control = by_y[y].control
        assert control is not None
        assert math.isclose(control.x_hinge, hinge, rel_tol=1e-12)
    middle = by_y[0.27163]  # a station between the two ends (sine to tip, 12 strips)
    assert middle.control is not None
    fraction = (0.271625 - 0.2) / 0.2
    line = 0.176 + fraction * (0.120 - 0.176)
    leading_edge = 0.02 + fraction * 0.02
    chord = 0.2 - fraction * 0.1
    assert math.isclose(middle.control.x_hinge, (line - leading_edge) / chord, rel_tol=1e-4)


def test_control_gain_minus_written_side() -> None:
    """The oriented chain is written on +y: the gain is -1 (a positive command raises the right
    trailing edge); the writer adds SgnDup -1 for the mirrored half."""
    main = surfaces(simple(), 12, drive=True)["Main"]
    assert {s.control.gain for s in main.sections if s.control is not None} == {-1.0}


def minus_y(document: dict[str, Any]) -> dict[str, Any]:
    wing = document["wings"]["Main"]
    for section in wing["x_secs"]:
        section["xyz_le"][1] = -section["xyz_le"][1]
    return document


def test_minus_y_stored_wing_writes_the_same_avl_file() -> None:
    plus = wing_document([0.0, 0.2, 0.4, 0.6], [1], [(0.78, 0.80)])
    minus = minus_y(wing_document([0.0, 0.2, 0.4, 0.6], [1], [(0.78, 0.80)]))
    a = mesh_surfaces(AirplaneGeometry.model_validate(plus), 12, lambda _a: 0, drive_roll=True)
    b = mesh_surfaces(AirplaneGeometry.model_validate(minus), 12, lambda _a: 0, drive_roll=True)
    assert a == b


def test_tip_first_stored_wing_writes_the_same_avl_file() -> None:
    """The same physical aileron (y 0.2 .. 0.4, hinge 0.78 at 0.2 and 0.80 at 0.4) stored tip first:
    ribs 0.6, 0.4, 0.2, 0.0 with the device on rib 1 (segment 0.4 -> 0.2), root hinge 0.80."""
    forward = wing_document([0.0, 0.2, 0.4, 0.6], [1], [(0.78, 0.80)])
    reversed_ = wing_document([0.6, 0.4, 0.2, 0.0], [1], [(0.80, 0.78)])
    for document in (forward, reversed_):
        for section in document["wings"]["Main"]["x_secs"]:
            section["xyz_le"][0] = 0.02 * {0.0: 0, 0.2: 1, 0.4: 2, 0.6: 3}[section["xyz_le"][1]]
    a = mesh_surfaces(AirplaneGeometry.model_validate(forward), 12, lambda _a: 0, drive_roll=True)
    b = mesh_surfaces(AirplaneGeometry.model_validate(reversed_), 12, lambda _a: 0, drive_roll=True)
    assert len(a[0].sections) == len(b[0].sections)
    for sa, sb in zip(a[0].sections, b[0].sections, strict=True):
        assert math.isclose(sa.y, sb.y, abs_tol=1e-9)
        assert (sa.control is None) == (sb.control is None)
        if sa.control is not None and sb.control is not None:
            assert math.isclose(sa.control.x_hinge, sb.control.x_hinge, rel_tol=1e-9)
            assert sa.control.gain == sb.control.gain


def two_segment_document(second_root: float) -> dict[str, Any]:
    """A driven device over two segments whose hinge is 0.78 at the end of the first and
    ``second_root`` at the start of the second."""
    return wing_document([0.0, 0.2, 0.4, 0.6], [1, 2], [(0.75, 0.78), (second_root, 0.80)])


def test_discontinuous_hinge_of_a_driven_device_is_unsupported() -> None:
    airplane = AirplaneGeometry.model_validate(two_segment_document(0.70))
    with pytest.raises(FormulaError) as raised:
        mesh_surfaces(airplane, 12, lambda _a: 0, drive_roll=True)
    assert raised.value.category is ErrorCategory.UNSUPPORTED_CONFIGURATION
    assert raised.value.code == "hinge_line_discontinuous"
    assert raised.value.detail["wing"] == "Main"


def test_continuous_hinge_of_a_driven_device_is_accepted() -> None:
    airplane = AirplaneGeometry.model_validate(two_segment_document(0.78))
    main = mesh_surfaces(airplane, 12, lambda _a: 0, drive_roll=True)[0]
    assert any(s.control is not None for s in main.sections)


def test_discontinuous_hinge_of_an_undriven_device_is_ignored() -> None:
    document = wing_document(
        [0.0, 0.2, 0.4, 0.6], [1, 2], [(0.75, 0.78), (0.70, 0.80)], role="elevator"
    )
    airplane = AirplaneGeometry.model_validate(document)
    for drive in (True, False):
        main = mesh_surfaces(airplane, 12, lambda _a: 0, drive_roll=drive)[0]
        assert all(s.control is None for s in main.sections)


def test_a_roll_device_off_the_main_wing_is_unsupported() -> None:
    document = wing_document([0.0, 0.2, 0.4, 0.6], [], [])
    tail = [
        {
            "xyz_le": [0.6, y, 0.0],
            "chord": 0.1,
            "twist": 0.0,
            "airfoil": "naca0012",
            **(
                {
                    "trailing_edge_device": {
                        "name": "elevon",
                        "role": "elevon",
                        "rel_chord_root": 0.7,
                        "rel_chord_tip": 0.7,
                    }
                }
                if y == 0.0
                else {}
            ),
        }
        for y in (0.0, 0.2)
    ]
    document["wings"]["Tail"] = {
        "name": "Tail",
        "surface_type": "horizontal_tail",
        "symmetric": True,
        "x_secs": tail,
    }
    with pytest.raises(FormulaError) as raised:
        mesh_surfaces(AirplaneGeometry.model_validate(document), 12, lambda _a: 0, drive_roll=True)
    assert raised.value.code == "unsupported_layout"
    assert raised.value.detail["wing"] == "Tail"
