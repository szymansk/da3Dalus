import unittest
import asyncio
import uuid
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.api.v2.endpoints.aeroplane.fuselages import get_aeroplane_fuselages
from app import schemas

class TestGetAeroplaneFuselages(unittest.TestCase):
    def test_get_aeroplane_fuselages_success(self):
        test_id = uuid.uuid4()
        mock_db = MagicMock()
        # Mock aeroplane with fuselages attribute
        mock_fuselage1 = MagicMock()
        mock_fuselage1.name = "fuselage1"
        mock_fuselage2 = MagicMock()
        mock_fuselage2.name = "fuselage2"
        mock_model = MagicMock()
        mock_model.fuselages = [mock_fuselage1, mock_fuselage2]
        mock_db.query.return_value.filter.return_value.first.return_value = mock_model

        result = asyncio.run(get_aeroplane_fuselages(aeroplane_id=test_id, db=mock_db))

        mock_db.query.assert_called_once()
        # The function returns a list of fuselage names
        self.assertEqual(result, ["fuselage1", "fuselage2"])

    def test_get_aeroplane_fuselages_not_found(self):
        test_id = uuid.uuid4()
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(get_aeroplane_fuselages(aeroplane_id=test_id, db=mock_db))

        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("not found", ctx.exception.detail.lower())

    def test_get_aeroplane_fuselages_db_error(self):
        test_id = uuid.uuid4()
        mock_db = MagicMock()
        mock_db.query.side_effect = SQLAlchemyError("DB down")

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(get_aeroplane_fuselages(aeroplane_id=test_id, db=mock_db))

        self.assertEqual(ctx.exception.status_code, 500)
        self.assertIn("Database error", ctx.exception.detail)

    def test_get_aeroplane_fuselages_unexpected_error(self):
        test_id = uuid.uuid4()
        mock_db = MagicMock()
        # simulate unexpected error fetching fuselages via property
        class DummyPlane:
            @property
            def fuselages(self):
                raise Exception("oops")
        mock_model = DummyPlane()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_model

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(get_aeroplane_fuselages(aeroplane_id=test_id, db=mock_db))

        self.assertEqual(ctx.exception.status_code, 500)
        self.assertIn("Unexpected error", ctx.exception.detail)

if __name__ == "__main__":
    unittest.main()