"""Tests for app/services/retrim_service.py — background auto-retrim of dirty OPs."""

from __future__ import annotations

import asyncio
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
            wing_id=wing.id, xyz_le=[0, 0, 0], chord=0.2, twist=0, airfoil="naca0012",
            sort_index=0,
        )
        db.add(xsec)
        db.flush()
        detail = WingXSecDetailModel(wing_xsec_id=xsec.id)
        db.add(detail)
        db.flush()
        ted = WingXSecTrailingEdgeDeviceModel(
            wing_xsec_detail_id=detail.id, name="elevator", role="elevator",
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
            WingModel, WingXSecModel, WingXSecDetailModel,
            WingXSecTrailingEdgeDeviceModel,
        )

        wing = WingModel(name="wing", aeroplane_id=aeroplane.id, symmetric=True)
        db.add(wing)
        db.flush()
        xsec = WingXSecModel(
            wing_id=wing.id, xyz_le=[0, 0, 0], chord=0.3, twist=0, airfoil="naca0012",
            sort_index=0,
        )
        db.add(xsec)
        db.flush()
        detail = WingXSecDetailModel(wing_xsec_id=xsec.id)
        db.add(detail)
        db.flush()
        ted = WingXSecTrailingEdgeDeviceModel(
            wing_xsec_detail_id=detail.id, name="elevon", role="elevon",
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
            WingModel, WingXSecModel, WingXSecDetailModel,
            WingXSecTrailingEdgeDeviceModel,
        )

        wing = WingModel(name="wing", aeroplane_id=aeroplane.id, symmetric=True)
        db.add(wing)
        db.flush()
        xsec = WingXSecModel(
            wing_id=wing.id, xyz_le=[0, 0, 0], chord=0.3, twist=0, airfoil="naca0012",
            sort_index=0,
        )
        db.add(xsec)
        db.flush()
        detail = WingXSecDetailModel(wing_xsec_id=xsec.id)
        db.add(detail)
        db.flush()
        ted = WingXSecTrailingEdgeDeviceModel(
            wing_xsec_detail_id=detail.id, name="aileron", role="aileron",
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
            WingModel, WingXSecModel, WingXSecDetailModel,
            WingXSecTrailingEdgeDeviceModel,
        )

        wing = WingModel(name="h-stab", aeroplane_id=aeroplane.id, symmetric=True)
        db.add(wing)
        db.flush()
        xsec = WingXSecModel(
            wing_id=wing.id, xyz_le=[0, 0, 0], chord=0.2, twist=0, airfoil="naca0012",
            sort_index=0,
        )
        db.add(xsec)
        db.flush()
        detail = WingXSecDetailModel(wing_xsec_id=xsec.id)
        db.add(detail)
        db.flush()
        ted = WingXSecTrailingEdgeDeviceModel(
            wing_xsec_detail_id=detail.id, name="elevator", role="elevator",
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
            WingModel, WingXSecModel, WingXSecDetailModel,
            WingXSecTrailingEdgeDeviceModel,
        )

        wing = WingModel(name="h-stab", aeroplane_id=aeroplane.id, symmetric=True)
        db.add(wing)
        db.flush()
        xsec = WingXSecModel(
            wing_id=wing.id, xyz_le=[0, 0, 0], chord=0.2, twist=0, airfoil="naca0012",
            sort_index=0,
        )
        db.add(xsec)
        db.flush()
        detail = WingXSecDetailModel(wing_xsec_id=xsec.id)
        db.add(detail)
        db.flush()
        ted = WingXSecTrailingEdgeDeviceModel(
            wing_xsec_detail_id=detail.id, name="elevator", role="elevator",
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
            WingModel, WingXSecModel, WingXSecDetailModel,
            WingXSecTrailingEdgeDeviceModel,
        )

        wing = WingModel(name="h-stab", aeroplane_id=aeroplane.id, symmetric=True)
        db.add(wing)
        db.flush()
        xsec = WingXSecModel(
            wing_id=wing.id, xyz_le=[0, 0, 0], chord=0.2, twist=0, airfoil="naca0012",
            sort_index=0,
        )
        db.add(xsec)
        db.flush()
        detail = WingXSecDetailModel(wing_xsec_id=xsec.id)
        db.add(detail)
        db.flush()
        ted = WingXSecTrailingEdgeDeviceModel(
            wing_xsec_detail_id=detail.id, name="elevator", role="elevator",
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
            WingModel, WingXSecModel, WingXSecDetailModel,
            WingXSecTrailingEdgeDeviceModel,
        )

        wing = WingModel(name="h-stab", aeroplane_id=aeroplane.id, symmetric=True)
        db.add(wing)
        db.flush()
        xsec = WingXSecModel(
            wing_id=wing.id, xyz_le=[0, 0, 0], chord=0.2, twist=0, airfoil="naca0012",
            sort_index=0,
        )
        db.add(xsec)
        db.flush()
        detail = WingXSecDetailModel(wing_xsec_id=xsec.id)
        db.add(detail)
        db.flush()
        ted = WingXSecTrailingEdgeDeviceModel(
            wing_xsec_detail_id=detail.id, name="elevator", role="elevator",
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
            WingModel, WingXSecModel, WingXSecDetailModel,
            WingXSecTrailingEdgeDeviceModel,
        )

        wing = WingModel(name="h-stab", aeroplane_id=aeroplane.id, symmetric=True)
        db.add(wing)
        db.flush()
        xsec = WingXSecModel(
            wing_id=wing.id, xyz_le=[0, 0, 0], chord=0.2, twist=0, airfoil="naca0012",
            sort_index=0,
        )
        db.add(xsec)
        db.flush()
        detail = WingXSecDetailModel(wing_xsec_id=xsec.id)
        db.add(detail)
        db.flush()
        ted = WingXSecTrailingEdgeDeviceModel(
            wing_xsec_detail_id=detail.id, name="elevator", role="elevator",
        )
        db.add(ted)
        db.commit()

        make_operating_point(
            db, aircraft_id=aeroplane.id, name="cruise", status="DIRTY",
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
            WingModel, WingXSecModel, WingXSecDetailModel,
            WingXSecTrailingEdgeDeviceModel,
        )

        wing = WingModel(name="h-stab", aeroplane_id=aeroplane.id, symmetric=True)
        db.add(wing)
        db.flush()
        xsec = WingXSecModel(
            wing_id=wing.id, xyz_le=[0, 0, 0], chord=0.2, twist=0, airfoil="naca0012",
            sort_index=0,
        )
        db.add(xsec)
        db.flush()
        detail = WingXSecDetailModel(wing_xsec_id=xsec.id)
        db.add(detail)
        db.flush()
        ted = WingXSecTrailingEdgeDeviceModel(
            wing_xsec_detail_id=detail.id, name="elevator", role="elevator",
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
            WingModel, WingXSecModel, WingXSecDetailModel,
            WingXSecTrailingEdgeDeviceModel,
        )

        wing = WingModel(name="h-stab", aeroplane_id=aeroplane.id, symmetric=True)
        db.add(wing)
        db.flush()
        xsec = WingXSecModel(
            wing_id=wing.id, xyz_le=[0, 0, 0], chord=0.2, twist=0, airfoil="naca0012",
            sort_index=0,
        )
        db.add(xsec)
        db.flush()
        detail = WingXSecDetailModel(wing_xsec_id=xsec.id)
        db.add(detail)
        db.flush()
        ted = WingXSecTrailingEdgeDeviceModel(
            wing_xsec_detail_id=detail.id, name="elevator", role="elevator",
        )
        db.add(ted)
        db.commit()

        make_operating_point(
            db, aircraft_id=aeroplane.id, name="cruise", status="TRIMMED",
        )
        make_operating_point(
            db, aircraft_id=aeroplane.id, name="stall", status="TRIMMED",
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
