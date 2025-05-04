import unittest
import asyncio
import uuid
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.api.v2.endpoints.aeroplane import get_aeroplane_wings
from app import schemas

class TestGetAeroplaneWings(unittest.TestCase):
    def test_get_aeroplane_wings_success(self):
        test_id = uuid.uuid4()
        mock_db = MagicMock()
        # Mock aeroplane with wings attribute
        mock_wing1 = MagicMock()
        mock_wing2 = MagicMock()
        mock_model = MagicMock()
        mock_model.wings = [mock_wing1, mock_wing2]
        mock_db.query.return_value.filter.return_value.first.return_value = mock_model

        # Patch model_validate to return dummy schemas
        dummy_schema1 = schemas.aeroplane.Wing.model_construct(id="w1")
        dummy_schema2 = schemas.aeroplane.Wing.model_construct(id="w2")
        with patch(
            'app.api.v2.endpoints.aeroplane.schemas.aeroplane.Wing.model_validate',
            side_effect=[dummy_schema1, dummy_schema2]
        ) as model_validate:
            result = asyncio.run(get_aeroplane_wings(aeroplane_id=test_id, db=mock_db))

        mock_db.query.assert_called_once()
        model_validate.assert_any_call(mock_wing1, from_attributes=True)
        model_validate.assert_any_call(mock_wing2, from_attributes=True)
        self.assertEqual(result, [dummy_schema1, dummy_schema2])

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