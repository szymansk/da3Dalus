"""gh-1146: the one conversion seam from super-ellipse half-axes to an ASB section.

``FuselageXSecSuperEllipseSchema.a`` / ``.b`` are half-axes (BR-F1); AeroSandbox's
``FuselageXSec.width`` / ``.height`` are full dimensions (ASB evaluates
``width / 2`` and ``height / 2``). The seam therefore produces ``width = 2a`` and
``height = 2b`` (Q-FD-3).

Only ASB constructors and closed-form properties are used, so the module stays in
the CI fast tier (same as ``test_fuselage_split_superellipse.py``).
"""

from __future__ import annotations

import math
from collections import OrderedDict

import pytest
from aerosandbox import FuselageXSec

from app import schemas
from app.converters.model_schema_converters import (
    _asb_fuselage_xsecs_from_schema,
    _build_asb_fuselages,
    fuselage_model_to_fuselage_config,
    fuselage_schema_to_fuselage_config,
)
from app.converters.split_superellipse import SplitSuperEllipseFuselageXSec
from app.converters.superellipse_asb import superellipse_to_asb_xsec
from app.models.aeroplanemodel import FuselageModel

A = 0.0226  # BRYAN's largest half-width in metres (issue #1146)
B = 0.0420  # BRYAN's largest half-height in metres


class TestSeam:
    def test_width_is_twice_the_half_axis_a(self):
        xsec = superellipse_to_asb_xsec(xyz=[0.1, 0.0, 0.0], a=A, b=B, n=2.0)
        assert xsec.width == pytest.approx(2.0 * A)

    def test_height_is_twice_the_half_axis_b(self):
        xsec = superellipse_to_asb_xsec(xyz=[0.1, 0.0, 0.0], a=A, b=B, n=2.0)
        assert xsec.height == pytest.approx(2.0 * B)

    def test_ellipse_area_is_pi_a_b(self):
        # Independent of ASB's convention: an ellipse with half-axes a, b has area pi*a*b.
        xsec = superellipse_to_asb_xsec(xyz=[0.0, 0.0, 0.0], a=A, b=B, n=2.0)
        assert float(xsec.xsec_area()) == pytest.approx(math.pi * A * B, rel=1e-9)

    def test_centre_normal_and_exponent_pass_through(self):
        xsec = superellipse_to_asb_xsec(xyz=[0.3, 0.01, -0.02], a=A, b=B, n=3.5)
        assert type(xsec) is FuselageXSec
        assert list(xsec.xyz_c) == pytest.approx([0.3, 0.01, -0.02])
        assert list(xsec.xyz_normal) == pytest.approx([1.0, 0.0, 0.0])
        assert xsec.shape == pytest.approx(3.5)

    def test_equal_n_lower_gives_a_plain_section(self):
        xsec = superellipse_to_asb_xsec(xyz=[0.0, 0.0, 0.0], a=A, b=B, n=2.0, n_lower=2.0)
        assert type(xsec) is FuselageXSec

    def test_split_section_also_gets_full_width_and_height(self):
        xsec = superellipse_to_asb_xsec(xyz=[0.0, 0.0, 0.0], a=A, b=B, n=2.0, n_lower=8.0)
        assert isinstance(xsec, SplitSuperEllipseFuselageXSec)
        assert xsec.width == pytest.approx(2.0 * A)
        assert xsec.height == pytest.approx(2.0 * B)
        assert xsec.shape_upper == pytest.approx(2.0)
        assert xsec.shape_lower == pytest.approx(8.0)


def _body() -> schemas.FuselageSchema:
    return schemas.FuselageSchema(
        name="BRYAN-like",
        x_secs=[
            schemas.FuselageXSecSuperEllipseSchema(xyz=[0.0, 0.0, 0.0], a=0.0, b=0.0, n=2.0),
            schemas.FuselageXSecSuperEllipseSchema(xyz=[0.1, 0.0, 0.0], a=A, b=B, n=2.0),
            schemas.FuselageXSecSuperEllipseSchema(xyz=[0.4, 0.0, 0.0], a=0.005, b=0.005, n=2.0),
        ],
    )


class TestEveryAppPathUsesTheSeam:
    def test_schema_path_builds_the_full_size_body(self):
        xsecs = _asb_fuselage_xsecs_from_schema(_body())
        assert max(float(x.width) for x in xsecs) == pytest.approx(2.0 * A)
        assert max(float(x.height) for x in xsecs) == pytest.approx(2.0 * B)

    def test_analysis_airplane_fuselage_is_full_size(self):
        (fuselage,) = _build_asb_fuselages(OrderedDict([("Body", _body())]))
        assert max(float(x.width) for x in fuselage.xsecs) == pytest.approx(2.0 * A)

    def test_cad_config_path_is_full_size(self):
        config = fuselage_schema_to_fuselage_config(_body())
        assert max(float(x.width) for x in config.asb_fuselage.xsecs) == pytest.approx(2.0 * A)

    def test_db_model_path_is_full_size(self):
        model = FuselageModel.from_dict(
            name="BRYAN-like",
            data={"x_secs": [xs.model_dump() for xs in _body().x_secs]},
        )
        xsecs = fuselage_model_to_fuselage_config(model).asb_fuselage.xsecs
        assert max(float(x.width) for x in xsecs) == pytest.approx(2.0 * A)
        assert max(float(x.height) for x in xsecs) == pytest.approx(2.0 * B)


class TestIntegralsOfTheAppBody:
    """Fuselage integrals that AeroBuildup depends on, against closed forms (gh-1146).

    An elliptic cylinder of half-axes a, b and length L: volume pi*a*b*L, wetted
    (lateral) area P*L with P the ellipse perimeter (Ramanujan's second
    approximation, relative error < 1e-9 at this a/b). A half-size body would give
    a quarter of the volume and half of the area.
    """

    A_CYL, B_CYL, LENGTH = 0.03, 0.05, 0.4

    def _cylinder(self):
        sections = [
            schemas.FuselageXSecSuperEllipseSchema(
                xyz=[x, 0.0, 0.0], a=self.A_CYL, b=self.B_CYL, n=2.0
            )
            for x in (0.0, self.LENGTH / 2, self.LENGTH)
        ]
        body = schemas.FuselageSchema(name="Cylinder", x_secs=sections)
        (fuselage,) = _build_asb_fuselages(OrderedDict([("Cylinder", body)]))
        return fuselage

    def test_volume_is_pi_a_b_length(self):
        expected = math.pi * self.A_CYL * self.B_CYL * self.LENGTH
        # ASB's section-area law is exact for n = 2; the frustum sum is exact for a cylinder.
        assert float(self._cylinder().volume()) == pytest.approx(expected, rel=1e-9)

    def test_wetted_area_is_perimeter_times_length(self):
        a, b = self.A_CYL, self.B_CYL
        h = ((a - b) / (a + b)) ** 2
        perimeter = math.pi * (a + b) * (1 + 3 * h / (10 + math.sqrt(4 - 3 * h)))
        # 1e-3: ASB evaluates the perimeter with its own closed-form approximation
        # (measured 2.1e-4 off Ramanujan here); a half-size body would be 0.5 off.
        assert float(self._cylinder().area_wetted()) == pytest.approx(
            perimeter * self.LENGTH, rel=1e-3
        )
