"""The OPER dialogue of the spanwise loads and the reading of AVL's FS and VM files (fast tier)."""

import math

from aero_kernel.solvers.avl_writer import avl_loads_commands, parse_loads_output

# Trimmed copies of the files AVL 3.40 wrote for the 0.28 m^2, 1.4 m rectangular test wing at C_L 0.6
# (aileron_trainer, 3 of the 24 strips; the surface "Main (YDUP)" follows in the real files).
STRIPS = """ ---------------------------------------------------------------
 Surface and Strip Forces by surface

  Sref = 0.28000       Cref = 0.20000       Bref =  1.4000
  Xref =  0.0000       Yref =  0.0000       Zref =  0.0000

  Surface # 1     Main
     # Chordwise = 10   # Spanwise = 24     First strip =  1
     Surface area Ssurf =    0.140000     Ave. chord Cave =    0.200000

 Strip Forces referred to Strip Area, Chord
    j     Xle      Yle      Zle      Chord    Area     c_cl     ai     cl_norm    cl       cd       cdv    cm_c/4     cm_LE   C.P.x/c
     1   0.0000   0.0146   0.0000   0.2000   0.0058   0.1392   0.0418   0.6971   0.6971   0.0146   0.0000  -0.0379  -0.2119    0.304
     2   0.0000   0.0437   0.0000   0.2000   0.0058   0.1391   0.0419   0.6966   0.6966   0.0147   0.0000  -0.0379  -0.2117    0.304
     3   0.0000   0.0729   0.0000   0.2000   0.0058   0.1389   0.0422   0.6955   0.6955   0.0147   0.0000  -0.0379  -0.2114    0.304

  Surface # 2     Main (YDUP)
     # Chordwise = 10   # Spanwise = 24     First strip = 25
 Strip Forces referred to Strip Area, Chord
    j     Xle      Yle      Zle      Chord    Area     c_cl     ai     cl_norm    cl       cd       cdv    cm_c/4     cm_LE   C.P.x/c
    25   0.0000  -0.0146   0.0000   0.2000   0.0058   0.9999   0.0418   0.6971   0.6971   0.0146   0.0000  -0.0379   0.2119    0.304
"""
SHEAR_MOMENT = """
 Shear/q and Bending Moment/q vs Y
  Mach  =    0.000
  alpha =    4.803    CLtot =    0.600
  beta  =    0.000

  Sref  =     0.28000
  Bref  =     1.40000

 Surface:   1
Main
     2Ymin/Bref =    0.0000000000000000
     2Ymax/Bref =    1.0000000000000000
   2Y/Bref      Vz/(q*Sref)      Mx/(q*Bref*Sref)
    0.0000  0.298353         0.669065E-01
    0.0208  0.291104         0.638364E-01
    1.0000   0.00000          0.00000

 Surface:   2
Main (YDUP)
   2Y/Bref      Vz/(q*Sref)      Mx/(q*Bref*Sref)
    0.0000  0.298353        -0.669065E-01
"""


def test_the_dialogue_solves_for_the_lift_coefficient_and_writes_both_files() -> None:
    assert avl_loads_commands(0.6, 0.25) == (
        "oper\no\nc\n0.25\n\na c 0.6\nx\nfs strips.txt\nvm shearmoment.txt\n\nquit\n"
    )


def test_the_first_surface_is_read_and_the_normalisations_are_undone() -> None:
    """Hand values: y = (2Y/Bref) Bref/2, V/q = Vz/(q Sref) Sref, M/q = Mx/(q Bref Sref) Bref Sref."""
    output = parse_loads_output(STRIPS, SHEAR_MOMENT, b_ref=1.4, s_ref=0.28)
    assert output is not None
    assert output.cl == 0.6
    assert output.y_strip == (0.0146, 0.0437, 0.0729)
    assert output.c_cl == (0.1392, 0.1391, 0.1389)
    assert output.y_station == (0.0, 0.0208 * 0.7, 0.7)
    assert math.isclose(output.shear[0], 0.298353 * 0.28, rel_tol=1e-12)
    assert math.isclose(output.moment[0], 0.0669065 * 0.28 * 1.4, rel_tol=1e-12)
    assert output.shear[2] == output.moment[2] == 0.0


def test_a_file_without_its_table_is_not_a_finished_run() -> None:
    assert parse_loads_output("", SHEAR_MOMENT, b_ref=1.4, s_ref=0.28) is None
    assert parse_loads_output(STRIPS, "", b_ref=1.4, s_ref=0.28) is None
    no_cl = SHEAR_MOMENT.replace("CLtot", "CLxxx")
    assert parse_loads_output(STRIPS, no_cl, b_ref=1.4, s_ref=0.28) is None
