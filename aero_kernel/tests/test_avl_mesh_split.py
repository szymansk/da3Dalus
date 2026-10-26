"""The main wing split at the hinge into a front and an aft AVL surface (ARCHITECTURE ch. 8.8)."""

import math

import pytest
from aero_kernel.solvers.avl_mesh import MeshSurface, split_at_hinge
from aero_kernel.solvers.avl_writer import avl_geometry
from aero_kernel.tests.mesh_helpers import mesh_surfaces
from aero_kernel.tests.test_solvers_roll_devices import aileron, wing_geometry

HINGE = 0.78


def driven() -> MeshSurface:
    """The unsplit driven main wing: 0.4 m half span, device on the second panel (y 0.2 .. 0.4)."""
    plane = wing_geometry((0.0, 0.2, 0.4), 1, aileron(HINGE, HINGE))
    (main,) = mesh_surfaces(plane, 8, lambda _a: 0, drive_roll=True)
    return main


def test_both_pieces_have_the_stations_of_the_unsplit_wing() -> None:
    main = driven()
    front, aft = split_at_hinge(main, (12, 8))
    assert [s.y for s in front.sections] == [s.y for s in main.sections]
    assert [s.y for s in aft.sections] == [s.y for s in main.sections]
    assert (front.name, aft.name) == ("Main front", "Main aft")
    assert (front.n_chord, aft.n_chord) == (12, 8)
    assert front.symmetric is aft.symmetric is main.symmetric


def test_the_pieces_cut_the_chord_at_the_hinge_and_keep_z_and_twist() -> None:
    """Front: leading edge unchanged, chord h c, AFIL 0..h. Aft: leading edge at x + h c, z and twist
    unchanged (AVL tilts the normals, it never rotates the lattice), chord (1 - h) c, AFIL h..1."""
    main = driven()
    front, aft = split_at_hinge(main, (12, 8))
    for whole, f, a in zip(main.sections, front.sections, aft.sections, strict=True):
        assert a.chord_range is not None
        cut = a.chord_range[0]
        assert math.isclose(cut, HINGE)
        assert f.x == whole.x
        assert math.isclose(f.chord, cut * whole.chord)
        assert f.chord_range == (0.0, cut)
        assert math.isclose(a.x, whole.x + cut * whole.chord)
        assert math.isclose(a.chord, (1.0 - cut) * whole.chord)
        assert a.chord_range == (cut, 1.0)
        assert (f.z, a.z) == (whole.z, whole.z)
        assert (f.twist, a.twist) == (whole.twist, whole.twist)
        assert math.isclose(f.chord + a.chord, whole.chord)


def test_the_control_sits_on_the_aft_piece_with_its_hinge_at_the_leading_edge() -> None:
    main = driven()
    front, aft = split_at_hinge(main, (12, 8))
    assert all(s.control is None for s in front.sections)
    for whole, a in zip(main.sections, aft.sections, strict=True):
        if whole.control is None:
            assert a.control is None
        else:
            assert a.control is not None
            assert a.control.x_hinge == 0.0
            assert a.control.gain == whole.control.gain


def test_stations_off_the_device_take_the_cut_of_the_nearest_controlled_station() -> None:
    """The inboard stations have no control; their cut is the hinge of the nearest device end, so the
    cut is continuous along the span."""
    plane = wing_geometry((0.0, 0.2, 0.4), 1, aileron(0.7, 0.8))
    (main,) = mesh_surfaces(plane, 8, lambda _a: 0, drive_roll=True)
    front, _ = split_at_hinge(main, (12, 8))
    root = front.sections[0]
    assert root.chord_range is not None
    assert math.isclose(root.chord_range[1], 0.7)


def test_the_file_has_two_surfaces_with_their_chordwise_counts_and_afil_ranges() -> None:
    front, aft = split_at_hinge(driven(), (12, 8))
    text = avl_geometry([front, aft], [1.0], n_chord=10, s_ref=0.16, c_ref=0.2, b_ref=0.8)
    lines = text.splitlines()
    assert lines.count("SURFACE") == 2
    counts = [lines[i + 1] for i, line in enumerate(lines) if line == "#Nchordwise  Cspace"]
    assert counts == ["12   1", "8   1"]
    ranges = [line.split() for line in lines if line.startswith("AFIL")]
    assert all(len(r) == 3 for r in ranges)  # every section of a split surface names its range
    assert all(math.isclose(float(hi), HINGE) for _, lo, hi in ranges if float(lo) == 0.0)
    assert all(
        math.isclose(float(lo), HINGE) and float(hi) == 1.0
        for _, lo, hi in ranges
        if float(lo) != 0.0
    )


def test_a_surface_without_a_count_takes_the_runs() -> None:
    (main,) = mesh_surfaces(
        wing_geometry((0.0, 0.2, 0.4), 1, aileron(HINGE, HINGE)), 8, lambda _a: 0
    )
    text = avl_geometry([main], [1.0], n_chord=10, s_ref=0.16, c_ref=0.2, b_ref=0.8)
    assert "10   1" in text.splitlines()
    assert not any(line.startswith("AFIL ") for line in text.splitlines())


@pytest.mark.parametrize("cut", [0.5, 0.9])
def test_the_pieces_cover_the_chord_for_any_hinge(cut: float) -> None:
    plane = wing_geometry((0.0, 0.2, 0.4), 1, aileron(cut, cut))
    (main,) = mesh_surfaces(plane, 8, lambda _a: 0, drive_roll=True)
    front, aft = split_at_hinge(main, (12, 8))
    for whole, f, a in zip(main.sections, front.sections, aft.sections, strict=True):
        assert math.isclose(f.chord + a.chord, whole.chord)
        assert math.isclose(a.x, f.x + f.chord)
