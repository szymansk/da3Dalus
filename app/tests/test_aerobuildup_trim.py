"""Tests for AeroBuildup trim analysis — scipy root-finding.

Covers: AeroBuildupTrimRequest, AeroBuildupTrimResult schemas,
trim_with_aerobuildup service, and the aerobuildup-trim endpoint.
"""

from __future__ import annotations

import asyncio
import math
import uuid
from unittest.mock import MagicMock, patch

import pytest


# =========================================================================== #
# Schema validation — AeroBuildupTrimRequest
# =========================================================================== #


class TestAeroBuildupTrimRequest:
    """Verify AeroBuildupTrimRequest schema validation."""

    def test_valid_request_with_defaults(self):
        from app.schemas.aeroanalysisschema import (
            AeroBuildupTrimRequest,
            OperatingPointSchema,
        )

        req = AeroBuildupTrimRequest(
            operating_point=OperatingPointSchema(velocity=15.0, alpha=5.0),
        )
        assert req.trim_variable == "elevator"
        assert req.target_coefficient == "Cm"
        assert req.target_value == 0.0
        assert req.deflection_bounds == [-25.0, 25.0]

    def test_valid_request_custom_values(self):
        from app.schemas.aeroanalysisschema import (
            AeroBuildupTrimRequest,
            OperatingPointSchema,
        )

        req = AeroBuildupTrimRequest(
            operating_point=OperatingPointSchema(velocity=20.0, alpha=3.0),
            trim_variable="aileron",
            target_coefficient="Cl",
            target_value=0.01,
            deflection_bounds=[-15.0, 15.0],
        )
        assert req.trim_variable == "aileron"
        assert req.target_coefficient == "Cl"
        assert req.target_value == 0.01
        assert req.deflection_bounds == [-15.0, 15.0]

    def test_invalid_trim_variable_special_chars(self):
        from pydantic import ValidationError as PydanticValidationError

        from app.schemas.aeroanalysisschema import (
            AeroBuildupTrimRequest,
            OperatingPointSchema,
        )

        with pytest.raises(PydanticValidationError, match="Invalid trim variable name"):
            AeroBuildupTrimRequest(
                operating_point=OperatingPointSchema(velocity=15.0),
                trim_variable="bad-name!",
            )

    def test_invalid_trim_variable_starts_with_digit(self):
        from pydantic import ValidationError as PydanticValidationError

        from app.schemas.aeroanalysisschema import (
            AeroBuildupTrimRequest,
            OperatingPointSchema,
        )

        with pytest.raises(PydanticValidationError, match="Invalid trim variable name"):
            AeroBuildupTrimRequest(
                operating_point=OperatingPointSchema(velocity=15.0),
                trim_variable="1elevator",
            )

    def test_invalid_trim_variable_empty(self):
        from pydantic import ValidationError as PydanticValidationError

        from app.schemas.aeroanalysisschema import (
            AeroBuildupTrimRequest,
            OperatingPointSchema,
        )

        with pytest.raises(PydanticValidationError, match="Invalid trim variable name"):
            AeroBuildupTrimRequest(
                operating_point=OperatingPointSchema(velocity=15.0),
                trim_variable="",
            )

    def test_bounds_wrong_order_rejected(self):
        from pydantic import ValidationError as PydanticValidationError

        from app.schemas.aeroanalysisschema import (
            AeroBuildupTrimRequest,
            OperatingPointSchema,
        )

        with pytest.raises(PydanticValidationError, match="must be less than"):
            AeroBuildupTrimRequest(
                operating_point=OperatingPointSchema(velocity=15.0),
                deflection_bounds=[25.0, -25.0],
            )

    def test_bounds_equal_rejected(self):
        from pydantic import ValidationError as PydanticValidationError

        from app.schemas.aeroanalysisschema import (
            AeroBuildupTrimRequest,
            OperatingPointSchema,
        )

        with pytest.raises(PydanticValidationError, match="must be less than"):
            AeroBuildupTrimRequest(
                operating_point=OperatingPointSchema(velocity=15.0),
                deflection_bounds=[0.0, 0.0],
            )

    def test_alpha_as_list_rejected(self):
        from pydantic import ValidationError as PydanticValidationError

        from app.schemas.aeroanalysisschema import (
            AeroBuildupTrimRequest,
            OperatingPointSchema,
        )

        with pytest.raises(PydanticValidationError, match="Alpha must be a scalar"):
            AeroBuildupTrimRequest(
                operating_point=OperatingPointSchema(velocity=15.0, alpha=[1.0, 2.0]),
            )

    def test_custom_target_coefficient(self):
        from app.schemas.aeroanalysisschema import (
            AeroBuildupTrimRequest,
            OperatingPointSchema,
        )

        req = AeroBuildupTrimRequest(
            operating_point=OperatingPointSchema(velocity=15.0, alpha=5.0),
            target_coefficient="CL",
            target_value=0.5,
        )
        assert req.target_coefficient == "CL"
        assert req.target_value == 0.5


# =========================================================================== #
# Schema validation — AeroBuildupTrimResult
# =========================================================================== #


class TestAeroBuildupTrimResult:
    """Verify AeroBuildupTrimResult schema construction."""

    def test_result_with_all_fields(self):
        from app.schemas.aeroanalysisschema import AeroBuildupTrimResult

        result = AeroBuildupTrimResult(
            converged=True,
            trim_variable="elevator",
            trimmed_deflection=-3.5,
            target_coefficient="Cm",
            achieved_value=0.0001,
            aero_coefficients={"CL": 0.5, "CD": 0.03, "Cm": 0.0001},
            stability_derivatives={"CL_a": 6.1, "Cm_a": -1.2},
        )
        assert result.converged is True
        assert result.trim_variable == "elevator"
        assert result.trimmed_deflection == -3.5
        assert result.target_coefficient == "Cm"
        assert result.achieved_value == 0.0001
        assert result.aero_coefficients["CL"] == 0.5
        assert result.stability_derivatives["CL_a"] == 6.1

    def test_result_not_converged(self):
        from app.schemas.aeroanalysisschema import AeroBuildupTrimResult

        result = AeroBuildupTrimResult(
            converged=False,
            trim_variable="elevator",
            trimmed_deflection=0.0,
            target_coefficient="Cm",
            achieved_value=float("nan"),
        )
        assert result.converged is False
        assert result.trim_variable == "elevator"
        assert result.trimmed_deflection == 0.0
        assert result.aero_coefficients == {}
        assert result.stability_derivatives == {}


# =========================================================================== #
# Service unit tests — trim_with_aerobuildup (mocked)
# =========================================================================== #


def _make_mock_airplane_with_controls(control_names: list[str]) -> MagicMock:
    """Build a mock ASB airplane with the given control surfaces."""
    airplane = MagicMock()
    cs_list = []
    for name in control_names:
        cs = MagicMock()
        cs.name = name
        cs.deflection = 0.0
        cs_list.append(cs)
    xsec = MagicMock()
    xsec.control_surfaces = cs_list
    wing = MagicMock()
    wing.xsecs = [xsec]
    airplane.wings = [wing]
    return airplane


class TestTrimWithAerobuildup:
    """Verify the trim_with_aerobuildup service orchestrates correctly."""

    @patch("app.converters.model_schema_converters.aeroplane_schema_to_asb_airplane_async")
    @patch("app.services.analysis_service.get_aeroplane_schema_or_raise")
    def test_success_trim_converges(self, mock_get_schema, mock_to_asb):
        """Mock AeroBuildup so Cm varies linearly with deflection; verify convergence."""
        from app.schemas.aeroanalysisschema import (
            AeroBuildupTrimRequest,
            OperatingPointSchema,
        )
        from app.services.aerobuildup_trim_service import trim_with_aerobuildup

        mock_get_schema.return_value = MagicMock()
        mock_airplane = _make_mock_airplane_with_controls(["elevator"])
        mock_to_asb.return_value = mock_airplane

        # Mock AeroBuildup: Cm = 0.1 * deflection (trim at deflection=0)
        # But we want Cm=0 for trim — the residual is Cm - 0 = 0.1*d
        # So trim should find deflection=0.0
        def mock_aerobuildup_init(airplane, op_point, xyz_ref):
            abu = MagicMock()

            def run_with_stability_derivatives():
                # We need to get the deflection from the airplane's control surface
                # But since we're mocking with_control_deflections, we track the deflection
                return {
                    "CL": 0.5,
                    "CD": 0.03,
                    "CY": 0.0,
                    "Cm": 0.0,  # Will be overridden below
                    "Cl": 0.0,
                    "Cn": 0.0,
                    "CL_a": 6.1,
                    "Cm_a": -1.2,
                }

            abu.run_with_stability_derivatives = run_with_stability_derivatives
            return abu

        # Instead of mocking AeroBuildup class, mock _run_single_aerobuildup
        call_count = [0]
        deflections_seen = []

        def mock_run_single(asb_airplane, op_point, xyz_ref, trim_variable, deflection_deg):
            call_count[0] += 1
            deflections_seen.append(deflection_deg)
            # Cm varies linearly: Cm = 0.1 + 0.02 * deflection
            # Root at deflection = -5.0
            cm_val = 0.1 + 0.02 * deflection_deg
            return {
                "CL": 0.5,
                "CD": 0.03,
                "CY": 0.0,
                "Cm": cm_val,
                "Cl": 0.0,
                "Cn": 0.0,
                "CL_a": 6.1,
                "Cm_a": -1.2,
            }

        with patch(
            "app.services.aerobuildup_trim_service._run_single_aerobuildup",
            side_effect=mock_run_single,
        ):
            request = AeroBuildupTrimRequest(
                operating_point=OperatingPointSchema(velocity=15.0, alpha=5.0),
                trim_variable="elevator",
            )
            result = asyncio.run(
                trim_with_aerobuildup(db=MagicMock(), aeroplane_uuid="test-uuid", request=request)
            )

        assert result.converged is True
        assert result.trim_variable == "elevator"
        assert result.target_coefficient == "Cm"
        assert abs(result.trimmed_deflection - (-5.0)) < 1e-4
        assert abs(result.achieved_value) < 1e-4
        assert "CL" in result.aero_coefficients
        assert "CL_a" in result.stability_derivatives

    @patch("app.services.analysis_service.get_aeroplane_schema_or_raise")
    def test_aeroplane_not_found(self, mock_get_schema):
        from app.core.exceptions import NotFoundError
        from app.schemas.aeroanalysisschema import (
            AeroBuildupTrimRequest,
            OperatingPointSchema,
        )
        from app.services.aerobuildup_trim_service import trim_with_aerobuildup

        mock_get_schema.side_effect = NotFoundError(message="not found")

        request = AeroBuildupTrimRequest(
            operating_point=OperatingPointSchema(velocity=15.0),
        )

        with pytest.raises(NotFoundError):
            asyncio.run(
                trim_with_aerobuildup(db=MagicMock(), aeroplane_uuid="bad-uuid", request=request)
            )

    @patch("app.converters.model_schema_converters.aeroplane_schema_to_asb_airplane_async")
    @patch("app.services.analysis_service.get_aeroplane_schema_or_raise")
    def test_control_surface_not_found(self, mock_get_schema, mock_to_asb):
        from app.core.exceptions import ValidationDomainError
        from app.schemas.aeroanalysisschema import (
            AeroBuildupTrimRequest,
            OperatingPointSchema,
        )
        from app.services.aerobuildup_trim_service import trim_with_aerobuildup

        mock_get_schema.return_value = MagicMock()
        # Airplane has no control surfaces
        mock_airplane = _make_mock_airplane_with_controls([])
        mock_to_asb.return_value = mock_airplane

        request = AeroBuildupTrimRequest(
            operating_point=OperatingPointSchema(velocity=15.0, alpha=5.0),
            trim_variable="elevator",
        )

        with pytest.raises(ValidationDomainError, match="Control surface 'elevator' not found"):
            asyncio.run(
                trim_with_aerobuildup(db=MagicMock(), aeroplane_uuid="test-uuid", request=request)
            )

    @patch("app.converters.model_schema_converters.aeroplane_schema_to_asb_airplane_async")
    @patch("app.services.analysis_service.get_aeroplane_schema_or_raise")
    def test_root_not_bracketed_returns_not_converged(self, mock_get_schema, mock_to_asb):
        """When residual has the same sign at both bounds, return converged=False."""
        from app.schemas.aeroanalysisschema import (
            AeroBuildupTrimRequest,
            OperatingPointSchema,
        )
        from app.services.aerobuildup_trim_service import trim_with_aerobuildup

        mock_get_schema.return_value = MagicMock()
        mock_airplane = _make_mock_airplane_with_controls(["elevator"])
        mock_to_asb.return_value = mock_airplane

        # Cm is always positive — no root in bounds
        def mock_run_single(asb_airplane, op_point, xyz_ref, trim_variable, deflection_deg):
            return {
                "CL": 0.5,
                "CD": 0.03,
                "Cm": 1.0,  # Always positive, never crosses zero
            }

        with patch(
            "app.services.aerobuildup_trim_service._run_single_aerobuildup",
            side_effect=mock_run_single,
        ):
            request = AeroBuildupTrimRequest(
                operating_point=OperatingPointSchema(velocity=15.0, alpha=5.0),
                trim_variable="elevator",
            )
            result = asyncio.run(
                trim_with_aerobuildup(db=MagicMock(), aeroplane_uuid="test-uuid", request=request)
            )

        assert result.converged is False
        assert math.isnan(result.achieved_value)

    @patch("app.converters.model_schema_converters.aeroplane_schema_to_asb_airplane_async")
    @patch("app.services.analysis_service.get_aeroplane_schema_or_raise")
    def test_brentq_convergence_failure_returns_not_converged(self, mock_get_schema, mock_to_asb):
        """If brentq raises ValueError internally, return converged=False."""
        from app.schemas.aeroanalysisschema import (
            AeroBuildupTrimRequest,
            OperatingPointSchema,
        )
        from app.services.aerobuildup_trim_service import trim_with_aerobuildup

        mock_get_schema.return_value = MagicMock()
        mock_airplane = _make_mock_airplane_with_controls(["elevator"])
        mock_to_asb.return_value = mock_airplane

        # Residual changes sign (so bracket check passes) but brentq fails
        call_count = [0]

        def mock_run_single(asb_airplane, op_point, xyz_ref, trim_variable, deflection_deg):
            call_count[0] += 1
            # First two calls: bounds evaluation (opposite signs)
            if call_count[0] <= 2:
                return {
                    "CL": 0.5,
                    "CD": 0.03,
                    "Cm": -1.0 if deflection_deg < 0 else 1.0,
                }
            # Subsequent calls during brentq: raise to simulate failure
            raise RuntimeError("simulation diverged")

        with patch(
            "app.services.aerobuildup_trim_service._run_single_aerobuildup",
            side_effect=mock_run_single,
        ):
            # brentq will catch the RuntimeError and re-raise as ValueError
            # Actually, brentq doesn't catch runtime errors — it will propagate.
            # Let's mock brentq itself to raise ValueError
            pass

        # Better approach: mock brentq directly
        with (
            patch(
                "app.services.aerobuildup_trim_service._run_single_aerobuildup",
                side_effect=lambda *a, **kw: {
                    "CL": 0.5,
                    "CD": 0.03,
                    "Cm": -0.5 if a[4] < 0 else 0.5,
                },
            ),
            patch(
                "app.services.aerobuildup_trim_service.brentq",
                side_effect=ValueError("convergence failed"),
            ),
        ):
            request = AeroBuildupTrimRequest(
                operating_point=OperatingPointSchema(velocity=15.0, alpha=5.0),
                trim_variable="elevator",
            )
            result = asyncio.run(
                trim_with_aerobuildup(db=MagicMock(), aeroplane_uuid="test-uuid", request=request)
            )

        assert result.converged is False
        assert math.isnan(result.achieved_value)


# =========================================================================== #
# Endpoint integration tests
# =========================================================================== #


class TestAeroBuildupTrimEndpoint:
    """Verify the /aeroplanes/{uuid}/operating-points/aerobuildup-trim endpoint."""

    @pytest.fixture()
    def client_and_db(self):
        from fastapi.testclient import TestClient
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool

        from app.db.base import Base
        from app.db.session import get_db
        from app.main import create_app

        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=engine)
        TestingSessionLocal = sessionmaker(bind=engine)

        app = create_app()

        def override_get_db():
            db = TestingSessionLocal()
            try:
                yield db
                db.commit()
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        with TestClient(app) as client:
            yield client, TestingSessionLocal

        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)

    @patch("app.services.aerobuildup_trim_service.trim_with_aerobuildup")
    def test_endpoint_success(self, mock_trim, client_and_db):
        from app.schemas.aeroanalysisschema import AeroBuildupTrimResult

        client, _ = client_and_db
        aeroplane_uuid = str(uuid.uuid4())

        mock_trim.return_value = AeroBuildupTrimResult(
            converged=True,
            trim_variable="elevator",
            trimmed_deflection=-3.5,
            target_coefficient="Cm",
            achieved_value=0.0001,
            aero_coefficients={"CL": 0.5, "CD": 0.03, "Cm": 0.0001},
            stability_derivatives={"CL_a": 6.1},
        )

        payload = {
            "operating_point": {"velocity": 15.0, "alpha": 5.0},
            "trim_variable": "elevator",
        }
        resp = client.post(
            f"/aeroplanes/{aeroplane_uuid}/operating-points/aerobuildup-trim",
            json=payload,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["converged"] is True
        assert data["trim_variable"] == "elevator"
        assert data["trimmed_deflection"] == -3.5
        assert data["aero_coefficients"]["CL"] == 0.5

    @patch("app.services.aerobuildup_trim_service.trim_with_aerobuildup")
    def test_endpoint_not_found(self, mock_trim, client_and_db):
        from app.core.exceptions import NotFoundError

        client, _ = client_and_db
        aeroplane_uuid = str(uuid.uuid4())

        mock_trim.side_effect = NotFoundError(message="Aeroplane not found")

        payload = {
            "operating_point": {"velocity": 15.0, "alpha": 5.0},
        }
        resp = client.post(
            f"/aeroplanes/{aeroplane_uuid}/operating-points/aerobuildup-trim",
            json=payload,
        )
        assert resp.status_code == 404

    def test_endpoint_validation_error_from_schema(self, client_and_db):
        """Invalid trim_variable should be rejected at the schema level (422)."""
        client, _ = client_and_db
        aeroplane_uuid = str(uuid.uuid4())

        payload = {
            "operating_point": {"velocity": 15.0, "alpha": 5.0},
            "trim_variable": "bad-name!",
        }
        resp = client.post(
            f"/aeroplanes/{aeroplane_uuid}/operating-points/aerobuildup-trim",
            json=payload,
        )
        assert resp.status_code == 422

    @patch("app.services.aerobuildup_trim_service.trim_with_aerobuildup")
    def test_endpoint_domain_validation_error(self, mock_trim, client_and_db):
        from app.core.exceptions import ValidationDomainError

        client, _ = client_and_db
        aeroplane_uuid = str(uuid.uuid4())

        mock_trim.side_effect = ValidationDomainError(
            message="Control surface 'elevator' not found on airplane."
        )

        payload = {
            "operating_point": {"velocity": 15.0, "alpha": 5.0},
        }
        resp = client.post(
            f"/aeroplanes/{aeroplane_uuid}/operating-points/aerobuildup-trim",
            json=payload,
        )
        assert resp.status_code == 422
