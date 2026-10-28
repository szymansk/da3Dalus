"""gh-788 / gh-1187: ASB reference geometry (s_ref/b_ref/c_ref) comes from the wing
marked ``surface_type == main_wing`` - not from wings[0] (import order, gh-788) and not
from the largest planform (the pre-gh-1187 heuristic, removed).

The fast-tier tests mock the aerosandbox geometry calls so the selection logic runs in
pure Python; the integration class at the bottom uses real aerosandbox Wings.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app import schemas
from app.core.exceptions import ValidationDomainError
from app.schemas.aeroplaneschema import SurfaceType


def _wing_schema(
    name: str,
    surface_type: SurfaceType,
    *,
    root_chord: float,
    tip_chord: float,
    half_span: float,
    airfoil: str = "naca0012",
) -> schemas.AsbWingSchema:
    return schemas.AsbWingSchema(
        name=name,
        surface_type=surface_type,
        symmetric=True,
        x_secs=[
            schemas.WingXSecSchema(
                xyz_le=[0.0, 0.0, 0.0], chord=root_chord, twist=0.0, airfoil=airfoil
            ),
            schemas.WingXSecSchema(
                xyz_le=[0.0, half_span, 0.0], chord=tip_chord, twist=0.0, airfoil=airfoil
            ),
        ],
    )


def _mock_asb_wing(name: str, area: float, span: float, mac: float) -> MagicMock:
    w = MagicMock()
    w.name = name
    w.area.return_value = area
    w.span.return_value = span
    w.mean_aerodynamic_chord.return_value = mac
    w.xsecs = []
    w.symmetric = True
    return w


def _fake_airplane_init_factory(captured: dict):
    def fake_airplane_init(self, **kwargs):
        captured.update(kwargs)
        self.wings = kwargs.get("wings", [])
        self.fuselages = kwargs.get("fuselages", [])
        self.s_ref = kwargs.get("s_ref", 0.0)
        self.b_ref = kwargs.get("b_ref", 0.0)
        self.c_ref = kwargs.get("c_ref", 0.0)
        self.name = kwargs.get("name", "")

    return fake_airplane_init


def _convert_with_mocks(plane: schemas.AeroplaneSchema, asb_wings: list[MagicMock]) -> dict:
    """Run the converter with mocked asb.Wing objects; return the Airplane kwargs."""
    from app.converters.model_schema_converters import aeroplane_schema_to_asb_airplane_async

    captured: dict = {}
    with (
        patch("app.converters.model_schema_converters.asb.Wing", side_effect=asb_wings),
        patch(
            "app.converters.model_schema_converters.asb.Airplane.__init__",
            _fake_airplane_init_factory(captured),
        ),
        patch(
            "app.converters.model_schema_converters._asb_wing_xsecs_from_schema",
            return_value=[],
        ),
    ):
        aeroplane_schema_to_asb_airplane_async(plane)
    return captured


# ---------------------------------------------------------------------------
# Fast tier: selection by surface_type
# ---------------------------------------------------------------------------


class TestRefGeometryFromMainWing:
    """s_ref/b_ref/c_ref follow the wing marked main_wing, whatever the order or size."""

    def test_tail_first_order_uses_main_wing_refs(self):
        """gh-788: tail-first import order (HTP, Wing) must still use the main wing."""
        htp_mock = _mock_asb_wing("HTP", 0.33, 1.5, 0.22)
        wing_mock = _mock_asb_wing("Wing", 5.50, 8.0, 0.69)
        plane = schemas.AeroplaneSchema(
            name="tail-first-import",
            wings={
                "HTP": _wing_schema(
                    "HTP",
                    SurfaceType.HORIZONTAL_TAIL,
                    root_chord=0.22,
                    tip_chord=0.17,
                    half_span=0.75,
                ),
                "Wing": _wing_schema(
                    "Wing", SurfaceType.MAIN_WING, root_chord=0.8, tip_chord=0.55, half_span=4.0
                ),
            },
        )

        captured = _convert_with_mocks(plane, [htp_mock, wing_mock])

        assert captured["s_ref"] == pytest.approx(5.50, rel=1e-6)
        assert captured["b_ref"] == pytest.approx(8.0, rel=1e-6)
        assert captured["c_ref"] == pytest.approx(0.69, rel=1e-6)

    def test_wing_first_order_unchanged(self):
        wing_mock = _mock_asb_wing("Wing", 5.50, 8.0, 0.69)
        htp_mock = _mock_asb_wing("HTP", 0.33, 1.5, 0.22)
        plane = schemas.AeroplaneSchema(
            name="wing-first-import",
            wings={
                "Wing": _wing_schema(
                    "Wing", SurfaceType.MAIN_WING, root_chord=0.8, tip_chord=0.55, half_span=4.0
                ),
                "HTP": _wing_schema(
                    "HTP",
                    SurfaceType.HORIZONTAL_TAIL,
                    root_chord=0.22,
                    tip_chord=0.17,
                    half_span=0.75,
                ),
            },
        )

        captured = _convert_with_mocks(plane, [wing_mock, htp_mock])

        assert captured["s_ref"] == pytest.approx(5.50, rel=1e-6)
        assert captured["b_ref"] == pytest.approx(8.0, rel=1e-6)
        assert captured["c_ref"] == pytest.approx(0.69, rel=1e-6)

    def test_main_wing_smaller_than_tail_still_supplies_refs(self):
        """gh-1187: size does not decide. A main wing smaller than another surface wins."""
        tail_mock = _mock_asb_wing("Big", 9.0, 6.0, 1.5)
        main_mock = _mock_asb_wing("Small", 0.5, 2.0, 0.25)
        plane = schemas.AeroplaneSchema(
            name="small-main",
            wings={
                "Big": _wing_schema(
                    "Big", SurfaceType.TANDEM_WING, root_chord=1.5, tip_chord=1.5, half_span=3.0
                ),
                "Small": _wing_schema(
                    "Small", SurfaceType.MAIN_WING, root_chord=0.25, tip_chord=0.25, half_span=1.0
                ),
            },
        )

        captured = _convert_with_mocks(plane, [tail_mock, main_mock])

        assert captured["s_ref"] == pytest.approx(0.5, rel=1e-6)
        assert captured["b_ref"] == pytest.approx(2.0, rel=1e-6)
        assert captured["c_ref"] == pytest.approx(0.25, rel=1e-6)

    def test_no_wings_does_not_pass_ref_geometry(self):
        """An airplane without wings must not pass s_ref/b_ref/c_ref."""
        plane = schemas.AeroplaneSchema(name="no-wings")

        captured = _convert_with_mocks(plane, [])

        assert "s_ref" not in captured
        assert "b_ref" not in captured
        assert "c_ref" not in captured


class TestExactlyOneMainWingRequired:
    def test_zero_main_wings_raises(self):
        from app.converters.model_schema_converters import aeroplane_schema_to_asb_airplane_async

        plane = schemas.AeroplaneSchema(
            name="no-main",
            wings={
                "HTP": _wing_schema(
                    "HTP", SurfaceType.HORIZONTAL_TAIL, root_chord=0.2, tip_chord=0.2, half_span=0.5
                ),
            },
        )
        with pytest.raises(ValidationDomainError):
            aeroplane_schema_to_asb_airplane_async(plane)

    def test_two_main_wings_raises(self):
        from app.converters.model_schema_converters import aeroplane_schema_to_asb_airplane_async

        plane = schemas.AeroplaneSchema(
            name="two-main",
            wings={
                "A": _wing_schema(
                    "A", SurfaceType.MAIN_WING, root_chord=0.5, tip_chord=0.5, half_span=2.0
                ),
                "B": _wing_schema(
                    "B", SurfaceType.MAIN_WING, root_chord=0.5, tip_chord=0.5, half_span=2.0
                ),
            },
        )
        with pytest.raises(ValidationDomainError):
            aeroplane_schema_to_asb_airplane_async(plane)


class TestMainAsbWing:
    def test_none_for_airplane_without_wings(self):
        from app.converters.model_schema_converters import main_asb_wing

        assert main_asb_wing(MagicMock(wings=[])) is None

    def test_raises_for_airplane_not_built_by_converter(self):
        from app.converters.model_schema_converters import main_asb_wing

        airplane = MagicMock(wings=[_mock_asb_wing("W", 1.0, 2.0, 0.5)])
        airplane.main_wing_name = None
        with pytest.raises(ValueError):
            main_asb_wing(airplane)

    def test_returns_wing_named_by_converter(self):
        from app.converters.model_schema_converters import main_asb_wing

        tail = _mock_asb_wing("HTP", 0.3, 1.0, 0.2)
        main = _mock_asb_wing("Wing", 5.0, 8.0, 0.7)
        airplane = MagicMock(wings=[tail, main])
        airplane.main_wing_name = "Wing"
        assert main_asb_wing(airplane) is main


# ---------------------------------------------------------------------------
# Real aerosandbox integration (skipped if aerosandbox not installed)
# ---------------------------------------------------------------------------


asb = pytest.importorskip("aerosandbox", reason="aerosandbox not installed")
pytest.importorskip("app.converters.model_schema_converters")


@pytest.mark.requires_aerosandbox
class TestAsbAirplaneRefGeomIntegration:
    """End-to-end: build a real asb.Airplane from a tail-first schema and check that
    s_ref/b_ref/c_ref come from the wing marked main_wing (Spitfire-like case: HTP before Wing).
    """

    def _tail_first_plane(self, main_half_span: float, tail_half_span: float):
        return schemas.AeroplaneSchema(
            name="tail-first",
            wings={
                "HTP": _wing_schema(
                    "HTP",
                    SurfaceType.HORIZONTAL_TAIL,
                    root_chord=0.22,
                    tip_chord=0.17,
                    half_span=tail_half_span,
                ),
                "Wing": _wing_schema(
                    "Wing",
                    SurfaceType.MAIN_WING,
                    root_chord=0.80,
                    tip_chord=0.55,
                    half_span=main_half_span,
                    airfoil="naca2412",
                ),
            },
        )

    def test_tail_first_s_ref_from_main_wing(self):
        from app.converters.model_schema_converters import (
            aeroplane_schema_to_asb_airplane_async,
            main_asb_wing,
        )

        asb_airplane = aeroplane_schema_to_asb_airplane_async(
            self._tail_first_plane(main_half_span=4.0, tail_half_span=0.75)
        )
        main_wing = main_asb_wing(asb_airplane)
        htp = asb_airplane.wings[0]

        assert main_wing.name == "Wing"
        assert main_wing.area() > htp.area(), "fixture broken: main wing must exceed the HTP"
        assert asb_airplane.s_ref == pytest.approx(main_wing.area(), rel=0.01)
        assert asb_airplane.b_ref == pytest.approx(main_wing.span(), rel=0.01)
        assert asb_airplane.c_ref == pytest.approx(main_wing.mean_aerodynamic_chord(), rel=0.01)

    def test_tail_first_with_main_wing_smaller_than_tail(self):
        """The role decides, not the size: a main wing smaller than the HTP still wins."""
        from app.converters.model_schema_converters import (
            aeroplane_schema_to_asb_airplane_async,
            main_asb_wing,
        )

        asb_airplane = aeroplane_schema_to_asb_airplane_async(
            self._tail_first_plane(main_half_span=0.3, tail_half_span=2.0)
        )
        main_wing = main_asb_wing(asb_airplane)
        htp = asb_airplane.wings[0]

        assert main_wing.area() < htp.area(), "fixture broken: main wing must be the smaller"
        assert asb_airplane.s_ref == pytest.approx(main_wing.area(), rel=0.01)
        assert asb_airplane.s_ref != pytest.approx(htp.area(), rel=0.01)

    def test_wing_first_order_s_ref_unchanged(self):
        """Wing-first import must not be broken - regression guard."""
        from app.converters.model_schema_converters import aeroplane_schema_to_asb_airplane_async

        plane = schemas.AeroplaneSchema(
            name="wing-first",
            wings={
                "Wing": _wing_schema(
                    "Wing",
                    SurfaceType.MAIN_WING,
                    root_chord=0.80,
                    tip_chord=0.55,
                    half_span=4.0,
                    airfoil="naca2412",
                ),
                "HTP": _wing_schema(
                    "HTP",
                    SurfaceType.HORIZONTAL_TAIL,
                    root_chord=0.22,
                    tip_chord=0.17,
                    half_span=0.75,
                ),
            },
        )

        asb_airplane = aeroplane_schema_to_asb_airplane_async(plane)

        assert asb_airplane.s_ref == pytest.approx(asb_airplane.wings[0].area(), rel=0.01)
