"""gh-790: a degenerate imported fuselage (zero length / zero volume) makes
AeroBuildup return all-NaN (divide-by-zero in fineness_ratio / log10(Re)).

AeroSandbox is third-party and can't be patched, so the converter must drop
a degenerate fuselage from the ASB aero model (with a warning) instead of
feeding NaN-poison into the solve. The separate CAD pipeline is unaffected.

These tests need aerosandbox importable (it is in the PR-fast/coverage tier)
but do not run a solver.
"""

from __future__ import annotations

import logging

import pytest

from app import schemas
from app.converters.model_schema_converters import (
    _asb_fuselage_is_degenerate,
    _build_asb_fuselages,
)


def _xsec(x: float, a: float, b: float, n: float = 2.0):
    return schemas.FuselageXSecSuperEllipseSchema(xyz=[x, 0.0, 0.0], a=a, b=b, n=n)


def _fuselage(name: str, xsecs, symmetric: bool = False):
    return schemas.FuselageSchema(name=name, x_secs=xsecs, symmetric=symmetric)


def _normal_xsecs():
    # length 1.0 m, non-zero radii → finite volume
    return [_xsec(0.0, 0.05, 0.05), _xsec(0.5, 0.2, 0.2), _xsec(1.0, 0.05, 0.05)]


def _degenerate_zero_length():
    # all sections at the same x → length 0
    return [_xsec(0.0, 0.2, 0.2), _xsec(0.0, 0.2, 0.2)]


def _degenerate_zero_volume():
    # finite length but zero radii → zero volume
    return [_xsec(0.0, 0.0, 0.0), _xsec(1.0, 0.0, 0.0)]


class TestIsDegenerate:
    def test_zero_length_is_degenerate(self):
        from aerosandbox import Fuselage

        from app.converters.model_schema_converters import _asb_fuselage_xsecs_from_schema

        fus = Fuselage(
            name="z",
            xsecs=_asb_fuselage_xsecs_from_schema(_fuselage("z", _degenerate_zero_length())),
        )
        assert _asb_fuselage_is_degenerate(fus) is True

    def test_zero_volume_is_degenerate(self):
        from aerosandbox import Fuselage

        from app.converters.model_schema_converters import _asb_fuselage_xsecs_from_schema

        fus = Fuselage(
            name="v",
            xsecs=_asb_fuselage_xsecs_from_schema(_fuselage("v", _degenerate_zero_volume())),
        )
        assert _asb_fuselage_is_degenerate(fus) is True

    def test_normal_fuselage_is_not_degenerate(self):
        from aerosandbox import Fuselage

        from app.converters.model_schema_converters import _asb_fuselage_xsecs_from_schema

        fus = Fuselage(
            name="ok", xsecs=_asb_fuselage_xsecs_from_schema(_fuselage("ok", _normal_xsecs()))
        )
        assert _asb_fuselage_is_degenerate(fus) is False
        # sanity: a normal fuselage yields a finite fineness ratio
        import math

        assert math.isfinite(fus.fineness_ratio())


class TestBuildAsbFuselagesGuard:
    def test_degenerate_fuselage_is_skipped_with_warning(self, caplog):
        fuses = {"deg": _fuselage("deg", _degenerate_zero_length())}
        with caplog.at_level(logging.WARNING):
            result = _build_asb_fuselages(fuses)
        assert result == []
        assert any("deg" in r.message for r in caplog.records)

    def test_normal_fuselage_is_kept(self):
        fuses = {"body": _fuselage("body", _normal_xsecs())}
        result = _build_asb_fuselages(fuses)
        assert len(result) == 1
        import math

        assert math.isfinite(result[0].fineness_ratio())

    def test_symmetric_normal_fuselage_expands_to_pair(self):
        fuses = {"body": _fuselage("body", _normal_xsecs(), symmetric=True)}
        result = _build_asb_fuselages(fuses)
        assert len(result) == 2

    def test_mixed_keeps_only_finite_fuselages(self):
        fuses = {
            "deg": _fuselage("deg", _degenerate_zero_volume()),
            "body": _fuselage("body", _normal_xsecs()),
        }
        result = _build_asb_fuselages(fuses)
        assert len(result) == 1
        assert result[0].name == "body"
