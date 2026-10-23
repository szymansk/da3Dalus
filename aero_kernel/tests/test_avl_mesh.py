"""The aligned AVL mesh: stations of the wing, the tail and the fins (AVL rule 1; AVL_CONVERGENCE.md)."""

import math

import pytest
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.solvers.avl_mesh import MeshSurface, mesh_surfaces

NSPAN = 12


def same(actual: list[float], expected: list[float]) -> bool:
    """Whether two station lists agree to a nanometre."""
    return len(actual) == len(expected) and all(
        math.isclose(a, e, abs_tol=1e-9) for a, e in zip(actual, expected, strict=True)
    )


def wing(
    name: str,
    surface_type: str,
    sections: list[tuple[float, float, float, float]],
    *,
    symmetric: bool = True,
) -> dict[str, object]:
    """A surface from (x_le, y, z, chord) rows, root first."""
    return {
        "name": name,
        "symmetric": symmetric,
        "surface_type": surface_type,
        "x_secs": [
            {"xyz_le": [x, y, z], "chord": c, "twist": 1.0, "airfoil": "naca0012"}
            for x, y, z, c in sections
        ],
    }


def airplane() -> AirplaneGeometry:
    """Wing y 0..0.6 with a middle section at 0.4; tail y 0..0.2 (middle section at 0.15); fin z 0..0.15."""
    return AirplaneGeometry.model_validate(
        {
            "name": "t",
            "wings": {
                "Fin": wing(
                    "Fin",
                    "vertical_tail",
                    [(0.5, 0.0, 0.0, 0.12), (0.55, 0.0, 0.15, 0.06)],
                    symmetric=False,
                ),
                "Tail": wing(
                    "Tail",
                    "horizontal_tail",
                    [(0.5, 0.0, 0.0, 0.1), (0.52, 0.15, 0.0, 0.08), (0.53, 0.2, 0.0, 0.05)],
                ),
                "Main": wing(
                    "Main",
                    "main_wing",
                    [(0.0, 0.0, 0.0, 0.2), (0.02, 0.4, 0.0, 0.15), (0.04, 0.6, 0.0, 0.1)],
                ),
            },
        }
    )


def surfaces() -> dict[str, MeshSurface]:
    return {s.name: s for s in mesh_surfaces(airplane(), NSPAN, lambda _airfoil: 0)}


def ys(surface: MeshSurface) -> list[float]:
    return [s.y for s in surface.sections]


def test_the_surfaces_come_main_wing_first_then_tail_then_the_rest() -> None:
    assert [s.name for s in mesh_surfaces(airplane(), NSPAN, lambda _a: 0)] == [
        "Main",
        "Tail",
        "Fin",
    ]


def test_the_main_wing_has_a_uniform_distribution_whatever_its_sections() -> None:
    """12 strips over 0.6 m (step 0.05 m) already contain the section at 0.4 m; the tip is 0.6 m."""
    stations = ys(surfaces()["Main"])
    assert len(stations) == NSPAN + 1
    assert same(stations, [0.05 * k for k in range(13)])


def test_the_tail_strip_boundaries_lie_on_the_wings_stations() -> None:
    """Over the tail span (0..0.2 m) the tail uses the wing's stations (0, 0.05, 0.1, 0.15) and its tip
    (0.2 m), none of its own section breaks (0.15 m is a wing station by chance)."""
    wing_stations = ys(surfaces()["Main"])
    tail = ys(surfaces()["Tail"])
    assert same(tail, [0.0, 0.05, 0.1, 0.15, 0.2])
    inside = [y for y in tail if y < 0.2 - 1e-9]
    assert all(any(math.isclose(y, w, abs_tol=1e-9) for w in wing_stations) for y in inside)


def test_a_sliver_strip_next_to_the_tip_is_dropped() -> None:
    """A wing station closer than 0.3 steps to the tail tip would leave a sliver strip against it."""
    plane = AirplaneGeometry.model_validate(
        {
            "name": "t",
            "wings": {
                "Main": wing("Main", "main_wing", [(0.0, 0.0, 0.0, 0.2), (0.0, 0.6, 0.0, 0.1)]),
                "Tail": wing(
                    "Tail", "horizontal_tail", [(0.5, 0.0, 0.0, 0.1), (0.5, 0.205, 0.0, 0.05)]
                ),
            },
        }
    )
    tail = ys(next(s for s in mesh_surfaces(plane, NSPAN, lambda _a: 0) if s.name == "Tail"))
    assert same(tail, [0.0, 0.05, 0.1, 0.15, 0.205])  # 0.20 is within 0.3 step


def test_the_fin_strip_width_equals_the_wings_step() -> None:
    """Fin height 0.15 m, wing step 0.05 m: max(2, round(3)) = 3 strips of 0.05 m along z."""
    fin = surfaces()["Fin"]
    zs = [s.z for s in fin.sections]
    assert same(zs, [0.0, 0.05, 0.1, 0.15])
    assert not fin.symmetric


def test_a_fin_is_meshed_uniformly_whatever_its_sections() -> None:
    plane = AirplaneGeometry.model_validate(
        {
            "name": "t",
            "wings": {
                "Main": wing("Main", "main_wing", [(0.0, 0.0, 0.0, 0.2), (0.0, 0.6, 0.0, 0.1)]),
                "Tail": wing(
                    "Tail", "horizontal_tail", [(0.5, 0.0, 0.0, 0.1), (0.5, 0.2, 0.0, 0.05)]
                ),
                "Fin": wing(
                    "Fin",
                    "vertical_tail",
                    [(0.5, 0.0, 0.0, 0.1), (0.4, 0.0, 0.07, 0.12), (0.5, 0.0, 0.15, 0.05)],
                    symmetric=False,
                ),
            },
        }
    )
    fin = next(s for s in mesh_surfaces(plane, NSPAN, lambda _a: 0) if s.name == "Fin")
    assert same([s.z for s in fin.sections], [0.0, 0.05, 0.1, 0.15])


def test_a_low_fin_gets_at_least_two_strips() -> None:
    plane = AirplaneGeometry.model_validate(
        {
            "name": "t",
            "wings": {
                "Main": wing("Main", "main_wing", [(0.0, 0.0, 0.0, 0.2), (0.0, 0.6, 0.0, 0.1)]),
                "Tail": wing(
                    "Tail", "horizontal_tail", [(0.5, 0.0, 0.0, 0.1), (0.5, 0.2, 0.0, 0.05)]
                ),
                "Fin": wing(
                    "Fin",
                    "vertical_tail",
                    [(0.5, 0.0, 0.0, 0.1), (0.5, 0.0, 0.02, 0.05)],
                    symmetric=False,
                ),
            },
        }
    )
    fin = next(s for s in mesh_surfaces(plane, NSPAN, lambda _a: 0) if s.name == "Fin")
    assert len(fin.sections) == 3


def test_a_station_interpolates_the_chord_leading_edge_and_twist_linearly() -> None:
    main = surfaces()["Main"]
    at = {round(s.y, 6): s for s in main.sections}
    middle = at[
        0.2
    ]  # halfway between the root (0.2 m chord, x 0) and the section at 0.4 (0.15, x 0.02)
    assert math.isclose(middle.chord, 0.175, abs_tol=1e-12)
    assert math.isclose(middle.x, 0.01, abs_tol=1e-12)
    assert math.isclose(middle.twist, 1.0, abs_tol=1e-12)


def test_the_airfoil_of_a_station_is_that_of_the_section_it_lies_in() -> None:
    plane = AirplaneGeometry.model_validate(
        {
            "name": "t",
            "wings": {
                "Main": {
                    "name": "Main",
                    "symmetric": True,
                    "surface_type": "main_wing",
                    "x_secs": [
                        {"xyz_le": [0.0, y, 0.0], "chord": 0.2, "twist": 0.0, "airfoil": name}
                        for y, name in ((0.0, "naca2412"), (0.3, "naca0012"), (0.6, "naca0012"))
                    ],
                }
            },
        }
    )
    index = {"naca2412": 0, "naca0012": 1}
    (main,) = mesh_surfaces(plane, 6, lambda airfoil: index[str(airfoil)])
    by_y = {round(s.y, 6): s.airfoil for s in main.sections}
    assert by_y[0.0] == by_y[0.2] == 0  # inboard of the 0.3 m section
    assert by_y[0.3] == by_y[0.4] == 1


def test_a_root_stored_off_the_centreline_starts_at_the_centreline() -> None:
    """BRYAN's root section lies at y = -0.25 mm: a strip across its own mirror image skews AVL."""
    plane = AirplaneGeometry.model_validate(
        {
            "name": "t",
            "wings": {
                "Main": wing("Main", "main_wing", [(0.0, -0.0003, 0.0, 0.2), (0.0, 0.6, 0.0, 0.1)])
            },
        }
    )
    (main,) = mesh_surfaces(plane, NSPAN, lambda _a: 0)
    assert main.sections[0].y == 0.0
    assert math.isclose(main.sections[0].chord, 0.2 - 0.1 * 0.0003 / 0.6003, abs_tol=1e-9)


def test_a_root_stored_off_the_centreline_on_the_far_side_is_extended_to_it() -> None:
    """JAGUAR's root lies at y = +1.1 mm: held at that y, the mirrored halves leave a 2.2 mm slit that
    made the neutral point drift by 1.9 % MAC per span doubling (0.1325, 0.1346, 0.1359 m)."""
    plane = AirplaneGeometry.model_validate(
        {
            "name": "t",
            "wings": {
                "Main": wing("Main", "main_wing", [(0.0, 0.0011, 0.0, 0.2), (0.0, 0.6, 0.0, 0.1)])
            },
        }
    )
    (main,) = mesh_surfaces(plane, NSPAN, lambda _a: 0)
    assert main.sections[0].y == 0.0
    assert main.sections[0].chord == 0.2


def stored(
    surface_type: str,
    name: str,
    rows: list[tuple[float, float, float, float]],
    airfoils: list[str],
    *,
    mirrored_to_negative: bool = False,
    tip_first: bool = False,
) -> dict[str, object]:
    """A surface from root-first rows (x_le, y, z, chord), stored the other way round if asked."""
    sign = -1.0 if mirrored_to_negative else 1.0
    sections = [
        {"xyz_le": [x, sign * y, z], "chord": c, "twist": 1.5 * k, "airfoil": airfoils[k]}
        for k, (x, y, z, c) in enumerate(rows)
    ]
    if tip_first:
        sections.reverse()
    return {"name": name, "symmetric": True, "surface_type": surface_type, "x_secs": sections}


MAIN_ROWS = [(0.0, 0.0, 0.0, 0.2), (0.02, 0.4, 0.01, 0.15), (0.04, 0.6, 0.02, 0.1)]
TAIL_ROWS = [(0.5, 0.0, 0.0, 0.1), (0.52, 0.15, 0.0, 0.08), (0.53, 0.2, 0.0, 0.05)]
AIRFOILS = ["naca2412", "naca0012", "naca0010"]
INDEX = {"naca2412": 0, "naca0012": 1, "naca0010": 2}


def meshes(**storage: bool) -> tuple[MeshSurface, ...]:
    plane = AirplaneGeometry.model_validate(
        {
            "name": "t",
            "wings": {
                "Main": stored("main_wing", "Main", MAIN_ROWS, AIRFOILS, **storage),
                "Tail": stored("horizontal_tail", "Tail", TAIL_ROWS, AIRFOILS, **storage),
            },
        }
    )
    return mesh_surfaces(plane, NSPAN, lambda airfoil: INDEX[str(airfoil)])


@pytest.mark.parametrize(
    "storage",
    [
        {"mirrored_to_negative": True},
        {"tip_first": True},
        {"mirrored_to_negative": True, "tip_first": True},
    ],
)
def test_the_mesh_does_not_depend_on_how_the_chain_is_stored(storage: dict[str, bool]) -> None:
    """The same wing stored on -y or tip first gave Xnp 8.6 % MAC lower, or collapsed to y = 0."""
    reference = meshes()
    other = meshes(**storage)
    assert len(other) == len(reference)
    for want, got in zip(reference, other, strict=True):
        assert got.name == want.name
        assert len(got.sections) == len(want.sections)
        for a, b in zip(want.sections, got.sections, strict=True):
            for field in ("x", "y", "z", "chord", "twist"):
                assert math.isclose(getattr(a, field), getattr(b, field), abs_tol=1e-9), field
            assert a.airfoil == b.airfoil


def test_a_fin_stored_from_the_tip_down_is_oriented_root_first() -> None:
    fin_rows = [(0.5, 0.0, 0.0, 0.1), (0.52, 0.0, 0.07, 0.08), (0.53, 0.0, 0.15, 0.05)]
    both: list[AirplaneGeometry] = []
    for tip_first in (False, True):
        fin = stored(
            "vertical_tail",
            "Fin",
            [(x, y, z, c) for x, y, z, c in fin_rows],
            AIRFOILS,
            tip_first=tip_first,
        )
        fin["symmetric"] = False
        both.append(
            AirplaneGeometry.model_validate(
                {
                    "name": "t",
                    "wings": {
                        "Main": stored("main_wing", "Main", MAIN_ROWS, AIRFOILS),
                        "Tail": stored("horizontal_tail", "Tail", TAIL_ROWS, AIRFOILS),
                        "Fin": fin,
                    },
                }
            )
        )
    first, second = (
        next(s for s in mesh_surfaces(p, NSPAN, lambda a: INDEX[str(a)]) if s.name == "Fin")
        for p in both
    )
    assert [s.z for s in first.sections] == [s.z for s in second.sections]
    assert first.sections[0].z == 0.0
    assert [s.chord for s in first.sections] == [s.chord for s in second.sections]


def test_a_chain_that_folds_back_is_refused() -> None:
    plane = AirplaneGeometry.model_validate(
        {
            "name": "t",
            "wings": {
                "Main": wing(
                    "Main",
                    "main_wing",
                    [(0.0, 0.0, 0.0, 0.2), (0.0, 0.4, 0.0, 0.15), (0.0, 0.2, 0.0, 0.1)],
                )
            },
        }
    )
    with pytest.raises(FormulaError) as raised:
        mesh_surfaces(plane, NSPAN, lambda _a: 0)
    assert raised.value.category is ErrorCategory.UNSUPPORTED_CONFIGURATION
