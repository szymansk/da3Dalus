"""Tests for AVL trim analysis — indirect constraints.

Covers: TrimTarget, TrimConstraint, AVLTrimRequest, AVLTrimResult schemas,
get_control_surface_index_map, build_indirect_constraint_commands,
_categorize_results, trim_with_avl service, and the AVL trim endpoint.
"""

from __future__ import annotations

import asyncio
import uuid
from unittest.mock import MagicMock, patch

import pytest


# =========================================================================== #
# Schema validation
# =========================================================================== #


class TestTrimTarget:
    """Verify TrimTarget enum values match AVL indirect constraint codes."""

    def test_all_target_values(self):
        from app.schemas.aeroanalysisschema import TrimTarget

        assert TrimTarget.CL.value == "C"
        assert TrimTarget.CY.value == "S"
        assert TrimTarget.PITCHING_MOMENT.value == "PM"
        assert TrimTarget.ROLLING_MOMENT.value == "RM"
        assert TrimTarget.YAWING_MOMENT.value == "YM"

    def test_enum_count(self):
        from app.schemas.aeroanalysisschema import TrimTarget

        assert len(TrimTarget) == 5


class TestTrimConstraint:
    """Verify TrimConstraint schema validation."""

    def test_valid_constraint(self):
        from app.schemas.aeroanalysisschema import TrimConstraint, TrimTarget

        tc = TrimConstraint(variable="alpha", target=TrimTarget.CL, value=0.5)
        assert tc.variable == "alpha"
        assert tc.target == TrimTarget.CL
        assert tc.value == 0.5

    def test_default_value_is_zero(self):
        from app.schemas.aeroanalysisschema import TrimConstraint, TrimTarget

        tc = TrimConstraint(variable="elevator", target=TrimTarget.PITCHING_MOMENT)
        assert tc.value == 0.0

    def test_control_surface_variable(self):
        from app.schemas.aeroanalysisschema import TrimConstraint, TrimTarget

        tc = TrimConstraint(variable="elevator", target=TrimTarget.PITCHING_MOMENT, value=0.0)
        assert tc.variable == "elevator"


class TestAVLTrimRequest:
    """Verify AVLTrimRequest schema validation."""

    def test_valid_request(self):
        from app.schemas.aeroanalysisschema import (
            AVLTrimRequest,
            OperatingPointSchema,
            TrimConstraint,
            TrimTarget,
        )

        req = AVLTrimRequest(
            operating_point=OperatingPointSchema(velocity=15.0, alpha=5.0),
            trim_constraints=[
                TrimConstraint(variable="elevator", target=TrimTarget.PITCHING_MOMENT, value=0.0),
            ],
        )
        assert len(req.trim_constraints) == 1

    def test_empty_constraints_rejected(self):
        from pydantic import ValidationError as PydanticValidationError

        from app.schemas.aeroanalysisschema import AVLTrimRequest, OperatingPointSchema

        with pytest.raises(PydanticValidationError):
            AVLTrimRequest(
                operating_point=OperatingPointSchema(velocity=15.0),
                trim_constraints=[],
            )

    def test_multiple_constraints(self):
        from app.schemas.aeroanalysisschema import (
            AVLTrimRequest,
            OperatingPointSchema,
            TrimConstraint,
            TrimTarget,
        )

        req = AVLTrimRequest(
            operating_point=OperatingPointSchema(velocity=15.0),
            trim_constraints=[
                TrimConstraint(variable="elevator", target=TrimTarget.PITCHING_MOMENT),
                TrimConstraint(variable="alpha", target=TrimTarget.CL, value=0.5),
            ],
        )
        assert len(req.trim_constraints) == 2


class TestAVLTrimResult:
    """Verify AVLTrimResult schema construction."""

    def test_result_with_all_fields(self):
        from app.schemas.aeroanalysisschema import AVLTrimResult

        result = AVLTrimResult(
            converged=True,
            trimmed_deflections={"elevator": -2.5},
            trimmed_state={"alpha": 3.2},
            aero_coefficients={"CL": 0.5, "CD": 0.03},
            forces_and_moments={"L": 50.0, "D": 3.0},
            stability_derivatives={"CL_a": 6.1},
            raw_results={"CL": 0.5, "CD": 0.03, "alpha": 3.2},
        )
        assert result.converged is True
        assert result.trimmed_deflections["elevator"] == -2.5
        assert result.aero_coefficients["CL"] == 0.5

    def test_result_not_converged(self):
        from app.schemas.aeroanalysisschema import AVLTrimResult

        result = AVLTrimResult(converged=False)
        assert result.converged is False
        assert result.trimmed_deflections == {}
        assert result.aero_coefficients == {}


# =========================================================================== #
# get_control_surface_index_map
# =========================================================================== #


class TestGetControlSurfaceIndexMap:
    """Verify control surface index mapping from airplane geometry."""

    def _make_cs(self, name: str, deflection: float = 0.0) -> MagicMock:
        cs = MagicMock()
        cs.name = name
        cs.deflection = deflection
        return cs

    def _make_xsec(self, control_surfaces: list) -> MagicMock:
        xsec = MagicMock()
        xsec.control_surfaces = control_surfaces
        return xsec

    def _make_wing(self, xsecs: list) -> MagicMock:
        wing = MagicMock()
        wing.xsecs = xsecs
        return wing

    def test_single_control_surface(self):
        from app.services.avl_strip_forces import get_control_surface_index_map

        airplane = MagicMock()
        airplane.wings = [
            self._make_wing(
                [
                    self._make_xsec([self._make_cs("elevator")]),
                ]
            )
        ]
        result = get_control_surface_index_map(airplane)
        assert result == {"elevator": 1}

    def test_multiple_control_surfaces(self):
        from app.services.avl_strip_forces import get_control_surface_index_map

        airplane = MagicMock()
        airplane.wings = [
            self._make_wing(
                [
                    self._make_xsec([self._make_cs("aileron")]),
                    self._make_xsec([self._make_cs("flap")]),
                ]
            ),
            self._make_wing(
                [
                    self._make_xsec([self._make_cs("elevator")]),
                ]
            ),
        ]
        result = get_control_surface_index_map(airplane)
        assert result == {"aileron": 1, "flap": 2, "elevator": 3}

    def test_duplicate_names_get_first_index(self):
        from app.services.avl_strip_forces import get_control_surface_index_map

        airplane = MagicMock()
        airplane.wings = [
            self._make_wing(
                [
                    self._make_xsec([self._make_cs("aileron")]),
                    self._make_xsec([self._make_cs("aileron")]),
                ]
            ),
        ]
        result = get_control_surface_index_map(airplane)
        assert result == {"aileron": 1}

    def test_no_control_surfaces(self):
        from app.services.avl_strip_forces import get_control_surface_index_map

        airplane = MagicMock()
        airplane.wings = [
            self._make_wing([self._make_xsec([])]),
        ]
        result = get_control_surface_index_map(airplane)
        assert result == {}

    def test_no_wings(self):
        from app.services.avl_strip_forces import get_control_surface_index_map

        airplane = MagicMock()
        airplane.wings = []
        result = get_control_surface_index_map(airplane)
        assert result == {}


# =========================================================================== #
# build_indirect_constraint_commands
# =========================================================================== #


class TestBuildIndirectConstraintCommands:
    """Verify AVL indirect constraint keystroke generation."""

    def _make_cs(self, name: str) -> MagicMock:
        cs = MagicMock()
        cs.name = name
        cs.deflection = 0.0
        return cs

    def _make_xsec(self, control_surfaces: list) -> MagicMock:
        xsec = MagicMock()
        xsec.control_surfaces = control_surfaces
        return xsec

    def _make_wing(self, xsecs: list) -> MagicMock:
        wing = MagicMock()
        wing.xsecs = xsecs
        return wing

    def _make_airplane(self, cs_names: list[str]) -> MagicMock:
        airplane = MagicMock()
        cs_list = [self._make_cs(name) for name in cs_names]
        airplane.wings = [self._make_wing([self._make_xsec(cs_list)])]
        return airplane

    def test_alpha_to_cl(self):
        from app.schemas.aeroanalysisschema import TrimConstraint, TrimTarget
        from app.services.avl_strip_forces import build_indirect_constraint_commands

        airplane = self._make_airplane([])
        tc = TrimConstraint(variable="alpha", target=TrimTarget.CL, value=0.5)
        commands = build_indirect_constraint_commands(airplane, [tc])
        assert commands == ["a C 0.5"]

    def test_beta_to_cy(self):
        from app.schemas.aeroanalysisschema import TrimConstraint, TrimTarget
        from app.services.avl_strip_forces import build_indirect_constraint_commands

        airplane = self._make_airplane([])
        tc = TrimConstraint(variable="beta", target=TrimTarget.CY, value=0.0)
        commands = build_indirect_constraint_commands(airplane, [tc])
        assert commands == ["b S 0.0"]

    def test_roll_rate_to_rm(self):
        from app.schemas.aeroanalysisschema import TrimConstraint, TrimTarget
        from app.services.avl_strip_forces import build_indirect_constraint_commands

        airplane = self._make_airplane([])
        tc = TrimConstraint(variable="roll_rate", target=TrimTarget.ROLLING_MOMENT, value=0.0)
        commands = build_indirect_constraint_commands(airplane, [tc])
        assert commands == ["r RM 0.0"]

    def test_pitch_rate_to_pm(self):
        from app.schemas.aeroanalysisschema import TrimConstraint, TrimTarget
        from app.services.avl_strip_forces import build_indirect_constraint_commands

        airplane = self._make_airplane([])
        tc = TrimConstraint(variable="pitch_rate", target=TrimTarget.PITCHING_MOMENT, value=0.0)
        commands = build_indirect_constraint_commands(airplane, [tc])
        assert commands == ["p PM 0.0"]

    def test_yaw_rate_to_ym(self):
        from app.schemas.aeroanalysisschema import TrimConstraint, TrimTarget
        from app.services.avl_strip_forces import build_indirect_constraint_commands

        airplane = self._make_airplane([])
        tc = TrimConstraint(variable="yaw_rate", target=TrimTarget.YAWING_MOMENT, value=0.0)
        commands = build_indirect_constraint_commands(airplane, [tc])
        assert commands == ["y YM 0.0"]

    def test_control_surface_to_pm(self):
        from app.schemas.aeroanalysisschema import TrimConstraint, TrimTarget
        from app.services.avl_strip_forces import build_indirect_constraint_commands

        airplane = self._make_airplane(["elevator"])
        tc = TrimConstraint(variable="elevator", target=TrimTarget.PITCHING_MOMENT, value=0.0)
        commands = build_indirect_constraint_commands(airplane, [tc])
        assert commands == ["d1 PM 0.0"]

    def test_multiple_control_surfaces(self):
        from app.schemas.aeroanalysisschema import TrimConstraint, TrimTarget
        from app.services.avl_strip_forces import build_indirect_constraint_commands

        airplane = self._make_airplane(["aileron", "elevator", "rudder"])
        constraints = [
            TrimConstraint(variable="elevator", target=TrimTarget.PITCHING_MOMENT, value=0.0),
            TrimConstraint(variable="aileron", target=TrimTarget.ROLLING_MOMENT, value=0.0),
        ]
        commands = build_indirect_constraint_commands(airplane, constraints)
        assert commands == ["d2 PM 0.0", "d1 RM 0.0"]

    def test_unknown_variable_raises_value_error(self):
        from app.schemas.aeroanalysisschema import TrimConstraint, TrimTarget
        from app.services.avl_strip_forces import build_indirect_constraint_commands

        airplane = self._make_airplane(["elevator"])
        tc = TrimConstraint(variable="nonexistent_surface", target=TrimTarget.PITCHING_MOMENT)
        with pytest.raises(ValueError, match="Unknown trim variable 'nonexistent_surface'"):
            build_indirect_constraint_commands(airplane, [tc])

    def test_mixed_state_and_control(self):
        from app.schemas.aeroanalysisschema import TrimConstraint, TrimTarget
        from app.services.avl_strip_forces import build_indirect_constraint_commands

        airplane = self._make_airplane(["elevator"])
        constraints = [
            TrimConstraint(variable="alpha", target=TrimTarget.CL, value=0.5),
            TrimConstraint(variable="elevator", target=TrimTarget.PITCHING_MOMENT, value=0.0),
        ]
        commands = build_indirect_constraint_commands(airplane, constraints)
        assert commands == ["a C 0.5", "d1 PM 0.0"]


# =========================================================================== #
# _categorize_results
# =========================================================================== #


class TestCategorizeResults:
    """Verify _categorize_results splits raw AVL output into categories."""

    def test_converged_result(self):
        from app.services.avl_trim_service import _categorize_results

        raw = {
            "CL": 0.5,
            "CD": 0.03,
            "CY": 0.0,
            "Cm": -0.01,
            "Cl": 0.0,
            "Cn": 0.0,
            "CDind": 0.02,
            "e": 0.95,
            "alpha": 3.2,
            "beta": 0.0,
            "mach": 0.05,
            "L": 50.0,
            "D": 3.0,
            "Y": 0.0,
            "l_b": 0.0,
            "m_b": -1.0,
            "n_b": 0.0,
            "CL_a": 6.1,
            "Cm_a": -1.2,
            "elevator": -2.5,
        }
        control_names = {"elevator"}
        result = _categorize_results(raw, control_names)

        assert result.converged is True
        assert result.aero_coefficients["CL"] == 0.5
        assert result.aero_coefficients["CD"] == 0.03
        assert result.forces_and_moments["L"] == 50.0
        assert result.trimmed_state["alpha"] == 3.2
        assert result.stability_derivatives["CL_a"] == 6.1
        assert result.trimmed_deflections["elevator"] == -2.5

    def test_not_converged_when_no_cl(self):
        from app.services.avl_trim_service import _categorize_results

        raw = {"some_key": 1.0}
        result = _categorize_results(raw, set())
        assert result.converged is False

    def test_raw_results_only_numeric(self):
        from app.services.avl_trim_service import _categorize_results

        raw = {"CL": 0.5, "F_w": [1, 2, 3], "name": "test"}
        result = _categorize_results(raw, set())
        assert "CL" in result.raw_results
        assert "F_w" not in result.raw_results
        assert "name" not in result.raw_results

    def test_multiple_control_surfaces(self):
        from app.services.avl_trim_service import _categorize_results

        raw = {
            "CL": 0.5,
            "elevator": -2.5,
            "aileron": 3.0,
            "rudder": 1.0,
        }
        control_names = {"elevator", "aileron", "rudder"}
        result = _categorize_results(raw, control_names)
        assert result.trimmed_deflections == {"elevator": -2.5, "aileron": 3.0, "rudder": 1.0}


# =========================================================================== #
# trim_with_avl service function (mocked integration)
# =========================================================================== #


class TestTrimWithAvl:
    """Verify the trim_with_avl service orchestrates all components correctly."""

    @patch("app.services.avl_strip_forces.get_control_surface_index_map")
    @patch("app.services.avl_runner.AVLRunner")
    @patch("app.converters.model_schema_converters.aeroplane_schema_to_asb_airplane_async")
    @patch("app.services.avl_geometry_service.get_user_avl_content")
    @patch("app.services.analysis_service.get_aeroplane_schema_or_raise")
    def test_trim_with_avl_success(
        self,
        mock_get_schema,
        mock_get_avl_content,
        mock_to_asb,
        mock_runner_cls,
        mock_cs_map,
    ):
        from app.schemas.aeroanalysisschema import (
            AVLTrimRequest,
            OperatingPointSchema,
            TrimConstraint,
            TrimTarget,
        )
        from app.services.avl_trim_service import trim_with_avl

        # Setup mocks
        mock_get_schema.return_value = MagicMock()
        mock_get_avl_content.return_value = "FAKE AVL CONTENT"

        mock_asb_airplane = MagicMock()
        mock_to_asb.return_value = mock_asb_airplane

        mock_runner = MagicMock()
        mock_runner.run_trim.return_value = {"CL": 0.5, "CD": 0.03, "alpha": 3.2}
        mock_runner_cls.return_value = mock_runner

        mock_cs_map.return_value = {}

        db = MagicMock()
        request = AVLTrimRequest(
            operating_point=OperatingPointSchema(velocity=15.0, alpha=5.0),
            trim_constraints=[
                TrimConstraint(variable="alpha", target=TrimTarget.CL, value=0.5),
            ],
        )

        result = asyncio.run(trim_with_avl(db, "test-uuid", request))

        assert result.converged is True
        assert result.aero_coefficients["CL"] == 0.5
        mock_runner.run_trim.assert_called_once()

    @patch("app.services.analysis_service.get_aeroplane_schema_or_raise")
    def test_trim_with_avl_aeroplane_not_found(self, mock_get_schema):
        from app.core.exceptions import NotFoundError
        from app.schemas.aeroanalysisschema import (
            AVLTrimRequest,
            OperatingPointSchema,
            TrimConstraint,
            TrimTarget,
        )
        from app.services.avl_trim_service import trim_with_avl

        mock_get_schema.side_effect = NotFoundError(message="not found")

        db = MagicMock()
        request = AVLTrimRequest(
            operating_point=OperatingPointSchema(velocity=15.0),
            trim_constraints=[
                TrimConstraint(variable="alpha", target=TrimTarget.CL, value=0.5),
            ],
        )

        with pytest.raises(NotFoundError):
            asyncio.run(trim_with_avl(db, "bad-uuid", request))


# =========================================================================== #
# Validator tests
# =========================================================================== #


class TestTrimConstraintValidators:
    """Verify TrimConstraint field validators."""

    def test_valid_known_state_variable(self):
        from app.schemas.aeroanalysisschema import TrimConstraint, TrimTarget

        for var in ("alpha", "beta", "roll_rate", "pitch_rate", "yaw_rate"):
            tc = TrimConstraint(variable=var, target=TrimTarget.CL)
            assert tc.variable == var

    def test_valid_control_surface_name(self):
        from app.schemas.aeroanalysisschema import TrimConstraint, TrimTarget

        tc = TrimConstraint(variable="elevator", target=TrimTarget.PITCHING_MOMENT)
        assert tc.variable == "elevator"

    def test_invalid_empty_variable_rejected(self):
        from pydantic import ValidationError as PydanticValidationError

        from app.schemas.aeroanalysisschema import TrimConstraint, TrimTarget

        with pytest.raises(PydanticValidationError, match="Invalid variable name"):
            TrimConstraint(variable="", target=TrimTarget.CL)

    def test_invalid_special_chars_rejected(self):
        from pydantic import ValidationError as PydanticValidationError

        from app.schemas.aeroanalysisschema import TrimConstraint, TrimTarget

        with pytest.raises(PydanticValidationError, match="Invalid variable name"):
            TrimConstraint(variable="bad-name!", target=TrimTarget.CL)

    def test_invalid_starts_with_digit_rejected(self):
        from pydantic import ValidationError as PydanticValidationError

        from app.schemas.aeroanalysisschema import TrimConstraint, TrimTarget

        with pytest.raises(PydanticValidationError, match="Invalid variable name"):
            TrimConstraint(variable="1elevator", target=TrimTarget.CL)


class TestAVLTrimRequestValidators:
    """Verify AVLTrimRequest model validators."""

    def test_duplicate_variables_rejected(self):
        from pydantic import ValidationError as PydanticValidationError

        from app.schemas.aeroanalysisschema import (
            AVLTrimRequest,
            OperatingPointSchema,
            TrimConstraint,
            TrimTarget,
        )

        with pytest.raises(PydanticValidationError, match="Duplicate trim variables"):
            AVLTrimRequest(
                operating_point=OperatingPointSchema(velocity=15.0),
                trim_constraints=[
                    TrimConstraint(variable="alpha", target=TrimTarget.CL, value=0.5),
                    TrimConstraint(variable="alpha", target=TrimTarget.PITCHING_MOMENT, value=0.0),
                ],
            )

    def test_duplicate_targets_rejected(self):
        from pydantic import ValidationError as PydanticValidationError

        from app.schemas.aeroanalysisschema import (
            AVLTrimRequest,
            OperatingPointSchema,
            TrimConstraint,
            TrimTarget,
        )

        with pytest.raises(PydanticValidationError, match="Duplicate trim targets"):
            AVLTrimRequest(
                operating_point=OperatingPointSchema(velocity=15.0),
                trim_constraints=[
                    TrimConstraint(variable="alpha", target=TrimTarget.CL, value=0.5),
                    TrimConstraint(variable="elevator", target=TrimTarget.CL, value=0.3),
                ],
            )

    def test_alpha_as_list_rejected(self):
        from pydantic import ValidationError as PydanticValidationError

        from app.schemas.aeroanalysisschema import (
            AVLTrimRequest,
            OperatingPointSchema,
            TrimConstraint,
            TrimTarget,
        )

        with pytest.raises(PydanticValidationError, match="Alpha must be a scalar"):
            AVLTrimRequest(
                operating_point=OperatingPointSchema(velocity=15.0, alpha=[1.0, 2.0]),
                trim_constraints=[
                    TrimConstraint(variable="alpha", target=TrimTarget.CL, value=0.5),
                ],
            )


# =========================================================================== #
# AVL trim endpoint tests
# =========================================================================== #


class TestAVLTrimEndpoint:
    """Verify the /aeroplanes/{uuid}/operating-points/avl-trim endpoint."""

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

    @patch("app.services.avl_trim_service.trim_with_avl")
    def test_avl_trim_endpoint_success(self, mock_trim, client_and_db):
        from app.schemas.aeroanalysisschema import AVLTrimResult

        client, _ = client_and_db
        aeroplane_uuid = str(uuid.uuid4())

        mock_trim.return_value = AVLTrimResult(
            converged=True,
            trimmed_deflections={"elevator": -2.5},
            trimmed_state={"alpha": 3.2},
            aero_coefficients={"CL": 0.5, "CD": 0.03},
            forces_and_moments={"L": 50.0},
            stability_derivatives={"CL_a": 6.1},
            raw_results={"CL": 0.5},
        )

        payload = {
            "operating_point": {"velocity": 15.0, "alpha": 5.0},
            "trim_constraints": [
                {"variable": "alpha", "target": "C", "value": 0.5},
            ],
        }
        resp = client.post(
            f"/aeroplanes/{aeroplane_uuid}/operating-points/avl-trim",
            json=payload,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["converged"] is True
        assert data["aero_coefficients"]["CL"] == 0.5
        assert data["trimmed_deflections"]["elevator"] == -2.5

    @patch("app.services.avl_trim_service.trim_with_avl")
    def test_avl_trim_endpoint_not_found(self, mock_trim, client_and_db):
        from app.core.exceptions import NotFoundError

        client, _ = client_and_db
        aeroplane_uuid = str(uuid.uuid4())

        mock_trim.side_effect = NotFoundError(message="Aeroplane not found")

        payload = {
            "operating_point": {"velocity": 15.0, "alpha": 5.0},
            "trim_constraints": [
                {"variable": "alpha", "target": "C", "value": 0.5},
            ],
        }
        resp = client.post(
            f"/aeroplanes/{aeroplane_uuid}/operating-points/avl-trim",
            json=payload,
        )
        assert resp.status_code == 404

    @patch("app.services.avl_trim_service.trim_with_avl")
    def test_avl_trim_endpoint_validation_error(self, mock_trim, client_and_db):
        from app.core.exceptions import ValidationDomainError

        client, _ = client_and_db
        aeroplane_uuid = str(uuid.uuid4())

        mock_trim.side_effect = ValidationDomainError(
            message="Unknown trim variable 'nonexistent'"
        )

        payload = {
            "operating_point": {"velocity": 15.0, "alpha": 5.0},
            "trim_constraints": [
                {"variable": "elevator", "target": "PM", "value": 0.0},
            ],
        }
        resp = client.post(
            f"/aeroplanes/{aeroplane_uuid}/operating-points/avl-trim",
            json=payload,
        )
        assert resp.status_code == 422
