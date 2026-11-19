"""The OPER dialogue of a hinge-moment run and the reading of its output (ch. 8.8)."""

import pytest
from aero_kernel.solvers.avl_mesh import MeshControl, MeshSection, MeshSurface
from aero_kernel.solvers.avl_writer import (
    HingeOutput,
    avl_geometry,
    avl_hinge_commands,
    parse_hinge_output,
)

OUTPUT = """
 Operating case:
  CLtot =   0.60000
  c01             =  -5.00000
  c02             =   5.00000
 ---------------------------------------------------------------
 Control Hinge Moments
 (referred to    Sref =  0.1600     Cref =    0.2000)

 Control          Chinge
 ---------------- -----------
 c01                -0.2345E-02
 c02                 0.1234E-01
 ---------------------------------------------------------------
"""


def test_the_commands_constrain_cl_set_every_control_run_and_print_the_hinge_moments() -> None:
    commands = avl_hinge_commands(0.6, 0.25, {"c02": 5.0, "c01": -5.0}, order=("c01", "c02"))
    assert commands == ("oper\no\nc\n0.25\n\na c 0.6\nd1 d1 -5.0\nd2 d2 5.0\nx\nhm\n\n\nquit\n")


def test_a_control_without_a_value_is_a_defect() -> None:
    with pytest.raises(KeyError):
        avl_hinge_commands(0.6, 0.25, {"c01": 1.0}, order=("c01", "c02"))


def test_the_output_gives_cl_the_echoed_controls_and_the_hinge_moments() -> None:
    output = parse_hinge_output(OUTPUT, ("c01", "c02"))
    assert output == HingeOutput(
        cl=0.6,
        controls={"c01": -5.0, "c02": 5.0},
        moments={"c01": -0.002345, "c02": 0.01234},
    )


def test_an_output_without_the_table_is_not_understood() -> None:
    assert parse_hinge_output(OUTPUT.split("Control Hinge")[0], ("c01", "c02")) is None


def test_an_output_missing_one_control_is_not_understood() -> None:
    assert parse_hinge_output(OUTPUT, ("c01", "c02", "c03")) is None


def test_a_control_hinge_vector_is_written_into_the_control_line() -> None:
    control = MeshControl(
        gain=1.0, x_hinge=0.0, name="c01", sgn_dup=1, hinge_vector=(0.0, 0.0, -1.0)
    )
    section = MeshSection(x=0.0, y=0.0, z=0.0, chord=0.1, twist=0.0, airfoil=0, others=(control,))
    surface = MeshSurface(name="s", symmetric=False, sections=(section, section), component=2)
    text = avl_geometry((surface,), [1.0], n_chord=4, s_ref=1.0, c_ref=1.0, b_ref=1.0)
    assert "CONTROL\nc01 1.0 0.0 0.0 0.0 -1.0 1\n" in text
    assert "COMPONENT\n2\n" in text
    assert "YDUPLICATE" not in text
