"""The AVL mesh with the roll devices driven: breaks, controls, hinges (ARCHITECTURE ch. 8.8)."""

import math
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


@pytest.mark.parametrize("member", list(FleetMember))
def test_clean_mesh_and_file_unchanged(member: FleetMember) -> None:
    """Without driving the roll devices the mesh is today's: no breaks, no controls."""
    airplane = fleet(member)
    clean = mesh_surfaces(airplane, 24, lambda _a: 0)
    assert clean == mesh_surfaces(airplane, 24, lambda _a: 0, drive_roll=False)
    assert all(section.control is None for surface in clean for section in surface.sections)


def test_device_ends_are_stations_and_close_uniform_stations_are_dropped() -> None:
    """BRYAN, 24 strips (step 0.011371 m): the aileron ends 0.063151 and 0.2265 are stations; the
    uniform neighbours 0.056855 and 0.068226 (0.55 / 0.45 step) stay, 0.22742 (0.08 step) goes."""
    main = stations(surfaces(fleet(FleetMember.BRYAN), 24, drive=True)["Tragflaeche"])
    assert len(main) == 25 + 2 - 1
    for y in (0.063151, 0.2265, 0.056855, 0.068226):
        assert has(main, y)
    assert not has(main, 0.22742)
    refined = stations(surfaces(fleet(FleetMember.BRYAN), 48, drive=True)["Tragflaeche"])
    assert len(refined) == 49 + 2 - 2  # at 48: 0.06254 (0.11 step) and 0.22742 (0.16 step) go
    assert has(refined, 0.063151)
    assert not has(refined, 0.06254)
    assert not has(refined, 0.22742)


def test_the_jaguar_stations() -> None:
    """JAGUAR, 24 strips (step 0.013004 m): 0.020446 is inserted with 0.013004 and 0.026008 kept
    (0.57 / 0.43 step), 0.285559 is inserted and 0.286088 (0.04 step) dropped."""
    main = stations(surfaces(fleet(FleetMember.JAGUAR), 24, drive=True)["Tragflaeche"])
    assert len(main) == 25 + 2 - 1
    for y in (0.020446, 0.013004, 0.026008, 0.285559):
        assert has(main, y)
    assert not has(main, 0.286088)
    refined = stations(surfaces(fleet(FleetMember.JAGUAR), 48, drive=True)["Tragflaeche"])
    assert len(refined) == 49 + 2 - 2
    assert not has(refined, 0.019506)
    assert not has(refined, 0.286088)


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
    by_y = {round(s.y, 6): s for s in main.sections if s.control is not None}
    for y, hinge in ((0.2, 0.78), (0.4, 0.80)):
        control = by_y[y].control
        assert control is not None
        assert math.isclose(control.x_hinge, hinge, rel_tol=1e-12)
    station = by_y[0.3]  # 12 strips of 0.05 m put a station at 0.3
    assert station.control is not None
    assert math.isclose(station.control.x_hinge, 0.118 / 0.15, rel_tol=1e-12)


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
