"""Tests for AVL geometry dataclass serialisation."""
from __future__ import annotations


class TestAvlCdcl:
    def test_repr_formats_six_values(self):
        from app.avl.geometry import AvlCdcl

        cdcl = AvlCdcl(cl_min=-0.6, cd_min=0.024, cl_0=0.2, cd_0=0.008, cl_max=1.4, cd_max=0.032)
        result = repr(cdcl)
        assert "CDCL" in result
        lines = [l.strip() for l in result.strip().splitlines() if l.strip() and not l.strip().startswith("!")]
        assert lines[0] == "CDCL"
        values = lines[1].split()
        assert len(values) == 6
        assert float(values[0]) == -0.6
        assert float(values[5]) == 0.032

    def test_zero_cdcl(self):
        from app.avl.geometry import AvlCdcl

        cdcl = AvlCdcl.zeros()
        assert cdcl.is_zero()
        result = repr(cdcl)
        assert "CDCL" in result

    def test_nonzero_is_not_zero(self):
        from app.avl.geometry import AvlCdcl

        cdcl = AvlCdcl(cl_min=-0.5, cd_min=0.02, cl_0=0.1, cd_0=0.007, cl_max=1.3, cd_max=0.03)
        assert not cdcl.is_zero()


class TestAvlControl:
    def test_repr_formats_control_block(self):
        from app.avl.geometry import AvlControl

        ctrl = AvlControl(name="aileron", gain=1.0, xhinge=0.8, xyz_hvec=(0.0, 0.0, 0.0), sgn_dup=-1.0)
        result = repr(ctrl)
        lines = [l.strip() for l in result.strip().splitlines() if l.strip() and not l.strip().startswith("!")]
        assert lines[0] == "CONTROL"
        parts = lines[1].split()
        assert parts[0] == "aileron"
        assert float(parts[1]) == 1.0
        assert float(parts[2]) == 0.8
        assert float(parts[-1]) == -1.0


class TestAvlAirfoilTypes:
    def test_naca_repr(self):
        from app.avl.geometry import AvlNaca

        assert "NACA" in repr(AvlNaca("2412"))
        assert "2412" in repr(AvlNaca("2412"))

    def test_afile_repr(self):
        from app.avl.geometry import AvlAfile

        result = repr(AvlAfile("/path/to/airfoil.dat"))
        assert "AFIL" in result
        assert "/path/to/airfoil.dat" in result

    def test_airfoil_inline_repr(self):
        from app.avl.geometry import AvlAirfoilInline

        coords = "1.0 0.0\n0.5 0.05\n0.0 0.0"
        result = repr(AvlAirfoilInline(name="custom", coordinates=coords))
        assert "AIRFOIL" in result
        assert "1.0 0.0" in result


class TestAvlSection:
    def test_minimal_section(self):
        from app.avl.geometry import AvlSection

        sec = AvlSection(xyz_le=(0.0, 0.0, 0.0), chord=0.2, ainc=2.0)
        result = repr(sec)
        assert "SECTION" in result

    def test_section_with_nspan_sspace(self):
        from app.avl.geometry import AvlSection

        sec = AvlSection(xyz_le=(0.0, 1.0, 0.0), chord=0.15, ainc=0.0, n_span=8, s_space=1.0)
        result = repr(sec)
        # Should have 7 values on geometry line: Xle Yle Zle Chord Ainc Nspan Sspace
        lines = [
            l
            for l in result.splitlines()
            if l.strip()
            and not l.strip().startswith("!")
            and not l.strip().startswith("#")
            and l.strip() != "SECTION"
        ]
        geo = lines[0].split()
        assert len(geo) == 7
        assert int(geo[5]) == 8

    def test_section_with_airfoil_claf_cdcl_controls(self):
        from app.avl.geometry import AvlAfile, AvlCdcl, AvlControl, AvlSection

        sec = AvlSection(
            xyz_le=(0.01, 0.0, 0.0),
            chord=0.2,
            ainc=0.0,
            airfoil=AvlAfile("/tmp/naca2412.dat"),
            claf=1.1,
            cdcl=AvlCdcl(cl_min=-0.5, cd_min=0.02, cl_0=0.1, cd_0=0.007, cl_max=1.3, cd_max=0.03),
            controls=[AvlControl("aileron", 1.0, 0.8, (0.0, 0.0, 0.0), -1.0)],
        )
        result = repr(sec)
        assert "AFIL" in result
        assert "CLAF" in result
        assert "CDCL" in result
        assert "CONTROL" in result


class TestAvlSurface:
    def test_minimal_surface(self):
        from app.avl.geometry import AvlSection, AvlSurface

        surf = AvlSurface(
            name="Main Wing",
            n_chord=12,
            c_space=1.0,
            sections=[
                AvlSection(xyz_le=(0.0, 0.0, 0.0), chord=0.2),
                AvlSection(xyz_le=(0.02, 1.0, 0.1), chord=0.15),
            ],
        )
        result = repr(surf)
        assert "SURFACE" in result
        assert "Main Wing" in result
        assert result.count("SECTION") == 2

    def test_surface_with_yduplicate(self):
        from app.avl.geometry import AvlSection, AvlSurface

        surf = AvlSurface(
            name="Wing",
            n_chord=12,
            c_space=1.0,
            yduplicate=0.0,
            sections=[AvlSection(xyz_le=(0, 0, 0), chord=0.2), AvlSection(xyz_le=(0, 1, 0), chord=0.15)],
        )
        assert "YDUPLICATE" in repr(surf)

    def test_surface_with_component(self):
        from app.avl.geometry import AvlSection, AvlSurface

        surf = AvlSurface(
            name="Wing",
            n_chord=12,
            c_space=1.0,
            component=1,
            sections=[AvlSection(xyz_le=(0, 0, 0), chord=0.2), AvlSection(xyz_le=(0, 1, 0), chord=0.15)],
        )
        assert "COMPONENT" in repr(surf)

    def test_surface_with_nspan_sspace(self):
        from app.avl.geometry import AvlSection, AvlSurface

        surf = AvlSurface(
            name="Wing",
            n_chord=12,
            c_space=1.0,
            n_span=20,
            s_space=1.0,
            sections=[AvlSection(xyz_le=(0, 0, 0), chord=0.2), AvlSection(xyz_le=(0, 1, 0), chord=0.15)],
        )
        result = repr(surf)
        lines = result.splitlines()
        for i, line in enumerate(lines):
            if "Nchord" in line:
                parts = lines[i + 1].strip().split()
                assert len(parts) == 4
                assert int(parts[0]) == 12
                assert int(parts[2]) == 20
                break

    def test_surface_flags(self):
        from app.avl.geometry import AvlSection, AvlSurface

        surf = AvlSurface(
            name="Fin",
            n_chord=8,
            c_space=1.0,
            nowake=True,
            noalbe=True,
            noload=True,
            sections=[AvlSection(xyz_le=(0, 0, 0), chord=0.1), AvlSection(xyz_le=(0, 0, 0.3), chord=0.08)],
        )
        result = repr(surf)
        assert "NOWAKE" in result
        assert "NOALBE" in result
        assert "NOLOAD" in result


class TestAvlBody:
    def test_body_repr(self):
        from app.avl.geometry import AvlBody

        body = AvlBody(name="Fuselage", n_body=12, b_space=1.0, bfile="/tmp/fuselage.bfile")
        result = repr(body)
        assert "BODY" in result
        assert "Fuselage" in result
        assert "BFIL" in result

    def test_body_with_translate_yduplicate(self):
        from app.avl.geometry import AvlBody

        body = AvlBody(
            name="Nacelle",
            n_body=8,
            b_space=1.0,
            bfile="/tmp/nacelle.bfile",
            yduplicate=0.0,
            translate=(1.0, 0.5, 0.0),
        )
        result = repr(body)
        assert "YDUPLICATE" in result
        assert "TRANSLATE" in result


class TestAvlGeometryFile:
    def test_complete_file_structure(self):
        from app.avl.geometry import (
            AvlAfile,
            AvlGeometryFile,
            AvlReference,
            AvlSection,
            AvlSurface,
            AvlSymmetry,
        )

        avl_file = AvlGeometryFile(
            title="Test Aircraft",
            mach=0.0,
            symmetry=AvlSymmetry(iy_sym=0, iz_sym=0, z_sym=0.0),
            reference=AvlReference(s_ref=0.5, c_ref=0.2, b_ref=2.0, xyz_ref=(0.05, 0.0, 0.0)),
            surfaces=[
                AvlSurface(
                    name="Wing",
                    n_chord=12,
                    c_space=1.0,
                    yduplicate=0.0,
                    sections=[
                        AvlSection(xyz_le=(0.0, 0.0, 0.0), chord=0.2, airfoil=AvlAfile("/tmp/af.dat")),
                        AvlSection(xyz_le=(0.02, 1.0, 0.1), chord=0.15, airfoil=AvlAfile("/tmp/af.dat")),
                    ],
                ),
            ],
        )
        result = repr(avl_file)
        assert result.splitlines()[0] == "Test Aircraft"
        assert "SURFACE" in result
        assert "SECTION" in result
        assert "YDUPLICATE" in result

    def test_file_with_cdp(self):
        from app.avl.geometry import AvlGeometryFile, AvlReference, AvlSection, AvlSurface, AvlSymmetry

        avl_file = AvlGeometryFile(
            title="Test",
            mach=0.1,
            symmetry=AvlSymmetry(),
            reference=AvlReference(s_ref=1.0, c_ref=0.3, b_ref=3.0, xyz_ref=(0, 0, 0)),
            cdp=0.01,
            surfaces=[
                AvlSurface(
                    name="W",
                    n_chord=8,
                    c_space=1.0,
                    sections=[
                        AvlSection(xyz_le=(0, 0, 0), chord=0.3),
                        AvlSection(xyz_le=(0, 1.5, 0), chord=0.2),
                    ],
                )
            ],
        )
        result = repr(avl_file)
        assert "CDp" in result

    def test_file_with_body(self):
        from app.avl.geometry import AvlBody, AvlGeometryFile, AvlReference, AvlSymmetry

        avl_file = AvlGeometryFile(
            title="With Body",
            mach=0.0,
            symmetry=AvlSymmetry(),
            reference=AvlReference(s_ref=1.0, c_ref=0.3, b_ref=3.0, xyz_ref=(0, 0, 0)),
            bodies=[AvlBody(name="Fuselage", n_body=12, b_space=1.0, bfile="/tmp/fuse.bfile")],
        )
        result = repr(avl_file)
        assert "BODY" in result
        assert "Fuselage" in result
