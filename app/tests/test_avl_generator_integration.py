"""Integration tests for the AVL geometry builder."""

from __future__ import annotations

from collections import OrderedDict

from app.avl.geometry import AvlGeometryFile
from app.schemas.aeroanalysisschema import CdclConfig, OperatingPointSchema, SpacingConfig
from app.schemas.aeroplaneschema import (
    AeroplaneSchema,
    AsbWingSchema,
    ControlSurfaceSchema,
    WingXSecSchema,
)


def _make_plane_schema():
    return AeroplaneSchema(
        name="TestPlane",
        wings=OrderedDict(
            {
                "Main Wing": AsbWingSchema(
                    name="Main Wing",
                    symmetric=True,
                    x_secs=[
                        WingXSecSchema(
                            xyz_le=[0.0, 0.0, 0.0],
                            chord=0.2,
                            twist=2.0,
                            airfoil="naca2412",
                            control_surface=ControlSurfaceSchema(
                                name="aileron",
                                hinge_point=0.75,
                                symmetric=False,
                                deflection=0.0,
                            ),
                        ),
                        WingXSecSchema(
                            xyz_le=[0.02, 1.0, 0.1],
                            chord=0.15,
                            twist=0.0,
                            airfoil="naca2412",
                        ),
                    ],
                ),
            }
        ),
        xyz_ref=[0.05, 0.0, 0.0],
    )


class TestBuildAvlGeometryFile:
    def test_produces_valid_avl_file(self):
        from app.services.avl_geometry_service import build_avl_geometry_file

        avl_file = build_avl_geometry_file(_make_plane_schema(), SpacingConfig(auto_optimise=False))
        assert isinstance(avl_file, AvlGeometryFile)
        assert avl_file.title == "TestPlane"
        assert len(avl_file.surfaces) == 1
        content = repr(avl_file)
        assert "SURFACE" in content
        assert "Main Wing" in content
        assert "YDUPLICATE" in content

    def test_includes_control_surfaces(self):
        from app.services.avl_geometry_service import build_avl_geometry_file

        avl_file = build_avl_geometry_file(_make_plane_schema(), SpacingConfig(auto_optimise=False))
        content = repr(avl_file)
        assert "CONTROL" in content
        assert "aileron" in content

    def test_sections_have_correct_geometry(self):
        from app.services.avl_geometry_service import build_avl_geometry_file

        avl_file = build_avl_geometry_file(_make_plane_schema(), SpacingConfig(auto_optimise=False))
        sec0 = avl_file.surfaces[0].sections[0]
        assert sec0.chord == 0.2
        assert sec0.ainc == 2.0  # twist
        assert sec0.xyz_le == (0.0, 0.0, 0.0)

    def test_auto_optimise_increases_nchord(self):
        from app.services.avl_geometry_service import build_avl_geometry_file

        avl_file = build_avl_geometry_file(
            _make_plane_schema(), SpacingConfig(auto_optimise=True, n_chord=12)
        )
        assert avl_file.surfaces[0].n_chord >= 16  # has control surfaces

    def test_cdcl_is_zeros_in_editor_mode(self):
        from app.services.avl_geometry_service import build_avl_geometry_file

        avl_file = build_avl_geometry_file(_make_plane_schema(), SpacingConfig(auto_optimise=False))
        for surf in avl_file.surfaces:
            for sec in surf.sections:
                assert sec.cdcl is not None
                assert sec.cdcl.is_zero()

    def test_generate_avl_content_from_schema(self):
        from app.services.avl_geometry_service import generate_avl_content_from_schema

        content = generate_avl_content_from_schema(
            _make_plane_schema(), SpacingConfig(auto_optimise=False)
        )
        assert isinstance(content, str)
        assert "SURFACE" in content
        assert "CDCL" in content


class TestInjectCdcl:
    def test_replaces_zero_cdcl(self):
        from app.services.avl_geometry_service import build_avl_geometry_file, inject_cdcl

        avl_file = build_avl_geometry_file(_make_plane_schema(), SpacingConfig(auto_optimise=False))
        op = OperatingPointSchema(velocity=30.0, altitude=0.0)
        inject_cdcl(avl_file, _make_plane_schema(), op, CdclConfig())
        for surf in avl_file.surfaces:
            for sec in surf.sections:
                assert not sec.cdcl.is_zero()
                assert sec.cdcl.cd_0 > 0

    def test_preserves_nonzero_cdcl(self):
        from app.avl.geometry import AvlCdcl
        from app.services.avl_geometry_service import build_avl_geometry_file, inject_cdcl

        avl_file = build_avl_geometry_file(_make_plane_schema(), SpacingConfig(auto_optimise=False))
        user_cdcl = AvlCdcl(cl_min=-0.5, cd_min=0.02, cl_0=0.1, cd_0=0.009, cl_max=1.2, cd_max=0.04)
        avl_file.surfaces[0].sections[0].cdcl = user_cdcl
        op = OperatingPointSchema(velocity=30.0, altitude=0.0)
        inject_cdcl(avl_file, _make_plane_schema(), op, CdclConfig())
        # First section: user-edited, preserved
        assert avl_file.surfaces[0].sections[0].cdcl == user_cdcl
        # Second section: was zero, now replaced
        assert not avl_file.surfaces[0].sections[1].cdcl.is_zero()

    def test_inject_cdcl_with_none_section_cdcl(self):
        from app.services.avl_geometry_service import build_avl_geometry_file, inject_cdcl

        avl_file = build_avl_geometry_file(_make_plane_schema(), SpacingConfig(auto_optimise=False))
        avl_file.surfaces[0].sections[0].cdcl = None
        op = OperatingPointSchema(velocity=30.0, altitude=0.0)
        inject_cdcl(avl_file, _make_plane_schema(), op, CdclConfig())
        assert avl_file.surfaces[0].sections[0].cdcl is not None
        assert avl_file.surfaces[0].sections[0].cdcl.cd_0 > 0

    def test_inject_cdcl_surface_wing_mismatch_logs_warning(self, caplog):
        import logging

        from app.avl.geometry import AvlCdcl, AvlSection, AvlSurface
        from app.services.avl_geometry_service import build_avl_geometry_file, inject_cdcl

        avl_file = build_avl_geometry_file(_make_plane_schema(), SpacingConfig(auto_optimise=False))
        avl_file.surfaces.append(
            AvlSurface(
                name="Extra",
                n_chord=8,
                c_space=1.0,
                sections=[AvlSection(xyz_le=(0, 0, 0), chord=0.1, cdcl=AvlCdcl.zeros())],
            )
        )
        op = OperatingPointSchema(velocity=30.0, altitude=0.0)
        with caplog.at_level(logging.WARNING, logger="app.services.avl_geometry_service"):
            inject_cdcl(avl_file, _make_plane_schema(), op, CdclConfig())
        assert "mismatch" in caplog.text
        assert not avl_file.surfaces[0].sections[0].cdcl.is_zero()


class TestBuildAirfoilNode:
    def test_naca_airfoil(self):
        from app.avl.geometry import AvlNaca
        from app.services.avl_geometry_service import _build_airfoil_node

        result = _build_airfoil_node("naca2412")
        assert isinstance(result, AvlNaca)
        assert result.digits == "2412"

    def test_naca5_airfoil(self):
        from app.avl.geometry import AvlNaca
        from app.services.avl_geometry_service import _build_airfoil_node

        result = _build_airfoil_node("NACA23012")
        assert isinstance(result, AvlNaca)
        assert result.digits == "23012"

    def test_unknown_falls_back_to_naca0012(self):
        from app.avl.geometry import AvlNaca
        from app.services.avl_geometry_service import _build_airfoil_node

        result = _build_airfoil_node("nonexistent_airfoil_xyz")
        assert isinstance(result, AvlNaca)
        assert result.digits == "0012"


    def test_naca_decimal_thickness_falls_through_to_file(self):
        """gh-588 (regression of gh-409): a decimal in a NACA-style name is NOT
        a valid 4-/5-digit NACA designation. AVL's ``NACA`` keyword expects an
        integer code (e.g. 2412, 23012) and crashes with ``Read error`` on a
        decimal value. The generator must therefore route ``naca23013.5`` to
        the file-resolution branch (``AFIL <path/naca23013.5.dat>``), which
        AVL accepts.
        """
        from app.avl.geometry import AvlAfile
        from app.services.avl_geometry_service import _build_airfoil_node

        result = _build_airfoil_node("naca23013.5")
        assert isinstance(result, AvlAfile), (
            "Decimal-named airfoils must resolve to AFIL so AVL can parse the "
            "geometry; emitting NACA with a decimal designation triggers a "
            "Read error on the AVL side (gh-588)."
        )
        assert result.filepath.endswith("naca23013.5.dat")

    def test_naca_decimal_thickness_case_insensitive_falls_through_to_file(self):
        """gh-588: same as above with upper-case spelling."""
        from app.avl.geometry import AvlAfile
        from app.services.avl_geometry_service import _build_airfoil_node

        result = _build_airfoil_node("NACA23013.5")
        assert isinstance(result, AvlAfile)
        assert result.filepath.endswith("naca23013.5.dat")

    def test_generated_avl_uses_afil_not_naca_for_decimal_airfoil(self):
        """gh-588 end-to-end: the serialised ``.avl`` content for a decimal-named
        airfoil must contain ``AFIL <path>`` and must NOT contain a bare
        ``NACA\\n23013.5`` line that AVL would reject.
        """
        from app.services.avl_geometry_service import _build_airfoil_node

        node = _build_airfoil_node("naca23013.5")
        serialised = repr(node)
        assert "AFIL" in serialised
        assert "naca23013.5.dat" in serialised
        # The bare decimal designation must not appear on its own line — AVL's
        # NACA-keyword parser would choke on it.
        assert "NACA\n23013.5" not in serialised
        assert "23013.5\n" != serialised  # not a stand-alone integer line


class TestBuildGeometryEdgeCases:
    def test_no_control_surfaces_wing(self):
        from app.services.avl_geometry_service import build_avl_geometry_file

        plane = AeroplaneSchema(
            name="NoCtrlPlane",
            wings=OrderedDict(
                {
                    "Plain Wing": AsbWingSchema(
                        name="Plain Wing",
                        symmetric=False,
                        x_secs=[
                            WingXSecSchema(xyz_le=[0.0, 0.0, 0.0], chord=0.2, twist=0.0, airfoil="naca0012"),
                            WingXSecSchema(xyz_le=[0.0, 1.0, 0.0], chord=0.1, twist=0.0, airfoil="naca0012"),
                        ],
                    ),
                }
            ),
            xyz_ref=[0, 0, 0],
        )
        avl_file = build_avl_geometry_file(plane, SpacingConfig(auto_optimise=False))
        assert len(avl_file.surfaces) == 1
        content = repr(avl_file)
        assert "CONTROL" not in content
