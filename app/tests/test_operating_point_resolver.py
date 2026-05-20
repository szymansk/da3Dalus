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

    def test_aircraft_pk_scopes_the_lookup(self):
        """gh-577 review CRITICAL: an OP belonging to a different aircraft must NOT resolve."""
        from app.services.operating_point_resolver import resolve_operating_point

        db = MagicMock()
        # `.filter().filter().first()` returns None — the row exists for the id
        # but not for the (id, aircraft_id) pair.
        db.query.return_value.filter.return_value.filter.return_value.first.return_value = (
            None
        )
        with pytest.raises(NotFoundError):
            resolve_operating_point(
                db,
                OperatingPointSchema(operating_point_id=42),
                aircraft_pk=999,
            )

    def test_missing_altitude_raises_validation(self):
        """A row with a NULL NOT-NULL field is corrupt — surface it loudly."""
        from app.services.operating_point_resolver import resolve_operating_point

        op = _make_op(altitude=None)
        with pytest.raises(ValidationDomainError):
            resolve_operating_point(
                _db_returning(op), OperatingPointSchema(operating_point_id=42)
            )

    def test_empty_xyz_ref_raises_validation(self):
        from app.services.operating_point_resolver import resolve_operating_point

        op = _make_op(xyz_ref=[])
        with pytest.raises(ValidationDomainError):
            resolve_operating_point(
                _db_returning(op), OperatingPointSchema(operating_point_id=42)
            )


class TestValidateDeflectionsAgainstAirplane:
    """gh-577 review CRITICAL: surface-name mismatches must fail loudly, not silently."""

    def _make_airplane(self, surface_names: list[str]):
        """Build a stub airplane with one wing/one xsec carrying named control surfaces."""
        airplane = MagicMock()
        # MagicMock's `name` kwarg is reserved for the mock's repr; set
        # the attribute after construction.
        surfaces = [MagicMock() for _ in surface_names]
        for surf, n in zip(surfaces, surface_names, strict=True):
            surf.name = n
        xsec = MagicMock()
        xsec.control_surfaces = surfaces
        wing = MagicMock()
        wing.xsecs = [xsec]
        airplane.wings = [wing]
        return airplane

    def test_passes_when_all_names_match(self):
        from app.services.operating_point_resolver import (
            validate_deflections_against_airplane,
        )

        airplane = self._make_airplane(["elevator", "aileron"])
        # No exception
        validate_deflections_against_airplane(
            airplane, {"elevator": -2.0, "aileron": 0.5}
        )

    def test_raises_listing_unknown_names(self):
        from app.services.operating_point_resolver import (
            validate_deflections_against_airplane,
        )

        airplane = self._make_airplane(["elevator"])
        with pytest.raises(ValidationDomainError) as exc:
            validate_deflections_against_airplane(
                airplane, {"elevator": -2.0, "rudder": 1.0}
            )
        assert "rudder" in exc.value.message
        assert "elevator" in exc.value.message  # listed as available

    def test_noop_when_deflections_empty_or_none(self):
        from app.services.operating_point_resolver import (
            validate_deflections_against_airplane,
        )

        airplane = self._make_airplane([])
        # Neither call raises.
        validate_deflections_against_airplane(airplane, None)
        validate_deflections_against_airplane(airplane, {})


class TestStreamlineServiceUsesResolvedOp:
    """The three streamline / strip-forces services must resolve the OP before the VLM/AVL run."""

    @staticmethod
    def _resolved_op():
        return OperatingPointSchema(
            operating_point_id=42,
            alpha=4.2,
            beta=0.5,
            velocity=20.0,
            altitude=100.0,
            xyz_ref=[0.183, 0.0, 0.0],
            control_deflections={"elevator": -2.5, "aileron": 0.0},
        )

    def test_streamlines_service_calls_resolver_then_analyse(self):
        import asyncio
        from contextlib import ExitStack
        from unittest.mock import patch

        from app.services import analysis_service

        resolved = self._resolved_op()
        op = _make_op()

        with ExitStack() as stack:
            stack.enter_context(patch.object(
                analysis_service, "get_aeroplane_or_raise",
                return_value=MagicMock(id=7),
            ))
            stack.enter_context(patch.object(
                analysis_service, "get_aeroplane_schema_or_raise",
                return_value=MagicMock(),
            ))
            stack.enter_context(patch.object(
                analysis_service, "aeroplane_schema_to_asb_airplane_async",
                return_value=MagicMock(),
            ))
            mock_resolver = stack.enter_context(patch.object(
                analysis_service.operating_point_resolver,
                "resolve_operating_point",
                return_value=resolved,
            ))
            stack.enter_context(patch.object(
                analysis_service, "validate_deflections_against_airplane",
            ))
            mock_analyse = stack.enter_context(patch.object(
                analysis_service, "analyse_aerodynamics",
            ))
            fake_fig = MagicMock()
            fake_fig.to_json.return_value = '{"data":[],"layout":{}}'
            mock_analyse.return_value = (MagicMock(), fake_fig)

            asyncio.run(
                analysis_service.calculate_streamlines_json(
                    _db_returning(op),
                    aeroplane_uuid="0" * 36,
                    operating_point=OperatingPointSchema(operating_point_id=42),
                )
            )

            mock_resolver.assert_called_once()
            # The aircraft pk is forwarded so OP lookup is scoped (gh-577 review).
            assert mock_resolver.call_args.kwargs["aircraft_pk"] == 7
            call_op = mock_analyse.call_args.args[1]
            assert call_op.alpha == pytest.approx(4.2)
            assert call_op.control_deflections == {"elevator": -2.5, "aileron": 0.0}
            assert call_op.xyz_ref == [0.183, 0.0, 0.0]

    def test_three_view_image_service_calls_resolver(self):
        import asyncio
        from contextlib import ExitStack
        from unittest.mock import patch

        from app.services import analysis_service

        resolved = self._resolved_op()
        op = _make_op()

        with ExitStack() as stack:
            stack.enter_context(patch.object(
                analysis_service, "get_aeroplane_or_raise",
                return_value=MagicMock(id=7),
            ))
            stack.enter_context(patch.object(
                analysis_service, "get_aeroplane_schema_or_raise",
                return_value=MagicMock(),
            ))
            stack.enter_context(patch.object(
                analysis_service, "aeroplane_schema_to_asb_airplane_async",
                return_value=MagicMock(),
            ))
            mock_resolver = stack.enter_context(patch.object(
                analysis_service.operating_point_resolver,
                "resolve_operating_point",
                return_value=resolved,
            ))
            stack.enter_context(patch.object(
                analysis_service, "validate_deflections_against_airplane",
            ))
            mock_analyse = stack.enter_context(patch.object(
                analysis_service, "analyse_aerodynamics",
            ))
            mock_four_view = stack.enter_context(patch.object(
                analysis_service, "compile_four_view_figure",
            ))
            mock_analyse.return_value = (MagicMock(), MagicMock())
            mock_four_view.return_value.to_image.return_value = b"png-bytes"

            asyncio.run(
                analysis_service.get_streamlines_three_view_image(
                    _db_returning(op),
                    aeroplane_uuid="0" * 36,
                    operating_point=OperatingPointSchema(operating_point_id=42),
                )
            )

            mock_resolver.assert_called_once()
            assert mock_resolver.call_args.kwargs["aircraft_pk"] == 7
            call_op = mock_analyse.call_args.args[1]
            assert call_op.alpha == pytest.approx(4.2)

    def test_strip_forces_service_calls_resolver(self):
        import asyncio
        from contextlib import ExitStack
        from unittest.mock import patch

        from app.services import analysis_service

        resolved = self._resolved_op()
        op = _make_op()

        with ExitStack() as stack:
            # gh-592: aircraft.name now feeds the StripForcesResponse wing_name
            # echo, so the mock must expose a real string. Note: passing
            # ``name="..."`` to MagicMock() sets the mock's repr name, not the
            # ``.name`` attribute — we have to assign it after construction.
            aircraft_mock = MagicMock(id=7)
            aircraft_mock.name = "test_plane"
            stack.enter_context(patch.object(
                analysis_service, "get_aeroplane_or_raise",
                return_value=aircraft_mock,
            ))
            stack.enter_context(patch.object(
                analysis_service, "get_aeroplane_schema_or_raise",
                return_value=MagicMock(),
            ))
            stack.enter_context(patch.object(
                analysis_service, "aeroplane_schema_to_asb_airplane_async",
                return_value=MagicMock(),
            ))
            mock_resolver = stack.enter_context(patch.object(
                analysis_service.operating_point_resolver,
                "resolve_operating_point",
                return_value=resolved,
            ))
            mock_runner_cls = stack.enter_context(patch(
                "app.services.avl_runner.AVLRunner",
            ))
            stack.enter_context(patch(
                "app.services.avl_geometry_service.get_user_avl_content",
                return_value="MOCK_AVL_CONTENT",
            ))
            mock_runner = MagicMock()
            mock_runner.run.return_value = {
                "strip_forces": [], "alpha": 4.2, "beta": 0.5,
                "mach": 0, "Sref": 1.0, "Cref": 1.0, "Bref": 1.0,
            }
            mock_runner_cls.return_value = mock_runner

            asyncio.run(
                analysis_service.analyze_airplane_strip_forces(
                    _db_returning(op),
                    aeroplane_uuid="0" * 36,
                    operating_point=OperatingPointSchema(operating_point_id=42),
                )
            )

            mock_resolver.assert_called_once()
            assert mock_resolver.call_args.kwargs["aircraft_pk"] == 7

    def test_service_propagates_validation_error_unmapped(self):
        """gh-577 review: ServiceException must NOT be re-wrapped as InternalError (500)."""
        import asyncio
        from contextlib import ExitStack
        from unittest.mock import patch

        from app.core.exceptions import ValidationDomainError
        from app.services import analysis_service

        resolved = OperatingPointSchema(
            operating_point_id=42, alpha=4.2, velocity=20.0, altitude=100.0,
            xyz_ref=[0.1, 0, 0], control_deflections={"ghost": 0.0},
        )
        op = _make_op()

        with ExitStack() as stack:
            stack.enter_context(patch.object(
                analysis_service, "get_aeroplane_or_raise",
                return_value=MagicMock(id=7),
            ))
            stack.enter_context(patch.object(
                analysis_service, "get_aeroplane_schema_or_raise",
                return_value=MagicMock(),
            ))
            stack.enter_context(patch.object(
                analysis_service, "aeroplane_schema_to_asb_airplane_async",
                return_value=MagicMock(),
            ))
            stack.enter_context(patch.object(
                analysis_service.operating_point_resolver,
                "resolve_operating_point",
                return_value=resolved,
            ))
            stack.enter_context(patch.object(
                analysis_service, "validate_deflections_against_airplane",
                side_effect=ValidationDomainError(message="ghost surface"),
            ))
            with pytest.raises(ValidationDomainError):
                asyncio.run(
                    analysis_service.calculate_streamlines_json(
                        _db_returning(op),
                        aeroplane_uuid="0" * 36,
                        operating_point=OperatingPointSchema(operating_point_id=42),
                    )
                )

    def _patch_service_pipeline(self, analysis_service, resolved):
        """Common ExitStack patches; returns the stack (caller manages enter/exit)."""
        from contextlib import ExitStack
        from unittest.mock import patch

        stack = ExitStack()
        stack.enter_context(patch.object(
            analysis_service, "get_aeroplane_or_raise",
            return_value=MagicMock(id=7),
        ))
        stack.enter_context(patch.object(
            analysis_service, "get_aeroplane_schema_or_raise",
            return_value=MagicMock(),
        ))
        stack.enter_context(patch.object(
            analysis_service, "aeroplane_schema_to_asb_airplane_async",
            return_value=MagicMock(),
        ))
        stack.enter_context(patch.object(
            analysis_service.operating_point_resolver,
            "resolve_operating_point",
            return_value=resolved,
        ))
        stack.enter_context(patch.object(
            analysis_service, "validate_deflections_against_airplane",
        ))
        return stack

    def test_streamlines_service_wraps_generic_error_as_internal(self):
        """gh-577 review: non-ServiceException errors get logger.exception + InternalError."""
        import asyncio
        from unittest.mock import patch

        from app.core.exceptions import InternalError
        from app.services import analysis_service

        resolved = self._resolved_op()

        with self._patch_service_pipeline(analysis_service, resolved) as stack:
            stack.enter_context(patch.object(
                analysis_service, "analyse_aerodynamics",
                side_effect=RuntimeError("VLM crashed"),
            ))
            with pytest.raises(InternalError):
                asyncio.run(
                    analysis_service.calculate_streamlines_json(
                        _db_returning(_make_op()),
                        aeroplane_uuid="0" * 36,
                        operating_point=OperatingPointSchema(operating_point_id=42),
                    )
                )

    def test_three_view_service_wraps_generic_error_as_internal(self):
        import asyncio
        from unittest.mock import patch

        from app.core.exceptions import InternalError
        from app.services import analysis_service

        resolved = self._resolved_op()

        with self._patch_service_pipeline(analysis_service, resolved) as stack:
            stack.enter_context(patch.object(
                analysis_service, "analyse_aerodynamics",
                side_effect=RuntimeError("VLM crashed"),
            ))
            stack.enter_context(patch.object(
                analysis_service, "compile_four_view_figure",
            ))
            with pytest.raises(InternalError):
                asyncio.run(
                    analysis_service.get_streamlines_three_view_image(
                        _db_returning(_make_op()),
                        aeroplane_uuid="0" * 36,
                        operating_point=OperatingPointSchema(operating_point_id=42),
                    )
                )

    def test_strip_forces_service_wraps_generic_error_as_internal(self):
        import asyncio
        from unittest.mock import patch

        from app.core.exceptions import InternalError
        from app.services import analysis_service

        resolved = self._resolved_op()

        with self._patch_service_pipeline(analysis_service, resolved) as stack:
            mock_runner_cls = stack.enter_context(patch(
                "app.services.avl_runner.AVLRunner",
            ))
            stack.enter_context(patch(
                "app.services.avl_geometry_service.get_user_avl_content",
                return_value="MOCK_AVL_CONTENT",
            ))
            mock_runner_cls.return_value.run.side_effect = RuntimeError("AVL crashed")

            with pytest.raises(InternalError):
                asyncio.run(
                    analysis_service.analyze_airplane_strip_forces(
                        _db_returning(_make_op()),
                        aeroplane_uuid="0" * 36,
                        operating_point=OperatingPointSchema(operating_point_id=42),
                    )
                )

    def test_streamlines_service_skips_resolver_when_no_id(self):
        """Diagnostic / manual mode — inline schema passes through untouched."""
        import asyncio
        from contextlib import ExitStack
        from unittest.mock import patch

        from app.services import analysis_service

        inline = OperatingPointSchema(
            alpha=5.0, velocity=14.0, altitude=100.0, xyz_ref=[0.18, 0, 0],
        )

        with ExitStack() as stack:
            stack.enter_context(patch.object(
                analysis_service, "get_aeroplane_or_raise",
                return_value=MagicMock(id=7),
            ))
            stack.enter_context(patch.object(
                analysis_service, "get_aeroplane_schema_or_raise",
                return_value=MagicMock(),
            ))
            stack.enter_context(patch.object(
                analysis_service, "aeroplane_schema_to_asb_airplane_async",
                return_value=MagicMock(),
            ))
            stack.enter_context(patch.object(
                analysis_service, "validate_deflections_against_airplane",
            ))
            mock_analyse = stack.enter_context(patch.object(
                analysis_service, "analyse_aerodynamics",
            ))
            fake_fig = MagicMock()
            fake_fig.to_json.return_value = '{"data":[],"layout":{}}'
            mock_analyse.return_value = (MagicMock(), fake_fig)

            asyncio.run(
                analysis_service.calculate_streamlines_json(
                    _db_returning(None),  # OP lookup never reached
                    aeroplane_uuid="0" * 36,
                    operating_point=inline,
                )
            )

            # The schema reaching analyse_aerodynamics is the inline one,
            # not a resolved record — operating_point_id stays None.
            call_op = mock_analyse.call_args.args[1]
            assert call_op.operating_point_id is None
            assert call_op.alpha == 5.0
