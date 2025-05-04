import unittest
import asyncio
import uuid
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.api.v2.endpoints.aeroplane import get_aeroplane
from app import schemas

class TestGetAeroplane(unittest.TestCase):
    def test_get_aeroplane_success(self):
        test_id = uuid.uuid4()
        mock_db = MagicMock()
        # mock the ORM model instance
        mock_model = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_model

        # patch model_validate to return a dummy schema
        mock_schema = schemas.aeroplane.Aeroplane.model_construct(uuid=test_id, name="Test")
        with patch(
            'app.api.v2.endpoints.aeroplane.schemas.aeroplane.Aeroplane.model_validate',
            return_value=mock_schema
        ) as model_validate:
            result = asyncio.run(get_aeroplane(aeroplane_id=test_id, db=mock_db))

        # assertions
        mock_db.query.assert_called_once()           # we queried the model
        model_validate.assert_called_once_with(mock_model, from_attributes=True) # we converted via model_validate
        self.assertIs(result, mock_schema)           # returned exactly our schema

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
        # simulate SQLAlchemy failure at query
        mock_db.query.side_effect = SQLAlchemyError("DB is down")

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(get_aeroplane(aeroplane_id=test_id, db=mock_db))

        self.assertEqual(ctx.exception.status_code, 500)
        self.assertIn("Database error", ctx.exception.detail)

    def test_get_aeroplane_unexpected_error(self):
        test_id = uuid.uuid4()
        mock_db = MagicMock()
        # simulate some other exception in filter()
        mock_db.query.return_value.filter.side_effect = Exception("whoops")

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(get_aeroplane(aeroplane_id=test_id, db=mock_db))

        self.assertEqual(ctx.exception.status_code, 500)
        self.assertIn("Unexpected error", ctx.exception.detail)

if __name__ == "__main__":
    unittest.main()