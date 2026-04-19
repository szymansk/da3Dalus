import pytest

from app.services.avl_strip_forces import parse_strip_forces_output

SAMPLE_FS_OUTPUT = """
 Surface and Strip Forces by surface

  Sref = 0.25000       Cref = 0.25333       Bref =  1.0000
  Xref =  0.0000       Yref =  0.0000       Zref =  0.0000

  Surface # 1     Main Wing
     # Chordwise = 12   # Spanwise = 12     First strip =  1
     Surface area Ssurf =    0.125000     Ave. chord Cave =    0.250000

 Forces referred to Sref, Cref, Bref about Xref, Yref, Zref
 Standard axis orientation,  X fwd, Z down
     CLsurf  =   0.16769     Clsurf  =  -0.03573
     CYsurf  =  -0.00190     Cmsurf  =  -0.04143
     CDsurf  =   0.00450     Cnsurf  =  -0.00157
     CDisurf =   0.00450     CDvsurf =   0.00000

 Forces referred to Ssurf, Cave
     CLsurf  =   0.33539     CDsurf  =   0.00900

 Strip Forces referred to Strip Area, Chord
    j     Xle      Yle      Zle      Chord    Area     c_cl     ai     cl_norm    cl       cd       cdv    cm_c/4     cm_LE   C.P.x/c
     1   0.0001   0.0021   0.0000   0.2996   0.0026   0.1064   0.0563   0.3555   0.3555   0.0117   0.0000   0.0128  -0.0759    0.214
     2   0.0008   0.0190   0.0000   0.2962   0.0074   0.1063   0.0550   0.3592   0.3592   0.0103   0.0000   0.0130  -0.0766    0.214
     3   0.0021   0.0517   0.0000   0.2897   0.0115   0.1056   0.0535   0.3649   0.3649   0.0098   0.0000   0.0131  -0.0779    0.214

  Surface # 2     Main Wing (YDUP)
     # Chordwise = 12   # Spanwise = 12     First strip = 13
     Surface area Ssurf =    0.125000     Ave. chord Cave =    0.250000

 Forces referred to Sref, Cref, Bref about Xref, Yref, Zref
 Standard axis orientation,  X fwd, Z down
     CLsurf  =   0.16769     Clsurf  =   0.03573
     CYsurf  =   0.00190     Cmsurf  =  -0.04143
     CDsurf  =   0.00450     Cnsurf  =   0.00157
     CDisurf =   0.00450     CDvsurf =   0.00000

 Forces referred to Ssurf, Cave
     CLsurf  =   0.33539     CDsurf  =   0.00900

 Strip Forces referred to Strip Area, Chord
    j     Xle      Yle      Zle      Chord    Area     c_cl     ai     cl_norm    cl       cd       cdv    cm_c/4     cm_LE   C.P.x/c
    13   0.0001  -0.0021   0.0000   0.2996   0.0026   0.1064   0.0563   0.3555   0.3555   0.0117   0.0000   0.0128   0.0759    0.214
    14   0.0008  -0.0190   0.0000   0.2962   0.0074   0.1063   0.0550   0.3592   0.3592   0.0103   0.0000   0.0130   0.0766    0.214
    15   0.0021  -0.0517   0.0000   0.2897   0.0115   0.1056   0.0535   0.3649   0.3649   0.0098   0.0000   0.0131   0.0779    0.214
"""


class TestParseStripForcesOutput:
    def test_parses_two_surfaces(self):
        result = parse_strip_forces_output(SAMPLE_FS_OUTPUT)
        assert len(result) == 2
        assert result[0]["surface_name"] == "Main Wing"
        assert result[1]["surface_name"] == "Main Wing (YDUP)"

    def test_parses_strip_data(self):
        result = parse_strip_forces_output(SAMPLE_FS_OUTPUT)
        strips = result[0]["strips"]
        assert len(strips) == 3
        assert strips[0]["j"] == 1
        assert strips[0]["Yle"] == pytest.approx(0.0021)
        assert strips[0]["Chord"] == pytest.approx(0.2996)
        assert strips[0]["cl"] == pytest.approx(0.3555)
        assert strips[0]["cd"] == pytest.approx(0.0117)
        assert strips[0]["cm_c/4"] == pytest.approx(0.0128)
        assert strips[0]["C.P.x/c"] == pytest.approx(0.214)

    def test_parses_surface_metadata(self):
        result = parse_strip_forces_output(SAMPLE_FS_OUTPUT)
        assert result[0]["n_chordwise"] == 12
        assert result[0]["n_spanwise"] == 12
        assert result[0]["surface_area"] == pytest.approx(0.125)

    def test_empty_output(self):
        result = parse_strip_forces_output("")
        assert result == []

    def test_output_without_strip_section(self):
        result = parse_strip_forces_output("Some random AVL output\nwithout strip data")
        assert result == []
