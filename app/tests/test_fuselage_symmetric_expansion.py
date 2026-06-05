"""gh-715 fuselage symmetric-expansion tests.

These tests live in their own file (no module-level
``requires_aerosandbox`` / ``requires_cadquery`` marker) so they run
in the CI **fast** tier and contribute to SonarCloud's new-code
coverage. The mirroring logic is fast and only touches
``asb.Fuselage`` / ``asb.FuselageXSec`` constructors — no heavy
solver code, no CadQuery topology — so it's safe to leave unmarked.
"""

from __future__ import annotations

import pytest

from app.schemas import aeroplaneschema as schemas


def _make_strut(symmetric: bool = True) -> schemas.FuselageSchema:
    """Build a minimal off-spine sub-fuselage suitable for mirror checks.

    Note: both xsecs sit at x=0 (a purely vertical leg), so the body has zero
    x-spine length/volume — i.e. it is *degenerate* for AeroBuildup (gh-790).
    Used for the CAD-config / pure-Python mirror tests, where that is fine.
    """
    return schemas.FuselageSchema(
        name="Strut",
        symmetric=symmetric,
        x_secs=[
            schemas.FuselageXSecSuperEllipseSchema(xyz=[0.0, 0.6, -0.3], a=0.02, b=0.02, n=2.0),
            schemas.FuselageXSecSuperEllipseSchema(xyz=[0.0, 0.6, -1.0], a=0.02, b=0.02, n=2.0),
        ],
    )


def _make_pod(symmetric: bool = True) -> schemas.FuselageSchema:
    """Build an off-spine sub-fuselage with a real x-extent (non-degenerate),
    so it survives the gh-790 aero-model guard while still exercising the
    mirror-expansion (Y-flip) logic."""
    return schemas.FuselageSchema(
        name="Pod",
        symmetric=symmetric,
        x_secs=[
            schemas.FuselageXSecSuperEllipseSchema(xyz=[0.0, 0.6, 0.0], a=0.05, b=0.05, n=2.0),
            schemas.FuselageXSecSuperEllipseSchema(xyz=[0.5, 0.6, 0.0], a=0.05, b=0.05, n=2.0),
        ],
    )


class TestMirrorFuselageSchemaY:
    """``_mirror_fuselage_schema_y`` is pure-Python — no asb needed."""

    def test_flips_y_keeps_xz(self):
        from app.converters.model_schema_converters import _mirror_fuselage_schema_y

        original = _make_strut(symmetric=True)
        mirror = _mirror_fuselage_schema_y(original)
        assert mirror.name == "Strut (mirror)"
        # Mirrored half is not symmetric — IS the other half already.
        assert mirror.symmetric is False
        assert mirror.x_secs[0].xyz == [0.0, -0.6, -0.3]
        assert mirror.x_secs[1].xyz == [0.0, -0.6, -1.0]

    def test_shape_unchanged(self):
        from app.converters.model_schema_converters import _mirror_fuselage_schema_y

        original = _make_strut()
        mirror = _mirror_fuselage_schema_y(original)
        for o_xs, m_xs in zip(original.x_secs, mirror.x_secs, strict=True):
            assert m_xs.a == o_xs.a
            assert m_xs.b == o_xs.b
            assert m_xs.n == o_xs.n

    def test_does_not_mutate_original(self):
        from app.converters.model_schema_converters import _mirror_fuselage_schema_y

        original = _make_strut()
        _mirror_fuselage_schema_y(original)
        assert original.x_secs[0].xyz == [0.0, 0.6, -0.3]
        assert original.symmetric is True


class TestBuildAsbFuselages:
    """``_build_asb_fuselages`` instantiates ``asb.Fuselage`` — needs the
    aerosandbox import but no solver. Safe in fast tier.
    """

    def test_symmetric_emits_primary_and_mirror(self):
        from collections import OrderedDict

        from app.converters.model_schema_converters import _build_asb_fuselages

        result = _build_asb_fuselages(OrderedDict([("Pod", _make_pod(symmetric=True))]))
        assert len(result) == 2
        assert result[0].name == "Pod"
        assert result[1].name == "Pod (mirror)"
        # Y centres flipped on the mirror, X/Z preserved.
        assert result[0].xsecs[0].xyz_c[1] == pytest.approx(0.6)
        assert result[1].xsecs[0].xyz_c[1] == pytest.approx(-0.6)
        assert result[1].xsecs[0].xyz_c[0] == result[0].xsecs[0].xyz_c[0]
        assert result[1].xsecs[0].xyz_c[2] == result[0].xsecs[0].xyz_c[2]

    def test_non_symmetric_stays_single(self):
        from collections import OrderedDict

        from app.converters.model_schema_converters import _build_asb_fuselages

        result = _build_asb_fuselages(OrderedDict([("Main", _make_pod(symmetric=False))]))
        assert len(result) == 1
        assert result[0].name == "Main"

    def test_degenerate_strut_skipped_from_aero_model(self):
        # gh-790: a zero-x-length strut would make AeroBuildup return all-NaN,
        # so it is dropped from the ASB aero model (the CAD mirror path keeps it).
        from collections import OrderedDict

        from app.converters.model_schema_converters import _build_asb_fuselages

        result = _build_asb_fuselages(OrderedDict([("Strut", _make_strut(symmetric=True))]))
        assert result == []

    def test_skips_empty_xsecs(self):
        from collections import OrderedDict

        from app.converters.model_schema_converters import _build_asb_fuselages

        empty = schemas.FuselageSchema.model_construct(name="Empty", symmetric=False, x_secs=[])
        result = _build_asb_fuselages(OrderedDict([("Empty", empty)]))
        assert result == []


class TestFuselageConfigsWithMirrors:
    """``_fuselage_configs_with_mirrors`` is the CAD-config equivalent
    of ``_build_asb_fuselages``. Its symmetric-expansion path is
    otherwise only reachable through the cadquery-dependent
    ``aeroplane_schema_to_airplane_configuration_async`` — extracting
    it as a helper lets us unit-test the expansion in fast tier.
    """

    def test_symmetric_emits_two_configs(self):
        from collections import OrderedDict

        from app.converters.model_schema_converters import _fuselage_configs_with_mirrors

        configs = _fuselage_configs_with_mirrors(
            OrderedDict([("Strut", _make_strut(symmetric=True))])
        )
        assert len(configs) == 2
        assert configs[0].name == "Strut"
        assert configs[1].name == "Strut (mirror)"

    def test_non_symmetric_stays_single(self):
        from collections import OrderedDict

        from app.converters.model_schema_converters import _fuselage_configs_with_mirrors

        configs = _fuselage_configs_with_mirrors(
            OrderedDict([("Strut", _make_strut(symmetric=False))])
        )
        assert len(configs) == 1
        assert configs[0].name == "Strut"


class TestAsbFuselageXSecsMirrorY:
    """``_asb_fuselage_xsecs_from_schema(mirror_y=True)`` flips just the
    y centre of each xsec — primary and mirror share the same xsec
    instances otherwise.
    """

    def test_mirror_y_flips_only_y(self):
        from app.converters.model_schema_converters import (
            _asb_fuselage_xsecs_from_schema,
        )

        fuse = _make_strut(symmetric=True)
        primary = _asb_fuselage_xsecs_from_schema(fuse, mirror_y=False)
        mirror = _asb_fuselage_xsecs_from_schema(fuse, mirror_y=True)
        for p, m in zip(primary, mirror, strict=True):
            assert m.xyz_c[0] == p.xyz_c[0]
            assert m.xyz_c[1] == -p.xyz_c[1]
            assert m.xyz_c[2] == p.xyz_c[2]
            assert m.width == p.width
            assert m.height == p.height
