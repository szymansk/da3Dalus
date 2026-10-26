"""The AVL text writer and the reader of its output (no AVL involved)."""

import pytest
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.solvers.avl_writer import (
    AvlOutput,
    airfoil_file,
    avl_commands,
    avl_geometry,
    parse_avl_output,
)
from aero_kernel.tests.mesh_helpers import mesh_surfaces
from aero_kernel.tests.np_builders import CONVENTIONAL, airplane_with, surface

S_REF, C_REF, B_REF = 0.28, 0.2, 1.4


def with_fin() -> AirplaneGeometry:
    """The conventional airplane plus a one-sided fin standing on the centreline."""
    fin = surface("Fin", "vertical_tail", 0.0, 0.1, 0.55)
    fin["symmetric"] = False
    fin["x_secs"] = [
        {"xyz_le": [0.55, 0.0, z], "chord": 0.1 - z * 0.2, "twist": 0.0, "airfoil": "naca0012"}
        for z in (0.0, 0.15)
    ]
    dumped = airplane_with(*CONVENTIONAL).model_dump(mode="json")
    dumped["wings"]["Fin"] = fin
    return AirplaneGeometry.model_validate(dumped)


def text(airplane: AirplaneGeometry | None = None, claf: float = 1.09) -> str:
    plane = airplane or with_fin()
    surfaces = mesh_surfaces(plane, 4, lambda _a: 0)
    return avl_geometry(surfaces, [claf], n_chord=10, s_ref=S_REF, c_ref=C_REF, b_ref=B_REF)


def test_the_file_has_the_kernels_references_at_mach_zero_and_the_origin_as_reference_point() -> (
    None
):
    lines = text().splitlines()
    assert lines[lines.index("#Mach") + 1] == "0.0"
    assert lines[lines.index("#Sref    Cref    Bref") + 1] == f"{S_REF!r} {C_REF!r} {B_REF!r}"
    assert lines[lines.index("#Xref    Yref    Zref") + 1] == "0.0 0.0 0.0"


def test_the_file_has_no_body_and_no_control() -> None:
    body = text()
    assert "BODY" not in body
    assert "CONTROL" not in body


def test_there_is_one_surface_per_mesh_surface_and_one_section_per_station() -> None:
    surfaces = mesh_surfaces(with_fin(), 4, lambda _a: 0)
    body = text()
    assert body.count("\nSURFACE\n") == len(surfaces) == 3
    assert body.count("SECTION\n") == sum(len(s.sections) for s in surfaces)


def test_only_mirrored_surfaces_are_duplicated() -> None:
    assert text(airplane_with("main_wing")).count("YDUPLICATE") == 1
    assert text().count("YDUPLICATE") == 2  # wing and tail; the fin is one-sided


def test_every_section_names_its_airfoil_file_and_claf() -> None:
    body = text(claf=1.0924)
    assert body.count("AFIL\naf0.dat") == body.count("SECTION\n")
    assert body.count("CLAF\n1.0924") == body.count("SECTION\n")


def test_the_airfoil_file_is_selig_text() -> None:
    assert airfoil_file("naca", [(1.0, 0.0), (0.5, 0.06), (0.0, 0.0)]) == (
        "naca\n1.00000000 0.00000000\n0.50000000 0.06000000\n0.00000000 0.00000000\n"
    )


@pytest.mark.parametrize("x", [1.2, -0.1])
def test_a_point_outside_the_unit_chord_is_refused(x: float) -> None:
    with pytest.raises(ValueError, match="outside the unit chord"):
        airfoil_file("bad", [(x, 0.0)])


def test_the_commands_set_the_core_ratio_then_constrain_cl_then_ask_for_stability() -> None:
    assert avl_commands(0.5, 0.25) == "oper\no\nc\n0.25\n\na c 0.5\nx\nst\n\n\nquit\n"


def test_the_output_is_read_by_its_first_hit_of_each_key() -> None:
    out = " Sref = 0.28000  Cref = 0.2\n CLtot =   0.50000\n Xnp = 0.131\n Clb Cnr / Clr Cnb = 1\n Xnp = 9.9\n"
    parsed = parse_avl_output(out)
    assert parsed is not None
    assert (parsed.x_np, parsed.cl) == (0.131, 0.5)


def test_an_output_without_the_neutral_point_is_none() -> None:
    assert parse_avl_output(" Sref = 0.28\n CLtot = 0.5\n") is None


def test_fortran_d_exponents_are_read() -> None:
    parsed = parse_avl_output(" CLtot = 1.5D-01\n Xnp = 1.5D-02\n")
    assert parsed is not None
    assert (parsed.x_np, parsed.cl) == (0.015, 0.15)


def test_the_output_carries_only_what_the_adapter_reads() -> None:
    """The reference area is the kernel's own and goes into the file; reading it back would be a
    second authority for it (ADR 0022) that nothing consults (ADR 0021)."""
    assert set(AvlOutput.model_fields) == {"x_np", "cl"}
