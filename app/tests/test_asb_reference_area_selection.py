"""gh-788: ASB reference geometry (s_ref/b_ref/c_ref) must come from the
largest-planform wing, not from wings[0] (import order).

These tests run in the CI **fast** tier (no requires_aerosandbox marker)
by mocking the aerosandbox.Wing geometry calls so the selection logic is
exercised in pure Python without the heavy solver dependency.

One integration-style test with real aerosandbox Wings is included
but gated with pytest.importorskip so it skips gracefully when
aerosandbox is absent.
"""

from __future__ import annotations

from typing import NamedTuple
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Unit tests for the internal _find_reference_wing helper
# (pure Python, no aerosandbox needed)
# ---------------------------------------------------------------------------


class TestFindReferenceWing:
    """The reference wing is the one with the largest planform area."""

    def _make_wing(self, name: str, area: float) -> MagicMock:
        w = MagicMock()
        w.name = name
        w.area.return_value = area
        return w

    def test_largest_area_wing_selected(self):
        from app.converters.model_schema_converters import _find_reference_wing

        small_htp = self._make_wing("HTP", 0.33)
        small_vtp = self._make_wing("VTP", 0.21)
        large_main = self._make_wing("Wing", 5.50)

        ref = _find_reference_wing([small_htp, small_vtp, large_main])
        assert ref is large_main

    def test_wings_in_wing_first_order_unchanged(self):
        """When the main wing is already first, the result must still be the main wing."""
        from app.converters.model_schema_converters import _find_reference_wing

        large_main = self._make_wing("Wing", 5.50)
        small_htp = self._make_wing("HTP", 0.33)

        ref = _find_reference_wing([large_main, small_htp])
        assert ref is large_main

    def test_single_wing_returned(self):
        from app.converters.model_schema_converters import _find_reference_wing

        only_wing = self._make_wing("Wing", 2.0)
        ref = _find_reference_wing([only_wing])
        assert ref is only_wing

    def test_empty_list_returns_none(self):
        from app.converters.model_schema_converters import _find_reference_wing

        assert _find_reference_wing([]) is None


# ---------------------------------------------------------------------------
# Integration tests for aeroplane_schema_to_asb_airplane_async
# (mock asb.Airplane construction to capture passed s_ref/b_ref/c_ref)
# ---------------------------------------------------------------------------


class TestAsbAirplaneRefGeomFromLargestWing:
    """Verify that s_ref/b_ref/c_ref passed to asb.Airplane come from the
    largest-area wing regardless of iteration order.
    """

    def _make_asb_wing_mock(self, name: str, area: float, span: float, mac: float) -> MagicMock:
        w = MagicMock()
        w.name = name
        w.area.return_value = area
        w.span.return_value = span
        w.mean_aerodynamic_chord.return_value = mac
        w.xsecs = []
        w.symmetric = True
        return w

    def test_tail_first_order_uses_largest_wing_refs(self):
        """Tail-first import order (HTP, VTP, Wing) must still pick the Wing's ref geometry."""
        # Small HTP: 0.33 m², span 1.5 m, MAC 0.22 m
        # Large Wing: 5.50 m², span 8.0 m, MAC 0.69 m
        htp_mock = self._make_asb_wing_mock("HTP", 0.33, 1.5, 0.22)
        wing_mock = self._make_asb_wing_mock("Wing", 5.50, 8.0, 0.69)

        captured: dict = {}

        def fake_airplane_init(self, **kwargs):
            captured.update(kwargs)
            self.wings = kwargs.get("wings", [])
            self.fuselages = kwargs.get("fuselages", [])
            self.s_ref = kwargs.get("s_ref", 0.0)
            self.b_ref = kwargs.get("b_ref", 0.0)
            self.c_ref = kwargs.get("c_ref", 0.0)
            self.name = kwargs.get("name", "")

        with (
            patch(
                "app.converters.model_schema_converters.asb.Wing",
                side_effect=[htp_mock, wing_mock],
            ),
            patch(
                "app.converters.model_schema_converters.asb.Airplane.__init__",
                fake_airplane_init,
            ),
            patch(
                "app.converters.model_schema_converters._asb_wing_xsecs_from_schema",
                return_value=[],
            ),
        ):
            import aerosandbox as asb_real  # noqa: F401 — needed to import the module
            from app import schemas
            from app.converters.model_schema_converters import (
                aeroplane_schema_to_asb_airplane_async,
            )

            htp_wing_schema = schemas.AsbWingSchema(
                name="HTP",
                symmetric=True,
                x_secs=[
                    schemas.WingXSecSchema(
                        xyz_le=[0.0, 0.0, 0.0],
                        chord=0.22,
                        twist=0.0,
                        airfoil="naca0012",
                    ),
                    schemas.WingXSecSchema(
                        xyz_le=[0.0, 0.75, 0.0],
                        chord=0.17,
                        twist=0.0,
                        airfoil="naca0012",
                    ),
                ],
            )
            main_wing_schema = schemas.AsbWingSchema(
                name="Wing",
                symmetric=True,
                x_secs=[
                    schemas.WingXSecSchema(
                        xyz_le=[0.0, 0.0, 0.0],
                        chord=0.80,
                        twist=2.0,
                        airfoil="naca2412",
                    ),
                    schemas.WingXSecSchema(
                        xyz_le=[0.1, 4.0, 0.0],
                        chord=0.55,
                        twist=0.0,
                        airfoil="naca2412",
                    ),
                ],
            )

            plane = schemas.AeroplaneSchema(
                name="tail-first-import",
                # HTP first (as OpenVSP would import Spitfire)
                wings={"HTP": htp_wing_schema, "Wing": main_wing_schema},
            )

            aeroplane_schema_to_asb_airplane_async(plane)

        # The fix must pass Wing's geometry, not HTP's, to asb.Airplane
        assert "s_ref" in captured, "s_ref must be explicitly passed to asb.Airplane"
        assert captured["s_ref"] == pytest.approx(5.50, rel=1e-6)
        assert captured["b_ref"] == pytest.approx(8.0, rel=1e-6)
        assert captured["c_ref"] == pytest.approx(0.69, rel=1e-6)

    def test_wing_first_order_unchanged(self):
        """When the main wing is already first, refs stay on the main wing."""
        wing_mock = self._make_asb_wing_mock("Wing", 5.50, 8.0, 0.69)
        htp_mock = self._make_asb_wing_mock("HTP", 0.33, 1.5, 0.22)

        captured: dict = {}

        def fake_airplane_init(self, **kwargs):
            captured.update(kwargs)
            self.wings = kwargs.get("wings", [])
            self.fuselages = kwargs.get("fuselages", [])
            self.s_ref = kwargs.get("s_ref", 0.0)
            self.b_ref = kwargs.get("b_ref", 0.0)
            self.c_ref = kwargs.get("c_ref", 0.0)
            self.name = kwargs.get("name", "")

        with (
            patch(
                "app.converters.model_schema_converters.asb.Wing",
                side_effect=[wing_mock, htp_mock],
            ),
            patch(
                "app.converters.model_schema_converters.asb.Airplane.__init__",
                fake_airplane_init,
            ),
            patch(
                "app.converters.model_schema_converters._asb_wing_xsecs_from_schema",
                return_value=[],
            ),
        ):
            from app import schemas
            from app.converters.model_schema_converters import (
                aeroplane_schema_to_asb_airplane_async,
            )

            main_wing_schema = schemas.AsbWingSchema(
                name="Wing",
                symmetric=True,
                x_secs=[
                    schemas.WingXSecSchema(
                        xyz_le=[0.0, 0.0, 0.0],
                        chord=0.80,
                        twist=2.0,
                        airfoil="naca2412",
                    ),
                    schemas.WingXSecSchema(
                        xyz_le=[0.1, 4.0, 0.0],
                        chord=0.55,
                        twist=0.0,
                        airfoil="naca2412",
                    ),
                ],
            )
            htp_wing_schema = schemas.AsbWingSchema(
                name="HTP",
                symmetric=True,
                x_secs=[
                    schemas.WingXSecSchema(
                        xyz_le=[0.0, 0.0, 0.0],
                        chord=0.22,
                        twist=0.0,
                        airfoil="naca0012",
                    ),
                    schemas.WingXSecSchema(
                        xyz_le=[0.0, 0.75, 0.0],
                        chord=0.17,
                        twist=0.0,
                        airfoil="naca0012",
                    ),
                ],
            )

            plane = schemas.AeroplaneSchema(
                name="wing-first-import",
                wings={"Wing": main_wing_schema, "HTP": htp_wing_schema},
            )

            aeroplane_schema_to_asb_airplane_async(plane)

        assert captured["s_ref"] == pytest.approx(5.50, rel=1e-6)
        assert captured["b_ref"] == pytest.approx(8.0, rel=1e-6)
        assert captured["c_ref"] == pytest.approx(0.69, rel=1e-6)

    def test_no_wings_does_not_pass_ref_geometry(self):
        """An airplane without wings should not pass s_ref/b_ref/c_ref."""
        captured: dict = {}

        def fake_airplane_init(self, **kwargs):
            captured.update(kwargs)
            self.wings = kwargs.get("wings", [])
            self.fuselages = kwargs.get("fuselages", [])
            self.s_ref = 1.0
            self.b_ref = 1.0
            self.c_ref = 1.0
            self.name = kwargs.get("name", "")

        with patch(
            "app.converters.model_schema_converters.asb.Airplane.__init__",
            fake_airplane_init,
        ):
            from app import schemas
            from app.converters.model_schema_converters import (
                aeroplane_schema_to_asb_airplane_async,
            )

            plane = schemas.AeroplaneSchema(name="no-wings")
            aeroplane_schema_to_asb_airplane_async(plane)

        # s_ref/b_ref/c_ref must not be present when there are no wings
        assert "s_ref" not in captured
        assert "b_ref" not in captured
        assert "c_ref" not in captured


# ---------------------------------------------------------------------------
# Real aerosandbox integration (skipped if aerosandbox not installed)
# ---------------------------------------------------------------------------


asb = pytest.importorskip("aerosandbox", reason="aerosandbox not installed")
pytest.importorskip("app.converters.model_schema_converters")


@pytest.mark.requires_aerosandbox
class TestAsbAirplaneRefGeomIntegration:
    """End-to-end: build a real asb.Airplane from a tail-first schema and
    check that s_ref/b_ref/c_ref are from the main (largest) wing.

    Spitfire-like case: HTP (0.33 m²) comes before Wing (22 m²).
    Pre-fix: s_ref = 0.33 m²; post-fix: s_ref ≈ 22 m².
    """

    def _make_wing_schema(
        self,
        name: str,
        root_chord: float,
        tip_chord: float,
        half_span: float,
        airfoil: str = "naca0012",
    ):
        from app import schemas

        return schemas.AsbWingSchema(
            name=name,
            symmetric=True,
            x_secs=[
                schemas.WingXSecSchema(
                    xyz_le=[0.0, 0.0, 0.0],
                    chord=root_chord,
                    twist=0.0,
                    airfoil=airfoil,
                ),
                schemas.WingXSecSchema(
                    xyz_le=[0.0, half_span, 0.0],
                    chord=tip_chord,
                    twist=0.0,
                    airfoil=airfoil,
                ),
            ],
        )

    def test_tail_first_s_ref_from_main_wing(self):
        from app import schemas
        from app.converters.model_schema_converters import aeroplane_schema_to_asb_airplane_async

        # HTP: ~0.33 m² trapezoidal (root 0.22m, tip 0.17m, half_span 0.75m)
        htp = self._make_wing_schema("HTP", root_chord=0.22, tip_chord=0.17, half_span=0.75)
        # Main wing: ~5.25 m² (root 0.80m, tip 0.55m, half_span 4.0m)
        wing = self._make_wing_schema(
            "Wing", root_chord=0.80, tip_chord=0.55, half_span=4.0, airfoil="naca2412"
        )

        # HTP first — simulates tail-first OpenVSP import
        plane = schemas.AeroplaneSchema(
            name="tail-first",
            wings={"HTP": htp, "Wing": wing},
        )

        asb_airplane = aeroplane_schema_to_asb_airplane_async(plane)

        # The main wing half-span is 4.0 m → full symmetric span = 8.0 m
        # Trapezoidal area: 0.5*(0.80+0.55)*4.0*2 = 5.40 m² (symmetric)
        main_wing_area = asb_airplane.wings[1].area()  # "Wing" is second in list
        htp_area = asb_airplane.wings[0].area()  # "HTP" is first in list

        assert main_wing_area > htp_area, (
            f"Test fixture broken: main wing area {main_wing_area:.3f} must exceed HTP {htp_area:.3f}"
        )

        # THE CRITICAL ASSERTION: s_ref must come from the main wing, not the HTP
        assert asb_airplane.s_ref == pytest.approx(main_wing_area, rel=0.01), (
            f"s_ref={asb_airplane.s_ref:.4f} should equal main wing area "
            f"{main_wing_area:.4f} m², not HTP area {htp_area:.4f} m². "
            f"This indicates the gh-788 bug is not fixed."
        )
        assert asb_airplane.b_ref > asb_airplane.c_ref, (
            "b_ref (span) must be larger than c_ref (chord) for any normal wing"
        )

    def test_wing_first_order_s_ref_unchanged(self):
        """Wing-first import must not be broken by the fix — regression guard."""
        from app import schemas
        from app.converters.model_schema_converters import aeroplane_schema_to_asb_airplane_async

        wing = self._make_wing_schema(
            "Wing", root_chord=0.80, tip_chord=0.55, half_span=4.0, airfoil="naca2412"
        )
        htp = self._make_wing_schema("HTP", root_chord=0.22, tip_chord=0.17, half_span=0.75)

        plane = schemas.AeroplaneSchema(
            name="wing-first",
            wings={"Wing": wing, "HTP": htp},
        )

        asb_airplane = aeroplane_schema_to_asb_airplane_async(plane)
        main_wing_area = asb_airplane.wings[0].area()

        assert asb_airplane.s_ref == pytest.approx(main_wing_area, rel=0.01), (
            f"Wing-first regression: s_ref={asb_airplane.s_ref:.4f} should still equal "
            f"main wing area {main_wing_area:.4f}"
        )
