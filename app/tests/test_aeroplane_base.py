import unittest
import asyncio
import uuid
from unittest.mock import MagicMock, patch
from fastapi import HTTPException, Response
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime

from app.core.exceptions import NotFoundError, ValidationError
from app.api.v2.endpoints.aeroplane.base import (
    create_aeroplane,
    get_aeroplanes,
    get_aeroplane,
    get_aeroplane_airplane_configuration,
    delete_aeroplane,
    get_aeroplane_total_mass_in_kg,
    create_aeroplane_total_mass_kg,
    GetAeroplaneResponse
)
from app.models.aeroplanemodel import AeroplaneModel
from app.schemas.AeroplaneRequest import AeroplaneMassRequest
from app.schemas.api_responses import CreateAeroplaneResponse, OperationStatusResponse
from app import schemas

class TestCreateAeroplane(unittest.TestCase):
    def test_create_aeroplane_success(self):
        mock_db = MagicMock()
        mock_uuid = uuid.uuid4()
        mock_aeroplane = MagicMock()
        mock_aeroplane.uuid = mock_uuid

        with patch('app.api.v2.endpoints.aeroplane.base.aeroplane_service.create_aeroplane', return_value=mock_aeroplane):
            result = asyncio.run(create_aeroplane(name="Test Aeroplane", db=mock_db))

            self.assertIsInstance(result, CreateAeroplaneResponse)
            self.assertEqual(result.id, str(mock_uuid))

    def test_create_aeroplane_db_error(self):
        # Setup mock
        mock_db = MagicMock()
        begin_cm = mock_db.begin.return_value
        begin_cm.__enter__.side_effect = SQLAlchemyError("Test DB error")

        # Call the function and check for exception
        with self.assertRaises(HTTPException) as context:
            asyncio.run(create_aeroplane(name="Test Aeroplane", db=mock_db))

        # Assertions
        self.assertEqual(context.exception.status_code, 500)
        self.assertIn("Database error", context.exception.detail)
        mock_db.begin.assert_called_once()

    def test_create_aeroplane_unexpected_error(self):
        # Setup mock
        mock_db = MagicMock()
        begin_cm = mock_db.begin.return_value
        begin_cm.__enter__.return_value = None
        mock_db.add.side_effect = Exception("Test unexpected error")

        # Call the function and check for exception
        with self.assertRaises(HTTPException) as context:
            asyncio.run(create_aeroplane(name="Test Aeroplane", db=mock_db))

        # Assertions
        self.assertEqual(context.exception.status_code, 500)
        self.assertIn("Unexpected error", context.exception.detail)
        mock_db.begin.assert_called_once()

class TestGetAeroplanes(unittest.TestCase):
    def test_get_aeroplanes_success(self):
        # Setup mock
        mock_db = MagicMock()

        # Create mock aeroplanes
        mock_aeroplane1 = MagicMock()
        mock_aeroplane1.name = "Test Aeroplane 1"
        mock_aeroplane1.uuid = uuid.uuid4()
        mock_aeroplane1.created_at = datetime.now()
        mock_aeroplane1.updated_at = datetime.now()

        mock_aeroplane2 = MagicMock()
        mock_aeroplane2.name = "Test Aeroplane 2"
        mock_aeroplane2.uuid = uuid.uuid4()
        mock_aeroplane2.created_at = datetime.now()
        mock_aeroplane2.updated_at = datetime.now()

        # Setup the mock to return our mock aeroplanes
        mock_db.query.return_value.order_by.return_value.all.return_value = [mock_aeroplane1, mock_aeroplane2]

        # Call the function
        result = asyncio.run(get_aeroplanes(db=mock_db))

        # Assertions
        self.assertIsInstance(result, GetAeroplaneResponse)
        self.assertEqual(len(result.aeroplanes), 2)
        self.assertEqual(result.aeroplanes[0].name, mock_aeroplane1.name)
        self.assertEqual(result.aeroplanes[0].id, mock_aeroplane1.uuid)
        self.assertEqual(result.aeroplanes[1].name, mock_aeroplane2.name)
        self.assertEqual(result.aeroplanes[1].id, mock_aeroplane2.uuid)
        mock_db.query.assert_called_once_with(AeroplaneModel)
        mock_db.query.return_value.order_by.assert_called_once()
        mock_db.query.return_value.order_by.return_value.all.assert_called_once()

    def test_get_aeroplanes_db_error(self):
        # Setup mock
        mock_db = MagicMock()
        mock_db.query.side_effect = SQLAlchemyError("Test DB error")

        # Call the function and check for exception
        with self.assertRaises(HTTPException) as context:
            asyncio.run(get_aeroplanes(db=mock_db))

        # Assertions
        self.assertEqual(context.exception.status_code, 500)
        self.assertIn("Database error", context.exception.detail)
        mock_db.query.assert_called_once_with(AeroplaneModel)

    def test_get_aeroplanes_unexpected_error(self):
        # Setup mock
        mock_db = MagicMock()
        mock_db.query.return_value.order_by.side_effect = Exception("Test unexpected error")

        # Call the function and check for exception
        with self.assertRaises(HTTPException) as context:
            asyncio.run(get_aeroplanes(db=mock_db))

        # Assertions
        self.assertEqual(context.exception.status_code, 500)
        self.assertIn("Unexpected error", context.exception.detail)
        mock_db.query.assert_called_once_with(AeroplaneModel)

class TestGetAeroplane(unittest.TestCase):
    def test_get_aeroplane_success(self):
        test_id = uuid.uuid4()
        mock_db = MagicMock()

        # Mock the ORM model instance
        mock_model = MagicMock()
        mock_model.wings = []
        mock_model.name = "Test Aeroplane 1"
        mock_model.fuselages = []
        mock_db.query.return_value.filter.return_value.first.return_value = mock_model

        # Mock the schema
        mock_schema = MagicMock()

        # Patch the model_validate method
        with patch('app.schemas.AeroplaneSchema.model_validate', return_value=mock_schema):
            result = asyncio.run(get_aeroplane(aeroplane_id=test_id, db=mock_db))

        # Assertions
        mock_db.query.assert_called_once_with(AeroplaneModel)
        mock_db.query.return_value.filter.assert_called_once()
        self.assertEqual(result.name, mock_model.name)

    def test_get_aeroplane_not_found(self):
        test_id = uuid.uuid4()
        mock_db = MagicMock()

        # .first() returns None → 404
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(get_aeroplane(aeroplane_id=test_id, db=mock_db))

        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("Aeroplane not found", ctx.exception.detail)

    def test_get_aeroplane_db_error(self):
        test_id = uuid.uuid4()
        mock_db = MagicMock()

        # Simulate SQLAlchemy failure at query
        mock_db.query.side_effect = SQLAlchemyError("DB is down")

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(get_aeroplane(aeroplane_id=test_id, db=mock_db))

        self.assertEqual(ctx.exception.status_code, 500)
        self.assertIn("Database error", ctx.exception.detail)

    def test_get_aeroplane_unexpected_error(self):
        test_id = uuid.uuid4()
        mock_db = MagicMock()

        # Simulate some other exception in filter()
        mock_db.query.return_value.filter.side_effect = Exception("whoops")

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(get_aeroplane(aeroplane_id=test_id, db=mock_db))

        self.assertEqual(ctx.exception.status_code, 500)
        self.assertIn("Unexpected error", ctx.exception.detail)

class TestDeleteAeroplane(unittest.TestCase):
    def test_delete_aeroplane_success(self):
        test_id = uuid.uuid4()
        mock_db = MagicMock()

        # Simulate found object
        mock_model = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_model

        # Context manager for transaction
        begin_cm = mock_db.begin.return_value
        begin_cm.__enter__.return_value = None

        result = asyncio.run(delete_aeroplane(aeroplane_id=test_id, db=mock_db))

        mock_db.query.assert_called_once_with(AeroplaneModel)
        mock_db.delete.assert_called_once_with(mock_model)
        # Ensure transaction was entered
        begin_cm.__enter__.assert_called_once()
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.operation, "delete_aeroplane")

    def test_delete_aeroplane_not_found(self):
        test_id = uuid.uuid4()
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(delete_aeroplane(aeroplane_id=test_id, db=mock_db))

        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("Aeroplane not found", ctx.exception.detail)

    def test_delete_aeroplane_db_error(self):
        test_id = uuid.uuid4()
        mock_db = MagicMock()
        mock_db.query.side_effect = SQLAlchemyError("DB down")

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(delete_aeroplane(aeroplane_id=test_id, db=mock_db))

        self.assertEqual(ctx.exception.status_code, 500)
        self.assertIn("Database error", ctx.exception.detail)

    def test_delete_aeroplane_unexpected_error(self):
        test_id = uuid.uuid4()
        mock_db = MagicMock()

        # Found model but delete blows up
        mock_model = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_model
        begin_cm = mock_db.begin.return_value
        begin_cm.__enter__.return_value = None
        mock_db.delete.side_effect = Exception("oops")

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(delete_aeroplane(aeroplane_id=test_id, db=mock_db))

        self.assertEqual(ctx.exception.status_code, 500)
        self.assertIn("Unexpected error", ctx.exception.detail)

class TestGetAeroplaneTotalMass(unittest.TestCase):
    def test_get_aeroplane_total_mass_success(self):
        test_id = uuid.uuid4()
        test_mass = 1000.5
        mock_db = MagicMock()

        # Mock the ORM model instance
        mock_model = MagicMock()
        mock_model.total_mass_kg = test_mass
        mock_db.query.return_value.filter.return_value.first.return_value = mock_model

        result = asyncio.run(get_aeroplane_total_mass_in_kg(aeroplane_id=test_id, db=mock_db))

        # Assertions
        mock_db.query.assert_called_once_with(AeroplaneModel)
        mock_db.query.return_value.filter.assert_called_once()
        self.assertEqual(result.total_mass_kg, test_mass)

    def test_get_aeroplane_total_mass_not_found(self):
        test_id = uuid.uuid4()
        mock_db = MagicMock()

        # .first() returns None → 404
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(get_aeroplane_total_mass_in_kg(aeroplane_id=test_id, db=mock_db))

        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("Aeroplane not found", ctx.exception.detail)

    def test_get_aeroplane_total_mass_not_set(self):
        test_id = uuid.uuid4()
        mock_db = MagicMock()

        # Mock the ORM model instance with None mass
        mock_model = MagicMock()
        mock_model.total_mass_kg = None
        mock_db.query.return_value.filter.return_value.first.return_value = mock_model

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(get_aeroplane_total_mass_in_kg(aeroplane_id=test_id, db=mock_db))

        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("Aeroplane weight not set", ctx.exception.detail)

    def test_get_aeroplane_total_mass_db_error(self):
        test_id = uuid.uuid4()
        mock_db = MagicMock()

        # Simulate SQLAlchemy failure at query
        mock_db.query.side_effect = SQLAlchemyError("DB is down")

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(get_aeroplane_total_mass_in_kg(aeroplane_id=test_id, db=mock_db))

        self.assertEqual(ctx.exception.status_code, 500)
        self.assertIn("Database error", ctx.exception.detail)

    def test_get_aeroplane_total_mass_unexpected_error(self):
        test_id = uuid.uuid4()
        mock_db = MagicMock()

        # Simulate some other exception in filter()
        mock_db.query.return_value.filter.side_effect = Exception("whoops")

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(get_aeroplane_total_mass_in_kg(aeroplane_id=test_id, db=mock_db))

        self.assertEqual(ctx.exception.status_code, 500)
        self.assertIn("Unexpected error", ctx.exception.detail)

class TestCreateAeroplaneTotalMass(unittest.TestCase):
    def test_create_aeroplane_total_mass_new_success(self):
        test_id = uuid.uuid4()
        test_mass = 1000.5
        mock_db = MagicMock()

        # Mock the ORM model instance
        mock_model = MagicMock()
        mock_model.total_mass_kg = None
        mock_db.query.return_value.filter.return_value.first.return_value = mock_model

        # Context manager for transaction
        begin_cm = mock_db.begin.return_value
        begin_cm.__enter__.return_value = None
        response = Response()

        # Create request body
        mass_request = AeroplaneMassRequest(total_mass_kg=test_mass)

        result = asyncio.run(create_aeroplane_total_mass_kg(
            aeroplane_id=test_id, 
            total_mass_kg=mass_request, 
            response=response,
            db=mock_db
        ))

        # Assertions
        mock_db.query.assert_called_once_with(AeroplaneModel)
        mock_db.query.return_value.filter.assert_called_once()
        self.assertEqual(mock_model.total_mass_kg, test_mass)
        self.assertIsInstance(result, OperationStatusResponse)
        self.assertEqual(result.status, "created")
        self.assertEqual(result.operation, "set_aeroplane_total_mass")
        self.assertEqual(response.status_code, 201)

    def test_create_aeroplane_total_mass_update_success(self):
        test_id = uuid.uuid4()
        old_mass = 900.0
        new_mass = 1000.5
        mock_db = MagicMock()

        # Mock the ORM model instance
        mock_model = MagicMock()
        mock_model.total_mass_kg = old_mass
        mock_db.query.return_value.filter.return_value.first.return_value = mock_model

        # Context manager for transaction
        begin_cm = mock_db.begin.return_value
        begin_cm.__enter__.return_value = None
        response = Response()

        # Create request body
        mass_request = AeroplaneMassRequest(total_mass_kg=new_mass)

        result = asyncio.run(create_aeroplane_total_mass_kg(
            aeroplane_id=test_id, 
            total_mass_kg=mass_request, 
            response=response,
            db=mock_db
        ))

        # Assertions
        mock_db.query.assert_called_once_with(AeroplaneModel)
        mock_db.query.return_value.filter.assert_called_once()
        self.assertEqual(mock_model.total_mass_kg, new_mass)
        self.assertIsInstance(result, OperationStatusResponse)
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.operation, "set_aeroplane_total_mass")
        self.assertEqual(response.status_code, 200)

    def test_create_aeroplane_total_mass_not_found(self):
        test_id = uuid.uuid4()
        test_mass = 1000.5
        mock_db = MagicMock()

        # .first() returns None → 404
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # Create request body
        mass_request = AeroplaneMassRequest(total_mass_kg=test_mass)

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(create_aeroplane_total_mass_kg(
                aeroplane_id=test_id, 
                total_mass_kg=mass_request, 
                db=mock_db
            ))

        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("Aeroplane not found", ctx.exception.detail)

    def test_create_aeroplane_total_mass_db_error(self):
        test_id = uuid.uuid4()
        test_mass = 1000.5
        mock_db = MagicMock()

        # Simulate SQLAlchemy failure at query
        mock_db.query.side_effect = SQLAlchemyError("DB is down")

        # Create request body
        mass_request = AeroplaneMassRequest(total_mass_kg=test_mass)

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(create_aeroplane_total_mass_kg(
                aeroplane_id=test_id, 
                total_mass_kg=mass_request, 
                db=mock_db
            ))

        self.assertEqual(ctx.exception.status_code, 500)
        self.assertIn("Database error", ctx.exception.detail)

    def test_create_aeroplane_total_mass_unexpected_error(self):
        test_id = uuid.uuid4()
        test_mass = 1000.5
        mock_db = MagicMock()

        # Simulate some other exception in filter()
        mock_db.query.return_value.filter.side_effect = Exception("whoops")

        # Create request body
        mass_request = AeroplaneMassRequest(total_mass_kg=test_mass)

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(create_aeroplane_total_mass_kg(
                aeroplane_id=test_id, 
                total_mass_kg=mass_request, 
                db=mock_db
            ))

        self.assertEqual(ctx.exception.status_code, 500)
        self.assertIn("Unexpected error", ctx.exception.detail)


class TestGetAirplaneConfiguration(unittest.TestCase):
    def test_get_airplane_configuration_success(self):
        test_id = uuid.uuid4()
        mock_db = MagicMock()
        mock_payload = {
            "name": "Test Plane",
            "total_mass_kg": 2.5,
            "wings": [
                {
                    "nose_pnt": [0, 0, 0],
                    "segments": [],
                    "parameters": "relative",
                    "symmetric": True,
                }
            ],
            "fuselages": None,
        }

        with patch(
            "app.api.v2.endpoints.aeroplane.base.aeroplane_service.get_aeroplane_airplane_configuration",
            return_value=mock_payload,
        ) as get_config:
            result = asyncio.run(get_aeroplane_airplane_configuration(aeroplane_id=test_id, db=mock_db))

        get_config.assert_called_once_with(mock_db, test_id)
        self.assertEqual(result.name, "Test Plane")
        self.assertEqual(result.total_mass_kg, 2.5)
        self.assertEqual(len(result.wings), 1)

    def test_get_airplane_configuration_not_found(self):
        test_id = uuid.uuid4()
        mock_db = MagicMock()

        with patch(
            "app.api.v2.endpoints.aeroplane.base.aeroplane_service.get_aeroplane_airplane_configuration",
            side_effect=NotFoundError(message="Aeroplane not found"),
        ):
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(get_aeroplane_airplane_configuration(aeroplane_id=test_id, db=mock_db))

        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("Aeroplane not found", ctx.exception.detail)

    def test_get_airplane_configuration_validation_error(self):
        test_id = uuid.uuid4()
        mock_db = MagicMock()

        with patch(
            "app.api.v2.endpoints.aeroplane.base.aeroplane_service.get_aeroplane_airplane_configuration",
            side_effect=ValidationError(message="mass missing"),
        ):
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(get_aeroplane_airplane_configuration(aeroplane_id=test_id, db=mock_db))

        self.assertEqual(ctx.exception.status_code, 422)
        self.assertIn("mass missing", ctx.exception.detail)

if __name__ == "__main__":
    unittest.main()
