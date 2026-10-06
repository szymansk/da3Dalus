"""gh-1157: fuselage sections with their own lower-half exponent (``n_lower``).

No module-level ``requires_aerosandbox`` marker, same as
``test_fuselage_symmetric_expansion.py``: only ``asb.FuselageXSec`` /
``asb.Fuselage`` constructors and closed-form properties are touched, so
the tests stay in the CI fast tier.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from aerosandbox import Fuselage, FuselageXSec
from pydantic import ValidationError
from scipy.special import gamma

from app import schemas
from app.converters.model_schema_converters import (
    _asb_fuselage_xsecs_from_schema,
    _mirror_fuselage_schema_y,
    fuselage_model_to_fuselage_config,
)
from app.converters.split_superellipse import (
    SplitSuperEllipseFuselageXSec,
    area_equivalent_exponent,
)
from app.models.aeroplanemodel import FuselageModel

N_TOP = 2.0
N_BOTTOM = 8.0


def _exact_area_fraction(n: float) -> float:
    """Exact super-ellipse area over the bounding w*h rectangle."""
    return gamma(1 + 1 / n) ** 2 / gamma(1 + 2 / n)


def _xsec(**kwargs) -> SplitSuperEllipseFuselageXSec:
    return SplitSuperEllipseFuselageXSec(
        xyz_c=[0.3, 0.0, 0.01],
        xyz_normal=[1.0, 0.0, 0.0],
        width=0.04,
        height=0.05,
        shape_upper=kwargs.get("upper", N_TOP),
        shape_lower=kwargs.get("lower", N_BOTTOM),
    )


def _plain(shape: float) -> FuselageXSec:
    return FuselageXSec(xyz_c=[0.3, 0.0, 0.01], width=0.04, height=0.05, shape=shape)


def _body(n_lower: float | None) -> schemas.FuselageSchema:
    return schemas.FuselageSchema(
        name="Rumpf",
        x_secs=[
            schemas.FuselageXSecSuperEllipseSchema(
                xyz=[0.0, 0.0, 0.0], a=0.02, b=0.025, n=N_TOP, n_lower=n_lower
            ),
            schemas.FuselageXSecSuperEllipseSchema(
                xyz=[0.4, 0.0, 0.0], a=0.02, b=0.025, n=N_TOP, n_lower=n_lower
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


class TestSchema:
    def test_n_lower_defaults_to_none(self):
        xsec = schemas.FuselageXSecSuperEllipseSchema(xyz=[0, 0, 0], a=0.1, b=0.1, n=2.0)
        assert xsec.n_lower is None

    def test_n_lower_round_trips_through_json(self):
        xsec = schemas.FuselageXSecSuperEllipseSchema(
            xyz=[0, 0, 0], a=0.1, b=0.1, n=2.0, n_lower=6.0
        )
        again = schemas.FuselageXSecSuperEllipseSchema.model_validate_json(xsec.model_dump_json())
        assert again.n_lower == pytest.approx(6.0)

    @pytest.mark.parametrize("bad", [0.0, -1.0])
    def test_n_lower_must_be_positive(self, bad):
        with pytest.raises(ValidationError):
            schemas.FuselageXSecSuperEllipseSchema(xyz=[0, 0, 0], a=0.1, b=0.1, n=2.0, n_lower=bad)


# ---------------------------------------------------------------------------
# Area-equivalent exponent
# ---------------------------------------------------------------------------


class TestAreaEquivalentExponent:
    def test_symmetric_section_keeps_its_exponent(self):
        assert area_equivalent_exponent(3.5, 3.5) == pytest.approx(3.5)

    def test_area_equals_mean_of_both_halves(self):
        n_eq = area_equivalent_exponent(N_TOP, N_BOTTOM)
        expected = 0.5 * (_plain(N_TOP).xsec_area() + _plain(N_BOTTOM).xsec_area())
        assert _plain(n_eq).xsec_area() == pytest.approx(expected, rel=1e-12)
        assert N_TOP < n_eq < N_BOTTOM

    def test_close_to_exact_gamma_area(self):
        # ASB's area law is an approximation (< 0.6 % error); the equivalent
        # exponent must inherit no more than that against the exact closed form.
        n_eq = area_equivalent_exponent(N_TOP, N_BOTTOM)
        exact = 0.5 * (_exact_area_fraction(N_TOP) + _exact_area_fraction(N_BOTTOM))
        assert _plain(n_eq).xsec_area() / (0.04 * 0.05) == pytest.approx(exact, rel=6e-3)


# ---------------------------------------------------------------------------
# Split ASB section
# ---------------------------------------------------------------------------


class TestSplitXSec:
    def test_upper_half_follows_n_and_lower_half_follows_n_lower(self):
        theta = np.linspace(0, 2 * np.pi, 361)[:-1]
        split = np.array(_xsec().get_3D_coordinates(theta))
        top = np.array(_plain(N_TOP).get_3D_coordinates(theta))
        bottom = np.array(_plain(N_BOTTOM).get_3D_coordinates(theta))
        upper = np.sin(theta) >= 0
        np.testing.assert_allclose(split[:, upper], top[:, upper])
        np.testing.assert_allclose(split[:, ~upper], bottom[:, ~upper])

    def test_outline_is_closed_at_the_waterline(self):
        # Both halves start at (±a, z_c). Approaching the waterline from below,
        # the lower half (n_lower = 8, z ~ |sin t|^(1/4)) closes onto that point.
        xsec = _xsec()
        _x, y0, z0 = xsec.get_3D_coordinates(np.array([0.0, np.pi]))
        assert z0[0] == pytest.approx(0.01)
        assert y0[0] == pytest.approx(-y0[1])
        gaps = []
        for step in (1e-2, 1e-6, 1e-10):
            _x, y, z = xsec.get_3D_coordinates(np.array([-step]))
            gaps.append(math.hypot(y[0] - y0[0], z[0] - z0[0]))
        assert gaps == sorted(gaps, reverse=True)
        assert gaps[-1] < 0.01 * xsec.height

    def test_default_theta_matches_asb(self):
        assert len(_xsec().get_3D_coordinates()[0]) == 60

    def test_perimeter_is_mean_of_both_halves(self):
        expected = 0.5 * (_plain(N_TOP).xsec_perimeter() + _plain(N_BOTTOM).xsec_perimeter())
        assert float(_xsec().xsec_perimeter()) == pytest.approx(float(expected))

    def test_shape_carries_area_equivalent_exponent(self):
        assert _xsec().shape == pytest.approx(area_equivalent_exponent(N_TOP, N_BOTTOM))

    def test_translate_keeps_both_exponents(self):
        moved = _xsec().translate([1.0, 0.0, 0.0])
        assert isinstance(moved, SplitSuperEllipseFuselageXSec)
        assert moved.shape_lower == pytest.approx(N_BOTTOM)
        assert "shape_lower" in repr(moved)


# ---------------------------------------------------------------------------
# Converters
# ---------------------------------------------------------------------------


class TestConverters:
    def test_symmetric_schema_builds_plain_asb_xsec(self):
        xsecs = _asb_fuselage_xsecs_from_schema(_body(None))
        assert all(type(xs) is FuselageXSec for xs in xsecs)
        assert xsecs[0].shape == pytest.approx(N_TOP)

    def test_equal_n_lower_builds_plain_asb_xsec(self):
        xsecs = _asb_fuselage_xsecs_from_schema(_body(N_TOP))
        assert all(type(xs) is FuselageXSec for xs in xsecs)

    def test_split_schema_builds_split_asb_xsec(self):
        xsecs = _asb_fuselage_xsecs_from_schema(_body(N_BOTTOM))
        assert all(isinstance(xs, SplitSuperEllipseFuselageXSec) for xs in xsecs)
        assert xsecs[1].shape_upper == pytest.approx(N_TOP)
        assert xsecs[1].shape_lower == pytest.approx(N_BOTTOM)
        # gh-706 axis convention unchanged.
        assert xsecs[1].width == pytest.approx(0.02)
        assert xsecs[1].height == pytest.approx(0.025)

    def test_mirror_keeps_n_lower(self):
        mirrored = _mirror_fuselage_schema_y(_body(N_BOTTOM))
        assert all(xs.n_lower == pytest.approx(N_BOTTOM) for xs in mirrored.x_secs)

    def test_mirrored_asb_xsec_stays_split(self):
        xsecs = _asb_fuselage_xsecs_from_schema(_body(N_BOTTOM), mirror_y=True)
        assert isinstance(xsecs[0], SplitSuperEllipseFuselageXSec)

    def test_model_path_builds_split_asb_xsec(self):
        model = FuselageModel.from_dict(
            name="Rumpf",
            data={
                "x_secs": [
                    {"xyz": [0.0, 0.0, 0.0], "a": 0.02, "b": 0.025, "n": 2.0, "n_lower": 8.0},
                    {"xyz": [0.4, 0.0, 0.0], "a": 0.02, "b": 0.025, "n": 2.0},
                ]
            },
        )
        xsecs = fuselage_model_to_fuselage_config(model).asb_fuselage.xsecs
        assert isinstance(xsecs[0], SplitSuperEllipseFuselageXSec)
        assert type(xsecs[1]) is FuselageXSec

    def test_split_body_volume_lies_between_both_symmetric_bodies(self):
        def volume(n_lower: float | None, n: float = N_TOP) -> float:
            body = _body(n_lower).model_copy(deep=True)
            for xs in body.x_secs:
                xs.n = n
            return float(Fuselage(xsecs=_asb_fuselage_xsecs_from_schema(body)).volume())

        round_body = volume(None, N_TOP)
        box_body = volume(None, N_BOTTOM)
        split_body = volume(N_BOTTOM)
        assert round_body < split_body < box_body
        assert split_body == pytest.approx(0.5 * (round_body + box_body), rel=1e-9)
        assert math.isfinite(split_body)


# ---------------------------------------------------------------------------
# REST round-trip
# ---------------------------------------------------------------------------


def test_put_and_get_fuselage_keep_n_lower(client_and_db):
    client, _ = client_and_db
    plane_id = client.post("/aeroplanes", params={"name": "Chekker"}).json()["id"]
    body = {
        "name": "Rumpf",
        "x_secs": [
            {"xyz": [0.0, 0.0, 0.0], "a": 0.02, "b": 0.025, "n": 2.0, "n_lower": 8.0},
            {"xyz": [0.4, 0.0, 0.0], "a": 0.02, "b": 0.025, "n": 2.0},
        ],
    }
    assert client.put(f"/aeroplanes/{plane_id}/fuselages/Rumpf", json=body).status_code == 201

    got = client.get(f"/aeroplanes/{plane_id}/fuselages/Rumpf").json()
    assert got["x_secs"][0]["n_lower"] == pytest.approx(8.0)
    assert got["x_secs"][1]["n_lower"] is None

    xsec = client.get(f"/aeroplanes/{plane_id}/fuselages/Rumpf/cross_sections/0").json()
    assert xsec["n_lower"] == pytest.approx(8.0)


def test_openvsp_slicer_refinement_skipped_for_asymmetric_sections(tmp_path, monkeypatch):
    """The STEP slicer fits symmetric super-ellipses only, so an imported
    fuselage with a VSP lower-half exponent keeps its handler sections."""
    import sys
    import types

    from app.core.config import settings
    from app.services import openvsp_import_service

    monkeypatch.setattr(settings, "ARTIFACTS_BASE_DIR", tmp_path)
    (tmp_path / "fuse.stp").write_text("FAKE")

    # Record calls instead of raising: the refinement swallows slicer errors,
    # and log capture depends on handler state other tests may change.
    slicer_calls: list[str] = []

    def _slicer_must_not_run(*_a, **_kw):
        slicer_calls.append("called")
        raise AssertionError("slicer must not run for asymmetric sections")

    fake_slicing = types.ModuleType("cad_designer.aerosandbox.slicing")
    fake_slicing.slice_step_at_stations = _slicer_must_not_run
    fake_slicing.slice_step_to_fuselage = _slicer_must_not_run
    fake_slicing.vsp_anchored_x_stations = _slicer_must_not_run
    monkeypatch.setitem(sys.modules, "cad_designer.aerosandbox.slicing", fake_slicing)

    handler_fuse = schemas.FuselageSchema(
        name="Body",
        x_secs=[
            schemas.FuselageXSecSuperEllipseSchema(xyz=[0.0, 0.0, 0.0], a=0.05, b=0.04, n=N_TOP),
            schemas.FuselageXSecSuperEllipseSchema(
                xyz=[0.5, 0.0, 0.0], a=0.05, b=0.04, n=N_TOP, n_lower=N_BOTTOM
            ),
        ],
    )

    result = openvsp_import_service._try_slicer_refinement("fuse.stp", handler_fuse, "Body")

    assert result is None
    assert slicer_calls == []
