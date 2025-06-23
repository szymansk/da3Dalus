import unittest
import asyncio
import uuid
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.api.v2.endpoints.aeroplane.wings import get_aeroplane_wings
from app import schemas

class TestGetAeroplaneWings(unittest.TestCase):
    def test_get_aeroplane_wings_success(self):
        test_id = uuid.uuid4()
        mock_db = MagicMock()
        # Mock aeroplane with wings attribute
        mock_wing1 = MagicMock()
        mock_wing1.name = "wing1"
        mock_wing2 = MagicMock()
        mock_wing2.name = "wing2"
        mock_model = MagicMock()
        mock_model.wings = [mock_wing1, mock_wing2]
        mock_db.query.return_value.filter.return_value.first.return_value = mock_model

        result = asyncio.run(get_aeroplane_wings(aeroplane_id=test_id, db=mock_db))

        mock_db.query.assert_called_once()
        # The function returns a list of wing names
        self.assertEqual(result, ["wing1", "wing2"])

    def test_get_aeroplane_wings_not_found(self):
        test_id = uuid.uuid4()
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(get_aeroplane_wings(aeroplane_id=test_id, db=mock_db))

        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("not found", ctx.exception.detail.lower())

    def test_get_aeroplane_wings_db_error(self):
        test_id = uuid.uuid4()
        mock_db = MagicMock()
        mock_db.query.side_effect = SQLAlchemyError("DB down")

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(get_aeroplane_wings(aeroplane_id=test_id, db=mock_db))

        self.assertEqual(ctx.exception.status_code, 500)
        self.assertIn("Database error", ctx.exception.detail)

    def test_get_aeroplane_wings_unexpected_error(self):
        test_id = uuid.uuid4()
        mock_db = MagicMock()
        # simulate unexpected error fetching wings via property
        class DummyPlane:
            @property
            def wings(self):
                raise Exception("oops")
        mock_model = DummyPlane()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_model

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(get_aeroplane_wings(aeroplane_id=test_id, db=mock_db))

        self.assertEqual(ctx.exception.status_code, 500)
        self.assertIn("Unexpected error", ctx.exception.detail)

if __name__ == "__main__":
    unittest.main()
