"""Reproduces gh-577: Trefftz/streamline VLM must run on a trim-consistent state.

When the request carries `operating_point_id`, the service must resolve the
stored trimmed OP server-side and overwrite the inline schema's
alpha (rad→deg), beta (rad→deg), xyz_ref, velocity, altitude, body rates,
and — critically — control-surface deflections. Deflections are sourced from
``control_deflections`` (manual override) if populated, otherwise from
``controls`` (the trim solver's output).
"""

from __future__ import annotations

import math
from unittest.mock import MagicMock

import pytest

from app.core.exceptions import NotFoundError, ValidationDomainError
from app.models.analysismodels import OperatingPointModel
from app.schemas.aeroanalysisschema import OperatingPointSchema, OperatingPointStatus


def _make_op(**overrides) -> OperatingPointModel:
    """Build a fake OperatingPointModel row with sensible defaults."""
    defaults = dict(
        id=42,
        name="cruise_trim",
        description="trimmed cruise",
        aircraft_id=1,
        config="clean",
        status=OperatingPointStatus.TRIMMED,
        warnings=[],
        controls={"elevator": -2.5, "aileron": 0.0},
        velocity=20.0,
        alpha=math.radians(4.2),  # stored in RADIANS
        beta=math.radians(0.5),
        p=0.0,
        q=0.0,
        r=0.0,
        xyz_ref=[0.183, 0.0, 0.0],
        altitude=100.0,
        control_deflections=None,
        trim_enrichment=None,
    )
    defaults.update(overrides)
    op = MagicMock(spec=OperatingPointModel)
    for k, v in defaults.items():
        setattr(op, k, v)
    return op


def _db_returning(op: OperatingPointModel | None) -> MagicMock:
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = op
    return db


class TestOperatingPointSchemaHasIdField:
    """The schema must accept an `operating_point_id` to bind a request to a stored OP."""

    def test_schema_accepts_operating_point_id(self):
        # gh-577: streamline/Trefftz requests bind to a trimmed OP by id.
        schema = OperatingPointSchema(operating_point_id=42)
        assert schema.operating_point_id == 42

    def test_schema_defaults_operating_point_id_to_none(self):
        schema = OperatingPointSchema()
        assert schema.operating_point_id is None


class TestResolveOperatingPoint:
    """The resolver pulls the trimmed state from a stored OperatingPointModel."""

    def test_returns_input_unchanged_when_no_id(self):
        from app.services.operating_point_resolver import resolve_operating_point

        inline = OperatingPointSchema(alpha=5.0, velocity=14.0, xyz_ref=[0.2, 0, 0])
        result = resolve_operating_point(MagicMock(), inline)
        assert result is inline

    def test_alpha_converted_from_radians_to_degrees(self):
        from app.services.operating_point_resolver import resolve_operating_point

        op = _make_op(alpha=math.radians(4.2))
        db = _db_returning(op)
        result = resolve_operating_point(
            db, OperatingPointSchema(operating_point_id=42, alpha=999.0)
        )
        assert result.alpha == pytest.approx(4.2, rel=1e-6)

    def test_beta_converted_from_radians_to_degrees(self):
        from app.services.operating_point_resolver import resolve_operating_point

        op = _make_op(beta=math.radians(0.5))
        result = resolve_operating_point(
            _db_returning(op), OperatingPointSchema(operating_point_id=42)
        )
        assert result.beta == pytest.approx(0.5, rel=1e-6)

    def test_xyz_ref_taken_from_stored_op(self):
        from app.services.operating_point_resolver import resolve_operating_point

        op = _make_op(xyz_ref=[0.183, 0.0, 0.0])
        result = resolve_operating_point(
            _db_returning(op),
            OperatingPointSchema(operating_point_id=42, xyz_ref=[0.0, 0.0, 0.0]),
        )
        assert result.xyz_ref == [0.183, 0.0, 0.0]

    def test_velocity_altitude_rates_taken_from_stored_op(self):
        from app.services.operating_point_resolver import resolve_operating_point

        op = _make_op(velocity=22.0, altitude=500.0, p=0.0, q=0.1, r=0.0)
        result = resolve_operating_point(
            _db_returning(op),
            OperatingPointSchema(operating_point_id=42, velocity=99.0, altitude=999.0),
        )
        assert result.velocity == 22.0
        assert result.altitude == 500.0
        assert result.q == pytest.approx(0.1)

    def test_control_deflections_from_controls_when_override_is_none(self):
        """Opti trim writes to `controls`; with no manual override we must use that."""
        from app.services.operating_point_resolver import resolve_operating_point

        op = _make_op(
            controls={"elevator": -2.5, "aileron": 0.0},
            control_deflections=None,
        )
        result = resolve_operating_point(
            _db_returning(op), OperatingPointSchema(operating_point_id=42)
        )
        assert result.control_deflections == {"elevator": -2.5, "aileron": 0.0}

    def test_control_deflections_override_wins_over_controls(self):
        """If the user PATCHed deflections, those take precedence over the trim output."""
        from app.services.operating_point_resolver import resolve_operating_point

        op = _make_op(
            controls={"elevator": -2.5},
            control_deflections={"elevator": -1.0},
        )
        result = resolve_operating_point(
            _db_returning(op), OperatingPointSchema(operating_point_id=42)
        )
        assert result.control_deflections == {"elevator": -1.0}

    def test_control_deflections_empty_dict_override_falls_back_to_controls(self):
        """An empty `control_deflections` (no-op override) must not erase the trim result."""
        from app.services.operating_point_resolver import resolve_operating_point

        op = _make_op(
            controls={"elevator": -2.5},
            control_deflections={},
        )
        result = resolve_operating_point(
            _db_returning(op), OperatingPointSchema(operating_point_id=42)
        )
        assert result.control_deflections == {"elevator": -2.5}

    def test_untrimmed_op_is_rejected_by_default(self):
        from app.services.operating_point_resolver import resolve_operating_point

        op = _make_op(status=OperatingPointStatus.NOT_TRIMMED)
        with pytest.raises(ValidationDomainError):
            resolve_operating_point(
                _db_returning(op), OperatingPointSchema(operating_point_id=42)
            )

    def test_dirty_op_is_rejected_by_default(self):
        from app.services.operating_point_resolver import resolve_operating_point

        op = _make_op(status=OperatingPointStatus.DIRTY)
        with pytest.raises(ValidationDomainError):
            resolve_operating_point(
                _db_returning(op), OperatingPointSchema(operating_point_id=42)
            )

    def test_missing_op_raises_not_found(self):
        from app.services.operating_point_resolver import resolve_operating_point

        with pytest.raises(NotFoundError):
            resolve_operating_point(
                _db_returning(None), OperatingPointSchema(operating_point_id=9999)
            )

    def test_require_trimmed_false_allows_untrimmed_for_diagnostic_use(self):
        """Diagnostic mode opts in to running on an untrimmed state."""
        from app.services.operating_point_resolver import resolve_operating_point

        op = _make_op(status=OperatingPointStatus.NOT_TRIMMED)
        result = resolve_operating_point(
            _db_returning(op),
            OperatingPointSchema(operating_point_id=42),
            require_trimmed=False,
        )
        assert result.operating_point_id == 42


class TestStreamlineServiceUsesResolvedOp:
    """`calculate_streamlines_json` must resolve the stored OP before running the VLM."""

    def test_streamlines_service_calls_resolver_then_analyse(self):
        import asyncio
        from unittest.mock import patch

        from app.services import analysis_service

        op = _make_op()
        plane_schema = MagicMock()

        resolved = OperatingPointSchema(
            operating_point_id=42,
            alpha=4.2,
            beta=0.5,
            velocity=20.0,
            altitude=100.0,
            xyz_ref=[0.183, 0.0, 0.0],
            control_deflections={"elevator": -2.5, "aileron": 0.0},
        )

        with patch.object(
            analysis_service, "get_aeroplane_schema_or_raise", return_value=plane_schema
        ), patch.object(
            analysis_service, "aeroplane_schema_to_asb_airplane_async"
        ) as mock_to_asb, patch(
            "app.services.operating_point_resolver.resolve_operating_point",
            return_value=resolved,
        ) as mock_resolver, patch.object(
            analysis_service, "analyse_aerodynamics"
        ) as mock_analyse:
            mock_to_asb.return_value = MagicMock()
            fake_fig = MagicMock()
            fake_fig.to_json.return_value = '{"data":[],"layout":{}}'
            mock_analyse.return_value = (MagicMock(), fake_fig)

            db = _db_returning(op)
            asyncio.run(
                analysis_service.calculate_streamlines_json(
                    db,
                    aeroplane_uuid="0" * 36,
                    operating_point=OperatingPointSchema(operating_point_id=42),
                )
            )

            mock_resolver.assert_called_once()
            # analyse_aerodynamics gets the RESOLVED schema, not the raw inline one
            call_op = mock_analyse.call_args.args[1]
            assert call_op.alpha == pytest.approx(4.2)
            assert call_op.control_deflections == {"elevator": -2.5, "aileron": 0.0}
            assert call_op.xyz_ref == [0.183, 0.0, 0.0]
