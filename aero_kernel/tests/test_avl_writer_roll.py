"""The AVL file and commands of the steady roll, and the reading of its output (ch. 8.8)."""

import math
from pathlib import Path

import pytest
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.solvers.avl_writer import (
    RollOutput,
    avl_commands,
    avl_geometry,
    avl_roll_commands,
    parse_roll_output,
)
from aero_kernel.tests.mesh_helpers import mesh_surfaces
from aero_kernel.tests.reference_fleet import FleetMember, reference_document

SNAPSHOTS = Path(__file__).resolve().parent / "reference" / "snapshots"


def written(member: FleetMember, *, roll: bool) -> str:
    """The AVL file of a fleet member at 24 strips: every airfoil gets CLAF 1.09."""
    plane = AirplaneGeometry.model_validate(reference_document(member))
    reference = member.reference
    numbers: dict[str, int] = {}

    def number(airfoil: object) -> int:
        return numbers.setdefault(repr(airfoil), len(numbers))

    surfaces = mesh_surfaces(plane, 24, number, drive_roll=roll)
    return avl_geometry(
        surfaces,
        [1.09] * len(numbers),
        n_chord=10,
        s_ref=reference.s_ref,
        c_ref=reference.c_mac,
        b_ref=reference.b_ref,
        xyz_ref=plane.xyz_ref if roll else (0.0, 0.0, 0.0),
    )


@pytest.mark.parametrize("member", list(FleetMember))
def test_clean_mesh_and_file_unchanged(member: FleetMember) -> None:
    """The neutral-point file is the slice-4b one (commit 1ab1d5ef): no breaks, no controls, the
    reference point at the origin. Only its ``Sref Cref Bref`` line moved, to AeroSandbox's values (gh-1240)."""
    expected = (SNAPSHOTS / f"{member.name.lower()}_clean.avl").read_text()
    assert written(member, roll=False) == expected


def test_roll_file_reference_point_is_xyz_ref() -> None:
    lines = written(FleetMember.BRYAN, roll=True).splitlines()
    assert lines[lines.index("#Xref    Yref    Zref") + 1] == "0.1368 0.0 -0.0062"


def test_roll_file_snapshot_bryan() -> None:
    expected = (SNAPSHOTS / "bryan_roll.avl").read_text()
    assert written(FleetMember.BRYAN, roll=True) == expected


def test_control_lines_follow_the_section_they_belong_to() -> None:
    text = written(FleetMember.BRYAN, roll=True)
    blocks = text.split("SECTION\n")[1:]
    controlled = [b for b in blocks if "CONTROL" in b]
    assert controlled
    for block in controlled:
        lines = block.splitlines()
        index = lines.index("CONTROL")
        assert lines[index - 2 : index] == ["CLAF", "1.09"]
        name, gain, hinge, *vector, sgn = lines[index + 1].split()
        assert name == "aileron"
        assert math.isclose(float(gain), -1.0, rel_tol=1e-12)
        assert 0.7 < float(hinge) < 0.8
        assert all(math.isclose(float(v), 0.0, abs_tol=1e-15) for v in vector)
        assert sgn == "-1"


def test_the_clean_file_has_no_control() -> None:
    assert "CONTROL" not in written(FleetMember.BRYAN, roll=False)


def test_roll_commands_cl_rm_d1() -> None:
    """Constrain C_L, the stability-axis rolling moment to zero, the aileron to the command and run;
    then hold the roll rate and the aileron at zero, run again and print the derivatives."""
    assert avl_roll_commands(0.5, 0.25, 20.0) == (
        "oper\no\nc\n0.25\n\na c 0.5\nr rm 0\nd1 d1 20.0\nx\nr r 0\nd1 d1 0\nx\nst\n\n\nquit\n"
    )
    assert avl_commands(0.5, 0.25) == "oper\no\nc\n0.25\n\na c 0.5\nx\nst\n\n\nquit\n"


OUTPUT = """
  Alpha =   7.08055     pb/2V =   0.24217     p'b/2V =   0.24403
  Beta  =   0.00000     qc/2V =   0.00000
  Mach  =     0.000     rb/2V =   0.03008     r'b/2V =  -0.00000

  CXtot =   0.07226     Cltot =   0.00385     Cl'tot =   0.00000
  CYtot =   0.03805     Cmtot =  -0.05464
  CZtot =  -0.79717     Cntot =  -0.03102     Cn'tot =  -0.03126

  CLtot =   0.80000
  CDtot =   0.02656

   aileron         =  20.00000

 x' mom.  Cl'|    Clp =  -0.352014    Clq =  -0.000000    Clr =   0.160788
 x' mom.  Cl'|   Cld01 =   0.004929

  p'b/2V =   9.99999
"""


def test_parse_stability_axis_pb2v_cltot_and_control_echo() -> None:
    """The stability-axis value (p'b/2V, not pb/2V), the first hit of each key."""
    parsed = parse_roll_output(OUTPUT)
    assert parsed == RollOutput(
        p_hat=0.24403, cl=0.8, cl_stability=0.0, control=20.0, cl_p=-0.352014, cl_delta=0.004929
    )


@pytest.mark.parametrize("missing", ["p'b/2V", "CLtot", "Cl'tot", "aileron", "Clp", "Cld01"])
def test_an_output_without_a_value_is_none(missing: str) -> None:
    broken = OUTPUT.replace(missing, "xxxxxx")
    assert parse_roll_output(broken) is None


def test_the_roll_output_carries_what_the_adapter_checks() -> None:
    assert set(RollOutput.model_fields) == {
        "p_hat",
        "cl",
        "cl_stability",
        "control",
        "cl_p",
        "cl_delta",
    }
