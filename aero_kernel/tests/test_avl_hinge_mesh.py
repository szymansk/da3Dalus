"""The AVL mesh of the hinge-moment procedure: one control per surface and half, explicit halves."""

import pytest
from aero_kernel.build import shipped_build
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.geometry import Airfoil, AirplaneGeometry
from aero_kernel.rules import Rules
from aero_kernel.solvers.avl_hinge import HingeMesh, hinge_mesh
from aero_kernel.solvers.avl_mesh import MeshSurface
from aero_kernel.solvers.avl_writer import control_order
from aero_kernel.tests.formula_builders import near
from aero_kernel.tests.hinge_builders import (
    conventional,
    device,
    v_tail_plane,
    wing_document,
)

SPLIT = (12, 8)


def mesh_of(airplane: AirplaneGeometry, role: str, n_wing: int = 12) -> HingeMesh:
    """The hinge mesh with the canon's join tolerance."""
    join = Rules(shipped_build().model).value("hinge-line-continuity", "join_tolerance")
    numbers: dict[Airfoil, int] = {}

    def number(airfoil: Airfoil) -> int:
        return numbers.setdefault(airfoil, len(numbers))

    return hinge_mesh(airplane, role, n_wing, number, join_tolerance_m=join, split_n_chord=SPLIT)


def controls_by_key(mesh: HingeMesh) -> dict[str, tuple[str, int]]:
    return {c.key: (c.name, c.sign) for c in mesh.controls}


def written(mesh: HingeMesh, name: str) -> list[tuple[MeshSurface, int]]:
    """Every surface piece that declares the control ``name`` on some station, with the count."""
    found: list[tuple[MeshSurface, int]] = []
    for surface in mesh.surfaces:
        count = sum(any(c.name == name for c in s.controls()) for s in surface.sections)
        if count:
            found.append((surface, count))
    return found


def test_the_aileron_role_has_one_control_per_half_with_opposite_signs() -> None:
    mesh = mesh_of(conventional(), "aileron")
    assert controls_by_key(mesh) == {
        "Main wing.aileron_right": ("c01", -1),
        "Main wing.aileron_left": ("c02", 1),
    }


def test_only_the_devices_of_the_role_are_controls() -> None:
    assert list(controls_by_key(mesh_of(conventional(), "elevator"))) == [
        "Tail.elevator_right",
        "Tail.elevator_left",
    ]
    assert list(controls_by_key(mesh_of(conventional(), "rudder"))) == ["Fin.rudder"]
    assert controls_by_key(mesh_of(conventional(), "flap")) == {}


def test_an_unmirrored_fin_has_one_control_without_a_side_and_a_positive_sign() -> None:
    assert controls_by_key(mesh_of(conventional(), "rudder")) == {"Fin.rudder": ("c01", 1)}


def test_a_dual_role_surface_is_a_control_of_each_of_its_roles() -> None:
    plane = conventional(main={1: device("elevon", "elevon", 0.75)}, tail={}, fin={})
    aileron = controls_by_key(mesh_of(plane, "aileron"))
    elevator = controls_by_key(mesh_of(plane, "elevator"))
    assert list(aileron) == list(elevator) == ["Main wing.elevon_right", "Main wing.elevon_left"]
    assert [s for _, s in aileron.values()] == [-1, 1]
    assert [s for _, s in elevator.values()] == [1, 1]


def test_a_ruddervator_is_antisymmetric_as_a_rudder_and_symmetric_as_an_elevator() -> None:
    plane = v_tail_plane()
    assert [s for _, s in controls_by_key(mesh_of(plane, "rudder")).values()] == [1, -1]
    assert [s for _, s in controls_by_key(mesh_of(plane, "elevator")).values()] == [1, 1]


def test_a_device_name_falls_back_to_its_label_and_then_its_role() -> None:
    labelled = device(None, "elevator", 0.6, label="Höhenruder")
    bare = device(None, "elevator", 0.6)
    assert list(controls_by_key(mesh_of(conventional(tail={0: labelled}), "elevator"))) == [
        "Tail.Höhenruder_right",
        "Tail.Höhenruder_left",
    ]
    assert list(controls_by_key(mesh_of(conventional(tail={0: bare}), "elevator"))) == [
        "Tail.elevator_right",
        "Tail.elevator_left",
    ]


def test_every_half_is_an_explicit_surface_of_the_one_component_of_its_wing() -> None:
    mesh = mesh_of(conventional(), "aileron")
    assert not any(s.symmetric for s in mesh.surfaces)
    components: dict[int, list[str]] = {}
    for surface in mesh.surfaces:
        assert surface.component is not None
        components.setdefault(surface.component, []).append(surface.name)
    assert sorted(components) == [1, 2, 3]
    assert components[1] == [
        "Main wing right front",
        "Main wing right aft",
        "Main wing left front",
        "Main wing left aft",
    ]


def test_the_left_half_runs_tip_to_root_on_the_negative_side() -> None:
    mesh = mesh_of(conventional(), "flap")
    right = next(s for s in mesh.surfaces if s.name == "Main wing right")
    left = next(s for s in mesh.surfaces if s.name == "Main wing left")
    ys_right = [s.y for s in right.sections]
    ys_left = [s.y for s in left.sections]
    assert ys_right == sorted(ys_right)
    assert (ys_right[0], ys_right[-1]) == (0.0, 0.4)
    assert ys_left == [-y for y in reversed(ys_right)]


def test_a_wing_without_a_control_in_the_role_is_not_split() -> None:
    mesh = mesh_of(conventional(), "aileron")
    names = [s.name for s in mesh.surfaces]
    assert "Tail right" in names
    assert "Tail right front" not in names
    assert "Fin" in names


def test_the_control_is_on_the_aft_piece_and_only_on_the_stations_of_the_device() -> None:
    mesh = mesh_of(conventional(), "aileron")
    ((aft, count),) = [(s, n) for s, n in written(mesh, "c01")]
    assert aft.name == "Main wing right aft"
    assert count >= 2
    for station in aft.sections:
        on = [c for c in station.controls() if c.name == "c01"]
        if on:
            assert 0.2 - 1e-9 <= station.y <= 0.4 + 1e-9
            assert on[0].gain == 1.0
            assert near(on[0].x_hinge, 0.0)
    # the device spans the outer panel: both ends are stations
    ys = {s.y for s in aft.sections}
    assert {0.2, 0.4} <= ys


def test_the_front_piece_ends_at_the_hinge_line() -> None:
    mesh = mesh_of(conventional(), "aileron")
    front = next(s for s in mesh.surfaces if s.name == "Main wing right front")
    aft = next(s for s in mesh.surfaces if s.name == "Main wing right aft")
    outer_front, outer_aft = front.sections[-1], aft.sections[-1]
    assert near(outer_front.y, 0.4)
    assert near(outer_front.chord, 0.75 * 0.2)
    assert near(outer_aft.x, 0.75 * 0.2)
    assert near(outer_aft.chord, 0.25 * 0.2)


def test_a_tapered_hinge_line_is_followed_station_by_station() -> None:
    plane = conventional(main={1: device("aileron", "aileron", 0.8, 0.6)})
    mesh = mesh_of(plane, "aileron")
    aft = next(s for s in mesh.surfaces if s.name == "Main wing right aft")
    # the aft piece is cut at the most forward hinge of the control's stations: 0.6 at the tip
    tip = aft.sections[-1]
    assert near(tip.y, 0.4)
    assert near(tip.chord, 0.4 * 0.2)


def test_the_control_names_are_short_and_in_creation_order() -> None:
    plane = conventional(
        main={0: device("inner", "aileron", 0.75), 1: device("outer", "aileron", 0.75)}
    )
    mesh = mesh_of(plane, "aileron")
    assert [c.name for c in mesh.controls] == ["c01", "c02", "c03", "c04"]
    assert all(len(c.name) <= 16 for c in mesh.controls)
    assert set(control_order(mesh.surfaces)) == {"c01", "c02", "c03", "c04"}


def test_adjacent_segments_of_one_name_are_one_surface() -> None:
    plane = conventional(
        main={0: device("aileron", "aileron", 0.75), 1: device("aileron", "aileron", 0.75)}
    )
    assert list(controls_by_key(mesh_of(plane, "aileron"))) == [
        "Main wing.aileron_right",
        "Main wing.aileron_left",
    ]


def test_adjacent_segments_of_two_names_are_two_surfaces() -> None:
    plane = conventional(
        main={0: device("inner", "aileron", 0.75), 1: device("outer", "aileron", 0.75)}
    )
    assert list(controls_by_key(mesh_of(plane, "aileron"))) == [
        "Main wing.inner_right",
        "Main wing.outer_right",
        "Main wing.inner_left",
        "Main wing.outer_left",
    ]


def test_the_stations_of_a_device_end_shared_by_two_devices_carry_both_controls() -> None:
    plane = conventional(
        main={0: device("inner", "aileron", 0.75), 1: device("outer", "aileron", 0.75)}
    )
    mesh = mesh_of(plane, "aileron")
    aft = next(s for s in mesh.surfaces if s.name == "Main wing right aft")
    shared = next(s for s in aft.sections if near(s.y, 0.2))
    assert sorted(c.name for c in shared.controls()) == ["c01", "c02"]


def test_two_surfaces_with_one_key_are_refused() -> None:
    plane = conventional(
        main={
            0: device("aileron", "aileron", 0.75),
            1: device("gap", "flap", 0.75),
            2: device("aileron", "aileron", 0.75),
        },
        main_ys=(0.0, 0.2, 0.4, 0.6),
    )
    with pytest.raises(FormulaError) as raised:
        mesh_of(plane, "aileron")
    assert raised.value.code == "duplicate_surface_key"
    assert raised.value.category is ErrorCategory.INVALID_INPUT


def test_a_device_without_a_hinge_is_refused() -> None:
    with pytest.raises(FormulaError) as raised:
        mesh_of(conventional(main={1: {"name": "aileron", "role": "aileron"}}), "aileron")
    assert raised.value.code == "missing_hinge"


@pytest.mark.parametrize("root", [0.0, 1.0, -0.1, 1.2])
def test_a_hinge_at_or_beyond_an_edge_of_the_chord_is_refused(root: float) -> None:
    plane = conventional(main={1: device("aileron", "aileron", root)})
    with pytest.raises(FormulaError) as raised:
        mesh_of(plane, "aileron")
    assert raised.value.code == "hinge_outside_chord"


def test_a_device_on_an_unmirrored_wing_that_spreads_sideways_is_refused() -> None:
    wings = {
        "Main": wing_document(
            "Main wing",
            "main_wing",
            [(0.0, 0.0, 0.0, 0.2), (0.0, 0.4, 0.0, 0.2)],
            {0: device("aileron", "aileron", 0.75)},
            symmetric=False,
        )
    }
    plane = AirplaneGeometry.model_validate({"name": "u", "wings": wings})
    with pytest.raises(FormulaError) as raised:
        mesh_of(plane, "aileron")
    assert raised.value.code == "hinge_device_on_unmirrored_surface"


def test_a_hinge_line_with_a_jump_is_refused() -> None:
    plane = conventional(
        main={
            0: device("aileron", "aileron", 0.75, 0.75),
            1: device("aileron", "aileron", 0.6, 0.6),
        }
    )
    with pytest.raises(FormulaError) as raised:
        mesh_of(plane, "aileron")
    assert raised.value.code == "hinge_line_discontinuous"


def test_a_mirrored_fin_has_a_mirrored_hinge_vector_on_its_image() -> None:
    wings = {
        "Main": wing_document(
            "Main wing", "main_wing", [(0.0, 0.0, 0.0, 0.2), (0.0, 0.4, 0.0, 0.2)]
        ),
        "Fins": wing_document(
            "Fins",
            "vertical_tail",
            [(0.6, 0.2, 0.0, 0.12), (0.6, 0.2, 0.12, 0.1)],
            {0: device("rudder", "rudder", 0.6)},
        ),
    }
    plane = AirplaneGeometry.model_validate({"name": "t", "wings": wings})
    mesh = mesh_of(plane, "rudder")
    assert controls_by_key(mesh) == {
        "Fins.rudder_right": ("c01", 1),
        "Fins.rudder_left": ("c02", -1),
    }
    vectors = {
        c.name: c.hinge_vector for s in mesh.surfaces for st in s.sections for c in st.controls()
    }
    assert vectors == {"c01": (0.0, 0.0, 0.0), "c02": (0.0, 0.0, -1.0)}
    image = next(s for s in mesh.surfaces if s.name == "Fins left aft")
    assert {s.y for s in image.sections} == {-0.2}
    assert [s.z for s in image.sections] == sorted(s.z for s in image.sections)


def test_a_role_without_devices_gives_no_controls_and_unsplit_surfaces() -> None:
    mesh = mesh_of(conventional(main={}, tail={}, fin={}), "aileron")
    assert mesh.controls == ()
    assert not any(s.name.endswith(("front", "aft")) for s in mesh.surfaces)
    assert control_order(mesh.surfaces) == ()


def test_an_airplane_without_a_main_wing_is_a_defect_of_the_caller() -> None:
    plane = AirplaneGeometry.model_validate(
        {
            "name": "n",
            "wings": {
                "Tail": wing_document(
                    "Tail", "horizontal_tail", [(0.0, 0.0, 0.0, 0.1), (0.0, 0.1, 0.0, 0.1)]
                )
            },
        }
    )
    with pytest.raises(ValueError, match="main_wing"):
        mesh_of(plane, "elevator")
