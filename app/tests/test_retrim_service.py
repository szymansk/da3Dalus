"""Tests for app/services/retrim_service.py — background auto-retrim of dirty OPs."""

from __future__ import annotations

import asyncio
import math
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.background_jobs import RetrimJob
from app.models.aeroplanemodel import AeroplaneModel
from app.models.analysismodels import OperatingPointModel
from app.tests.conftest import make_aeroplane, make_operating_point


def _run(coro):
    return asyncio.run(coro)


class TestFindPitchControlName:
    """Test _find_pitch_control_name helper."""

    def test_finds_elevator(self, client_and_db):
        _, SessionLocal = client_and_db
        db = SessionLocal()
        aeroplane = make_aeroplane(db, name="pitch-test")
        from app.models.aeroplanemodel import (
            WingModel,
            WingXSecModel,
            WingXSecDetailModel,
            WingXSecTrailingEdgeDeviceModel,
        )

        wing = WingModel(name="h-stab", aeroplane_id=aeroplane.id, symmetric=True)
        db.add(wing)
        db.flush()
        xsec = WingXSecModel(
            wing_id=wing.id,
            xyz_le=[0, 0, 0],
            chord=0.2,
            twist=0,
            airfoil="naca0012",
            sort_index=0,
        )
        db.add(xsec)
        db.flush()
        detail = WingXSecDetailModel(wing_xsec_id=xsec.id)
        db.add(detail)
        db.flush()
        ted = WingXSecTrailingEdgeDeviceModel(
            wing_xsec_detail_id=detail.id,
            name="elevator",
            role="elevator",
        )
        db.add(ted)
        db.commit()

        from app.services.retrim_service import _find_pitch_control_name

        result = _find_pitch_control_name(db, aeroplane.id)
        assert result == "elevator"
        db.close()

    def test_finds_elevon(self, client_and_db):
        _, SessionLocal = client_and_db
        db = SessionLocal()
        aeroplane = make_aeroplane(db, name="elevon-test")
        from app.models.aeroplanemodel import (
            WingModel,
            WingXSecModel,
            WingXSecDetailModel,
            WingXSecTrailingEdgeDeviceModel,
        )

        wing = WingModel(name="wing", aeroplane_id=aeroplane.id, symmetric=True)
        db.add(wing)
        db.flush()
        xsec = WingXSecModel(
            wing_id=wing.id,
            xyz_le=[0, 0, 0],
            chord=0.3,
            twist=0,
            airfoil="naca0012",
            sort_index=0,
        )
        db.add(xsec)
        db.flush()
        detail = WingXSecDetailModel(wing_xsec_id=xsec.id)
        db.add(detail)
        db.flush()
        ted = WingXSecTrailingEdgeDeviceModel(
            wing_xsec_detail_id=detail.id,
            name="elevon",
            role="elevon",
        )
        db.add(ted)
        db.commit()

        from app.services.retrim_service import _find_pitch_control_name

        assert _find_pitch_control_name(db, aeroplane.id) == "elevon"
        db.close()

    def test_returns_none_when_no_teds(self, client_and_db):
        _, SessionLocal = client_and_db
        db = SessionLocal()
        aeroplane = make_aeroplane(db, name="no-teds")

        from app.services.retrim_service import _find_pitch_control_name

        assert _find_pitch_control_name(db, aeroplane.id) is None
        db.close()

    def test_returns_none_for_aileron_only(self, client_and_db):
        _, SessionLocal = client_and_db
        db = SessionLocal()
        aeroplane = make_aeroplane(db, name="aileron-only")
        from app.models.aeroplanemodel import (
            WingModel,
            WingXSecModel,
            WingXSecDetailModel,
            WingXSecTrailingEdgeDeviceModel,
        )

        wing = WingModel(name="wing", aeroplane_id=aeroplane.id, symmetric=True)
        db.add(wing)
        db.flush()
        xsec = WingXSecModel(
            wing_id=wing.id,
            xyz_le=[0, 0, 0],
            chord=0.3,
            twist=0,
            airfoil="naca0012",
            sort_index=0,
        )
        db.add(xsec)
        db.flush()
        detail = WingXSecDetailModel(wing_xsec_id=xsec.id)
        db.add(detail)
        db.flush()
        ted = WingXSecTrailingEdgeDeviceModel(
            wing_xsec_detail_id=detail.id,
            name="aileron",
            role="aileron",
        )
        db.add(ted)
        db.commit()

        from app.services.retrim_service import _find_pitch_control_name

        assert _find_pitch_control_name(db, aeroplane.id) is None
        db.close()


class TestRetrimDirtyOps:
    """Test the main retrim_dirty_ops function."""

    def test_noop_when_no_dirty_ops(self, client_and_db):
        _, SessionLocal = client_and_db
        db = SessionLocal()
        aeroplane = make_aeroplane(db, name="no-dirty")
        make_operating_point(db, aircraft_id=aeroplane.id, name="cruise", status="TRIMMED")
        db.close()

        with patch("app.services.retrim_service.SessionLocal", SessionLocal):
            from app.services.retrim_service import retrim_dirty_ops

            _run(retrim_dirty_ops(aeroplane.id))

        db2 = SessionLocal()
        op = db2.query(OperatingPointModel).filter_by(aircraft_id=aeroplane.id).first()
        assert op.status == "TRIMMED"
        db2.close()

    def test_trims_dirty_ops_to_trimmed(self, client_and_db):
        _, SessionLocal = client_and_db
        db = SessionLocal()
        aeroplane = make_aeroplane(db, name="trim-test")

        from app.models.aeroplanemodel import (
            WingModel,
            WingXSecModel,
            WingXSecDetailModel,
            WingXSecTrailingEdgeDeviceModel,
        )

        wing = WingModel(name="h-stab", aeroplane_id=aeroplane.id, symmetric=True)
        db.add(wing)
        db.flush()
        xsec = WingXSecModel(
            wing_id=wing.id,
            xyz_le=[0, 0, 0],
            chord=0.2,
            twist=0,
            airfoil="naca0012",
            sort_index=0,
        )
        db.add(xsec)
        db.flush()
        detail = WingXSecDetailModel(wing_xsec_id=xsec.id)
        db.add(detail)
        db.flush()
        ted = WingXSecTrailingEdgeDeviceModel(
            wing_xsec_detail_id=detail.id,
            name="elevator",
            role="elevator",
        )
        db.add(ted)
        db.commit()

        make_operating_point(db, aircraft_id=aeroplane.id, name="cruise", status="DIRTY")
        make_operating_point(db, aircraft_id=aeroplane.id, name="stall", status="DIRTY")
        db.close()

        mock_trim_result = MagicMock()
        mock_trim_result.converged = True
        mock_trim_result.trimmed_deflection = -3.5
        mock_trim_result.aero_coefficients = {"CL": 0.5, "CD": 0.03, "Cm": 0.0}
        mock_trim_result.stability_derivatives = {"Cm_a": -1.2}

        with (
            patch("app.services.retrim_service.SessionLocal", SessionLocal),
            patch(
                "app.services.retrim_service.trim_with_aerobuildup",
                new_callable=AsyncMock,
                return_value=mock_trim_result,
            ) as mock_trim,
            patch(
                "app.services.retrim_service.get_stability_summary",
                new_callable=AsyncMock,
            ),
        ):
            from app.services.retrim_service import retrim_dirty_ops

            _run(retrim_dirty_ops(aeroplane.id))

        assert mock_trim.call_count == 2

        db2 = SessionLocal()
        ops = db2.query(OperatingPointModel).filter_by(aircraft_id=aeroplane.id).all()
        assert all(op.status == "TRIMMED" for op in ops)
        db2.close()

    def test_individual_failure_does_not_block_others(self, client_and_db):
        _, SessionLocal = client_and_db
        db = SessionLocal()
        aeroplane = make_aeroplane(db, name="partial-fail")

        from app.models.aeroplanemodel import (
            WingModel,
            WingXSecModel,
            WingXSecDetailModel,
            WingXSecTrailingEdgeDeviceModel,
        )

        wing = WingModel(name="h-stab", aeroplane_id=aeroplane.id, symmetric=True)
        db.add(wing)
        db.flush()
        xsec = WingXSecModel(
            wing_id=wing.id,
            xyz_le=[0, 0, 0],
            chord=0.2,
            twist=0,
            airfoil="naca0012",
            sort_index=0,
        )
        db.add(xsec)
        db.flush()
        detail = WingXSecDetailModel(wing_xsec_id=xsec.id)
        db.add(detail)
        db.flush()
        ted = WingXSecTrailingEdgeDeviceModel(
            wing_xsec_detail_id=detail.id,
            name="elevator",
            role="elevator",
        )
        db.add(ted)
        db.commit()

        make_operating_point(db, aircraft_id=aeroplane.id, name="op_fail", status="DIRTY")
        make_operating_point(db, aircraft_id=aeroplane.id, name="op_ok", status="DIRTY")
        db.close()

        call_count = 0
        success_result = MagicMock()
        success_result.converged = True
        success_result.trimmed_deflection = -2.0
        success_result.aero_coefficients = {"CL": 0.4}
        success_result.stability_derivatives = {}

        async def _trim_side_effect(db, uuid, request):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("Simulated solver crash")
            return success_result

        with (
            patch("app.services.retrim_service.SessionLocal", SessionLocal),
            patch(
                "app.services.retrim_service.trim_with_aerobuildup",
                side_effect=_trim_side_effect,
            ),
            patch(
                "app.services.retrim_service.get_stability_summary",
                new_callable=AsyncMock,
            ),
        ):
            from app.services.retrim_service import retrim_dirty_ops

            _run(retrim_dirty_ops(aeroplane.id))

        db2 = SessionLocal()
        ops = (
            db2.query(OperatingPointModel)
            .filter_by(aircraft_id=aeroplane.id)
            .order_by(OperatingPointModel.id)
            .all()
        )
        assert ops[0].status == "NOT_TRIMMED"
        assert ops[1].status == "TRIMMED"
        db2.close()

    def test_not_converged_sets_limit_reached(self, client_and_db):
        _, SessionLocal = client_and_db
        db = SessionLocal()
        aeroplane = make_aeroplane(db, name="limit-test")

        from app.models.aeroplanemodel import (
            WingModel,
            WingXSecModel,
            WingXSecDetailModel,
            WingXSecTrailingEdgeDeviceModel,
        )

        wing = WingModel(name="h-stab", aeroplane_id=aeroplane.id, symmetric=True)
        db.add(wing)
        db.flush()
        xsec = WingXSecModel(
            wing_id=wing.id,
            xyz_le=[0, 0, 0],
            chord=0.2,
            twist=0,
            airfoil="naca0012",
            sort_index=0,
        )
        db.add(xsec)
        db.flush()
        detail = WingXSecDetailModel(wing_xsec_id=xsec.id)
        db.add(detail)
        db.flush()
        ted = WingXSecTrailingEdgeDeviceModel(
            wing_xsec_detail_id=detail.id,
            name="elevator",
            role="elevator",
        )
        db.add(ted)
        db.commit()

        make_operating_point(db, aircraft_id=aeroplane.id, name="cruise", status="DIRTY")
        db.close()

        not_converged = MagicMock()
        not_converged.converged = False

        with (
            patch("app.services.retrim_service.SessionLocal", SessionLocal),
            patch(
                "app.services.retrim_service.trim_with_aerobuildup",
                new_callable=AsyncMock,
                return_value=not_converged,
            ),
            patch(
                "app.services.retrim_service.get_stability_summary",
                new_callable=AsyncMock,
            ) as mock_stability,
        ):
            from app.services.retrim_service import retrim_dirty_ops

            _run(retrim_dirty_ops(aeroplane.id))

        db2 = SessionLocal()
        op = db2.query(OperatingPointModel).filter_by(aircraft_id=aeroplane.id).first()
        assert op.status == "LIMIT_REACHED"
        mock_stability.assert_not_called()
        db2.close()

    def test_no_pitch_control_leaves_ops_dirty(self, client_and_db):
        _, SessionLocal = client_and_db
        db = SessionLocal()
        aeroplane = make_aeroplane(db, name="no-elevator")
        make_operating_point(db, aircraft_id=aeroplane.id, name="cruise", status="DIRTY")
        db.close()

        with patch("app.services.retrim_service.SessionLocal", SessionLocal):
            from app.services.retrim_service import retrim_dirty_ops

            _run(retrim_dirty_ops(aeroplane.id))

        db2 = SessionLocal()
        op = db2.query(OperatingPointModel).filter_by(aircraft_id=aeroplane.id).first()
        assert op.status == "DIRTY"
        db2.close()

    def test_recomputes_stability_after_trim(self, client_and_db):
        _, SessionLocal = client_and_db
        db = SessionLocal()
        aeroplane = make_aeroplane(db, name="stability-test")

        from app.models.aeroplanemodel import (
            WingModel,
            WingXSecModel,
            WingXSecDetailModel,
            WingXSecTrailingEdgeDeviceModel,
        )

        wing = WingModel(name="h-stab", aeroplane_id=aeroplane.id, symmetric=True)
        db.add(wing)
        db.flush()
        xsec = WingXSecModel(
            wing_id=wing.id,
            xyz_le=[0, 0, 0],
            chord=0.2,
            twist=0,
            airfoil="naca0012",
            sort_index=0,
        )
        db.add(xsec)
        db.flush()
        detail = WingXSecDetailModel(wing_xsec_id=xsec.id)
        db.add(detail)
        db.flush()
        ted = WingXSecTrailingEdgeDeviceModel(
            wing_xsec_detail_id=detail.id,
            name="elevator",
            role="elevator",
        )
        db.add(ted)
        db.commit()

        make_operating_point(db, aircraft_id=aeroplane.id, name="cruise", status="DIRTY")
        db.close()

        mock_trim_result = MagicMock()
        mock_trim_result.converged = True
        mock_trim_result.trimmed_deflection = -3.0
        mock_trim_result.aero_coefficients = {"CL": 0.5}
        mock_trim_result.stability_derivatives = {}

        with (
            patch("app.services.retrim_service.SessionLocal", SessionLocal),
            patch(
                "app.services.retrim_service.trim_with_aerobuildup",
                new_callable=AsyncMock,
                return_value=mock_trim_result,
            ),
            patch(
                "app.services.retrim_service.get_stability_summary",
                new_callable=AsyncMock,
            ) as mock_stability,
        ):
            from app.services.retrim_service import retrim_dirty_ops

            _run(retrim_dirty_ops(aeroplane.id))

        mock_stability.assert_called_once()

    def test_aeroplane_deleted_before_retrim(self, client_and_db):
        """Finding 9: aeroplane deleted between schedule and execution."""
        _, SessionLocal = client_and_db
        db = SessionLocal()
        aeroplane = make_aeroplane(db, name="deleted")
        aeroplane_id = aeroplane.id
        make_operating_point(db, aircraft_id=aeroplane_id, name="cruise", status="DIRTY")
        db.query(OperatingPointModel).filter_by(aircraft_id=aeroplane_id).delete()
        db.query(AeroplaneModel).filter_by(id=aeroplane_id).delete()
        db.commit()
        db.close()

        with patch("app.services.retrim_service.SessionLocal", SessionLocal):
            from app.services.retrim_service import retrim_dirty_ops

            _run(retrim_dirty_ops(aeroplane_id))

    def test_control_deflections_merge_preserves_existing(self, client_and_db):
        """Finding 10: existing deflections must survive the merge."""
        _, SessionLocal = client_and_db
        db = SessionLocal()
        aeroplane = make_aeroplane(db, name="merge-test")

        from app.models.aeroplanemodel import (
            WingModel,
            WingXSecModel,
            WingXSecDetailModel,
            WingXSecTrailingEdgeDeviceModel,
        )

        wing = WingModel(name="h-stab", aeroplane_id=aeroplane.id, symmetric=True)
        db.add(wing)
        db.flush()
        xsec = WingXSecModel(
            wing_id=wing.id,
            xyz_le=[0, 0, 0],
            chord=0.2,
            twist=0,
            airfoil="naca0012",
            sort_index=0,
        )
        db.add(xsec)
        db.flush()
        detail = WingXSecDetailModel(wing_xsec_id=xsec.id)
        db.add(detail)
        db.flush()
        ted = WingXSecTrailingEdgeDeviceModel(
            wing_xsec_detail_id=detail.id,
            name="elevator",
            role="elevator",
        )
        db.add(ted)
        db.commit()

        make_operating_point(
            db,
            aircraft_id=aeroplane.id,
            name="cruise",
            status="DIRTY",
            control_deflections={"aileron": 5.0},
        )
        db.close()

        mock_trim_result = MagicMock()
        mock_trim_result.converged = True
        mock_trim_result.trimmed_deflection = -3.0
        mock_trim_result.aero_coefficients = {}
        mock_trim_result.stability_derivatives = {}

        with (
            patch("app.services.retrim_service.SessionLocal", SessionLocal),
            patch(
                "app.services.retrim_service.trim_with_aerobuildup",
                new_callable=AsyncMock,
                return_value=mock_trim_result,
            ),
            patch(
                "app.services.retrim_service.get_stability_summary",
                new_callable=AsyncMock,
            ),
        ):
            from app.services.retrim_service import retrim_dirty_ops

            _run(retrim_dirty_ops(aeroplane.id))

        db2 = SessionLocal()
        op = db2.query(OperatingPointModel).filter_by(aircraft_id=aeroplane.id).first()
        assert op.control_deflections["aileron"] == 5.0
        assert op.control_deflections["elevator"] == -3.0
        db2.close()

    def test_stability_failure_does_not_rollback_trims(self, client_and_db):
        """Finding 12: OPs remain TRIMMED even if stability recomputation fails."""
        _, SessionLocal = client_and_db
        db = SessionLocal()
        aeroplane = make_aeroplane(db, name="stab-fail")

        from app.models.aeroplanemodel import (
            WingModel,
            WingXSecModel,
            WingXSecDetailModel,
            WingXSecTrailingEdgeDeviceModel,
        )

        wing = WingModel(name="h-stab", aeroplane_id=aeroplane.id, symmetric=True)
        db.add(wing)
        db.flush()
        xsec = WingXSecModel(
            wing_id=wing.id,
            xyz_le=[0, 0, 0],
            chord=0.2,
            twist=0,
            airfoil="naca0012",
            sort_index=0,
        )
        db.add(xsec)
        db.flush()
        detail = WingXSecDetailModel(wing_xsec_id=xsec.id)
        db.add(detail)
        db.flush()
        ted = WingXSecTrailingEdgeDeviceModel(
            wing_xsec_detail_id=detail.id,
            name="elevator",
            role="elevator",
        )
        db.add(ted)
        db.commit()

        make_operating_point(db, aircraft_id=aeroplane.id, name="cruise", status="DIRTY")
        db.close()

        mock_trim_result = MagicMock()
        mock_trim_result.converged = True
        mock_trim_result.trimmed_deflection = -2.0
        mock_trim_result.aero_coefficients = {}
        mock_trim_result.stability_derivatives = {}

        with (
            patch("app.services.retrim_service.SessionLocal", SessionLocal),
            patch(
                "app.services.retrim_service.trim_with_aerobuildup",
                new_callable=AsyncMock,
                return_value=mock_trim_result,
            ),
            patch(
                "app.services.retrim_service.get_stability_summary",
                new_callable=AsyncMock,
                side_effect=RuntimeError("Stability computation exploded"),
            ),
        ):
            from app.services.retrim_service import retrim_dirty_ops

            _run(retrim_dirty_ops(aeroplane.id))

        db2 = SessionLocal()
        op = db2.query(OperatingPointModel).filter_by(aircraft_id=aeroplane.id).first()
        assert op.status == "TRIMMED"
        db2.close()


class TestOpModelToSchemaRadDegConversion:
    """gh-587 regression: retrim path must convert alpha/beta from rad→deg.

    Before gh-587 the retrim seeded the solver with alpha in radians (≈ 0 °
    for small angles), discarding the converged trim. These tests pin the fix.
    """

    def _make_op_mock(self, **overrides) -> MagicMock:
        from app.models.analysismodels import OperatingPointModel
        from app.schemas.aeroanalysisschema import OperatingPointStatus

        defaults = dict(
            id=7,
            name="cruise",
            description="",
            aircraft_id=1,
            status=OperatingPointStatus.TRIMMED,
            warnings=[],
            controls={"elevator": -2.5},
            velocity=20.0,
            alpha=math.pi / 4,  # 45° stored as radians
            beta=math.radians(3.0),
            p=0.0,
            q=0.0,
            r=0.0,
            xyz_ref=[0.18, 0.0, 0.0],
            altitude=100.0,
            control_deflections=None,
            trim_enrichment=None,
        )
        defaults.update(overrides)
        op = MagicMock(spec=OperatingPointModel)
        for k, v in defaults.items():
            setattr(op, k, v)
        return op

    def test_retrim_schema_alpha_is_degrees_not_radians(self):
        """Alpha stored as π/4 rad must arrive as 45° on the schema."""
        from app.services.operating_point_resolver import operating_point_model_to_schema

        op = self._make_op_mock(alpha=math.pi / 4)
        schema = operating_point_model_to_schema(op)
        assert schema.alpha == pytest.approx(45.0, rel=1e-6)

    def test_retrim_schema_beta_is_degrees_not_radians(self):
        """Beta stored as radians must be converted to degrees on the schema."""
        from app.services.operating_point_resolver import operating_point_model_to_schema

        op = self._make_op_mock(beta=math.radians(3.0))
        schema = operating_point_model_to_schema(op)
        assert schema.beta == pytest.approx(3.0, rel=1e-6)

    def test_retrim_service_calls_operating_point_model_to_schema(self, client_and_db):
        """retrim_dirty_ops must use operating_point_model_to_schema (not _op_model_to_schema)."""
        _, SessionLocal = client_and_db
        db = SessionLocal()
        aeroplane = make_aeroplane(db, name="rad-deg-test")

        from app.models.aeroplanemodel import (
            WingModel,
            WingXSecDetailModel,
            WingXSecModel,
            WingXSecTrailingEdgeDeviceModel,
        )

        wing = WingModel(name="h-stab", aeroplane_id=aeroplane.id, symmetric=True)
        db.add(wing)
        db.flush()
        xsec = WingXSecModel(
            wing_id=wing.id,
            xyz_le=[0, 0, 0],
            chord=0.2,
            twist=0,
            airfoil="naca0012",
            sort_index=0,
        )
        db.add(xsec)
        db.flush()
        detail = WingXSecDetailModel(wing_xsec_id=xsec.id)
        db.add(detail)
        db.flush()
        ted = WingXSecTrailingEdgeDeviceModel(
            wing_xsec_detail_id=detail.id,
            name="elevator",
            role="elevator",
        )
        db.add(ted)
        db.commit()

        # Store alpha as π/4 radians — after the fix, the schema must get 45°
        make_operating_point(
            db,
            aircraft_id=aeroplane.id,
            name="cruise",
            status="DIRTY",
            alpha=math.pi / 4,
        )
        db.close()

        captured_schemas: list = []

        async def _capture_trim(db, uuid, request):
            captured_schemas.append(request.operating_point)
            result = MagicMock()
            result.converged = True
            result.trimmed_deflection = -2.0
            return result

        with (
            patch("app.services.retrim_service.SessionLocal", SessionLocal),
            patch(
                "app.services.retrim_service.trim_with_aerobuildup",
                side_effect=_capture_trim,
            ),
            patch(
                "app.services.retrim_service.get_stability_summary",
                new_callable=AsyncMock,
            ),
        ):
            from app.services.retrim_service import retrim_dirty_ops

            asyncio.run(retrim_dirty_ops(aeroplane.id))

        assert len(captured_schemas) == 1, "Expected exactly one trim call"
        schema = captured_schemas[0]
        # The schema must carry 45°, not ≈0.785 (radians value)
        assert schema.alpha == pytest.approx(45.0, rel=1e-3), (
            f"alpha was {schema.alpha!r} — expected 45.0° (gh-587 regression)"
        )


class TestStartupRegistration:
    """Verify trim function is registered at app startup."""

    def test_job_tracker_has_trim_function_after_startup(self, client_and_db):
        from app.core.background_jobs import job_tracker

        assert job_tracker._trim_function is not None


class TestRetrimIntegration:
    """Integration: geometry change → OPs dirty → retrim → stability recomputed."""

    def test_geometry_change_triggers_full_retrim_pipeline(self, client_and_db):
        _, SessionLocal = client_and_db
        db = SessionLocal()
        aeroplane = make_aeroplane(db, name="integration-test")

        from app.models.aeroplanemodel import (
            WingModel,
            WingXSecModel,
            WingXSecDetailModel,
            WingXSecTrailingEdgeDeviceModel,
        )

        wing = WingModel(name="h-stab", aeroplane_id=aeroplane.id, symmetric=True)
        db.add(wing)
        db.flush()
        xsec = WingXSecModel(
            wing_id=wing.id,
            xyz_le=[0, 0, 0],
            chord=0.2,
            twist=0,
            airfoil="naca0012",
            sort_index=0,
        )
        db.add(xsec)
        db.flush()
        detail = WingXSecDetailModel(wing_xsec_id=xsec.id)
        db.add(detail)
        db.flush()
        ted = WingXSecTrailingEdgeDeviceModel(
            wing_xsec_detail_id=detail.id,
            name="elevator",
            role="elevator",
        )
        db.add(ted)
        db.commit()

        make_operating_point(
            db,
            aircraft_id=aeroplane.id,
            name="cruise",
            status="TRIMMED",
        )
        make_operating_point(
            db,
            aircraft_id=aeroplane.id,
            name="stall",
            status="TRIMMED",
        )
        db.close()

        from app.services.invalidation_service import mark_ops_dirty

        db2 = SessionLocal()
        count = mark_ops_dirty(db2, aeroplane.id)
        db2.commit()
        assert count == 2
        ops = db2.query(OperatingPointModel).filter_by(aircraft_id=aeroplane.id).all()
        assert all(op.status == "DIRTY" for op in ops)
        db2.close()

        mock_result = MagicMock()
        mock_result.converged = True
        mock_result.trimmed_deflection = -4.0
        mock_result.aero_coefficients = {"CL": 0.6, "CD": 0.04, "Cm": 0.0}
        mock_result.stability_derivatives = {"Cm_a": -1.1}

        with (
            patch("app.services.retrim_service.SessionLocal", SessionLocal),
            patch(
                "app.services.retrim_service.trim_with_aerobuildup",
                new_callable=AsyncMock,
                return_value=mock_result,
            ),
            patch(
                "app.services.retrim_service.get_stability_summary",
                new_callable=AsyncMock,
            ) as mock_stability,
        ):
            from app.services.retrim_service import retrim_dirty_ops

            _run(retrim_dirty_ops(aeroplane.id))

        db3 = SessionLocal()
        ops = db3.query(OperatingPointModel).filter_by(aircraft_id=aeroplane.id).all()
        assert all(op.status == "TRIMMED" for op in ops)
        for op in ops:
            assert op.control_deflections["elevator"] == -4.0
        db3.close()

        mock_stability.assert_called_once()


class TestRetrimDistinguishesCorruptRowsFromSolverFailures:
    """gh-623 — a data-integrity error must land in INVALID, not NOT_TRIMMED.

    Before the fix, ``retrim_dirty_ops`` caught everything with a broad
    ``except Exception`` and shoved both solver crashes and corrupt-row
    errors into ``NOT_TRIMMED``. The UI then offered "retry the trim" for
    both — useless for a corrupt row.
    """

    @staticmethod
    def _setup_aeroplane_with_elevator(db) -> AeroplaneModel:
        from app.models.aeroplanemodel import (
            WingModel,
            WingXSecDetailModel,
            WingXSecModel,
            WingXSecTrailingEdgeDeviceModel,
        )

        aeroplane = make_aeroplane(db, name=f"corrupt-row-{id(db)}")
        wing = WingModel(name="h-stab", aeroplane_id=aeroplane.id, symmetric=True)
        db.add(wing)
        db.flush()
        xsec = WingXSecModel(
            wing_id=wing.id,
            xyz_le=[0, 0, 0],
            chord=0.2,
            twist=0,
            airfoil="naca0012",
            sort_index=0,
        )
        db.add(xsec)
        db.flush()
        detail = WingXSecDetailModel(wing_xsec_id=xsec.id)
        db.add(detail)
        db.flush()
        db.add(
            WingXSecTrailingEdgeDeviceModel(
                wing_xsec_detail_id=detail.id,
                name="elevator",
                role="elevator",
            )
        )
        db.commit()
        return aeroplane

    def test_validation_domain_error_lands_in_invalid_not_not_trimmed(self, client_and_db):
        """A corrupt OP row (NOT-NULL column was NULL → ValidationDomainError
        bubbles out of ``operating_point_model_to_schema``) must be marked
        INVALID, with the reason persisted to ``warnings`` for diagnostics.
        """
        from app.core.exceptions import ValidationDomainError

        _, SessionLocal = client_and_db
        db = SessionLocal()
        aeroplane = self._setup_aeroplane_with_elevator(db)
        make_operating_point(db, aircraft_id=aeroplane.id, name="bad-row", status="DIRTY")
        db.close()

        with (
            patch("app.services.retrim_service.SessionLocal", SessionLocal),
            patch(
                "app.services.retrim_service.operating_point_model_to_schema",
                side_effect=ValidationDomainError(message="velocity is required"),
            ),
            patch(
                "app.services.retrim_service.trim_with_aerobuildup",
                new_callable=AsyncMock,
            ) as mock_trim,
        ):
            from app.services.retrim_service import retrim_dirty_ops

            _run(retrim_dirty_ops(aeroplane.id))

        # Solver should never have been called — the row is bad before we
        # get there.
        mock_trim.assert_not_called()

        db2 = SessionLocal()
        op = db2.query(OperatingPointModel).filter_by(aircraft_id=aeroplane.id).first()
        assert op.status == "INVALID", (
            f"Corrupt row must land in INVALID (was {op.status}). "
            f"NOT_TRIMMED is reserved for solver failures the user can retry."
        )
        # The reason must be persisted so the UI can show it actionably —
        # without it the user has no signal beyond a colour change.
        assert any("velocity is required" in w for w in (op.warnings or [])), (
            f"reason not persisted to warnings: {op.warnings!r}"
        )
        db2.close()

    def test_pydantic_validation_error_also_lands_in_invalid(self, client_and_db):
        """A raw pydantic ``ValidationError`` (e.g. the schema validator
        rejected the persisted model) must also be classified INVALID,
        not NOT_TRIMMED.
        """
        from pydantic import BaseModel, ValidationError, field_validator

        class _StrictModel(BaseModel):
            v: float

            @field_validator("v")
            @classmethod
            def _positive(cls, value: float) -> float:
                if value <= 0:
                    raise ValueError("v must be positive")
                return value

        try:
            _StrictModel(v=-1.0)
        except ValidationError as exc:
            raised_pydantic_error = exc
        else:  # pragma: no cover — pydantic guarantees this raises
            pytest.fail("expected pydantic ValidationError")

        _, SessionLocal = client_and_db
        db = SessionLocal()
        aeroplane = self._setup_aeroplane_with_elevator(db)
        make_operating_point(db, aircraft_id=aeroplane.id, name="pyd-bad", status="DIRTY")
        db.close()

        with (
            patch("app.services.retrim_service.SessionLocal", SessionLocal),
            patch(
                "app.services.retrim_service.operating_point_model_to_schema",
                side_effect=raised_pydantic_error,
            ),
            patch(
                "app.services.retrim_service.trim_with_aerobuildup",
                new_callable=AsyncMock,
            ),
        ):
            from app.services.retrim_service import retrim_dirty_ops

            _run(retrim_dirty_ops(aeroplane.id))

        db2 = SessionLocal()
        op = db2.query(OperatingPointModel).filter_by(aircraft_id=aeroplane.id).first()
        assert op.status == "INVALID"
        db2.close()

    def test_solver_runtime_error_still_lands_in_not_trimmed(self, client_and_db):
        """Regression: the existing solver-failure path is unchanged. A
        ``RuntimeError`` from the trim solver must still land in
        NOT_TRIMMED so the user knows "retry the trim" is the right
        action for this OP.
        """
        _, SessionLocal = client_and_db
        db = SessionLocal()
        aeroplane = self._setup_aeroplane_with_elevator(db)
        make_operating_point(db, aircraft_id=aeroplane.id, name="solver-fail", status="DIRTY")
        db.close()

        with (
            patch("app.services.retrim_service.SessionLocal", SessionLocal),
            patch(
                "app.services.retrim_service.trim_with_aerobuildup",
                new_callable=AsyncMock,
                side_effect=RuntimeError("solver did not converge after 200 iters"),
            ),
        ):
            from app.services.retrim_service import retrim_dirty_ops

            _run(retrim_dirty_ops(aeroplane.id))

        db2 = SessionLocal()
        op = db2.query(OperatingPointModel).filter_by(aircraft_id=aeroplane.id).first()
        assert op.status == "NOT_TRIMMED", (
            f"Solver RuntimeError must stay in NOT_TRIMMED (was {op.status})"
        )
        db2.close()

    def test_corrupt_row_does_not_abort_batch(self, client_and_db):
        """The existing isolation contract must hold: one corrupt OP must
        not prevent the next OP in the batch from being trimmed.
        """
        from app.core.exceptions import ValidationDomainError

        _, SessionLocal = client_and_db
        db = SessionLocal()
        aeroplane = self._setup_aeroplane_with_elevator(db)
        make_operating_point(db, aircraft_id=aeroplane.id, name="bad", status="DIRTY")
        make_operating_point(db, aircraft_id=aeroplane.id, name="good", status="DIRTY")
        db.close()

        call_count = {"n": 0}
        ok_result = MagicMock()
        ok_result.converged = True
        ok_result.trimmed_deflection = -2.0
        ok_result.aero_coefficients = {"CL": 0.4}
        ok_result.stability_derivatives = {}

        def _resolver_side_effect(op_model):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise ValidationDomainError(message="xyz_ref is empty")
            # Delegate to the real resolver for the good OP. Importing it
            # lazily keeps the patch surface small.
            from app.services.operating_point_resolver import (
                operating_point_model_to_schema as real_resolver,
            )

            return real_resolver(op_model)

        with (
            patch("app.services.retrim_service.SessionLocal", SessionLocal),
            patch(
                "app.services.retrim_service.operating_point_model_to_schema",
                side_effect=_resolver_side_effect,
            ),
            patch(
                "app.services.retrim_service.trim_with_aerobuildup",
                new_callable=AsyncMock,
                return_value=ok_result,
            ),
            patch(
                "app.services.retrim_service.get_stability_summary",
                new_callable=AsyncMock,
            ),
        ):
            from app.services.retrim_service import retrim_dirty_ops

            _run(retrim_dirty_ops(aeroplane.id))

        db2 = SessionLocal()
        ops = (
            db2.query(OperatingPointModel)
            .filter_by(aircraft_id=aeroplane.id)
            .order_by(OperatingPointModel.id)
            .all()
        )
        assert ops[0].status == "INVALID"
        assert ops[1].status == "TRIMMED", (
            f"good OP was {ops[1].status} — corrupt row aborted the batch"
        )
        db2.close()
