import unittest
import asyncio
import uuid
from unittest.mock import MagicMock
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.api.v2.endpoints.aeroplane.base import delete_aeroplane

class TestDeleteAeroplane(unittest.TestCase):
    def test_delete_aeroplane_success(self):
        test_id = uuid.uuid4()
        mock_db = MagicMock()
        # simulate found object
        mock_model = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_model
        # context manager for transaction
        begin_cm = mock_db.begin.return_value
        begin_cm.__enter__.return_value = None

        result = asyncio.run(delete_aeroplane(aeroplane_id=test_id, db=mock_db))
        mock_db.query.assert_called_once()
        mock_db.delete.assert_called_once_with(mock_model)
        # ensure transaction was entered
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
        # found model but delete blows up
        mock_model = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_model
        begin_cm = mock_db.begin.return_value
        begin_cm.__enter__.return_value = None
        mock_db.delete.side_effect = Exception("oops")

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(delete_aeroplane(aeroplane_id=test_id, db=mock_db))

        self.assertEqual(ctx.exception.status_code, 500)
        self.assertIn("Unexpected error", ctx.exception.detail)

if __name__ == "__main__":
    unittest.main()
