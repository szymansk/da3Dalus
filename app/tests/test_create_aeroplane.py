import unittest
from unittest.mock import patch, MagicMock
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException
import uuid
import asyncio

from app.api.v2.endpoints.aeroplane.base import create_aeroplane
from app.models.aeroplanemodel import AeroplaneModel

class TestCreateAeroplane(unittest.TestCase):
    def test_create_aeroplane_success(self):
        # Setup mock
        mock_db = MagicMock()
        begin_cm = mock_db.begin.return_value
        begin_cm.__enter__.return_value = None

        # Create a mock aeroplane with a UUID
        mock_uuid = uuid.uuid4()
        mock_aeroplane = MagicMock()
        mock_aeroplane.uuid = mock_uuid

        # Setup the mock to return our mock aeroplane when AeroplaneModel is created
        with patch('app.api.v2.endpoints.aeroplane.base.AeroplaneModel', return_value=mock_aeroplane):
            result = asyncio.run(create_aeroplane(name="Test Aeroplane", db=mock_db))

            # Assertions
            self.assertEqual(result.body, bytes(f'{{"id":"{mock_uuid}"}}', 'utf-8'))
            mock_db.begin.assert_called_once()
            mock_db.add.assert_called_once_with(mock_aeroplane)
            mock_db.flush.assert_called_once()
            mock_db.refresh.assert_called_once_with(mock_aeroplane)

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
        self.assertTrue("Database error" in context.exception.detail)
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
        self.assertTrue("Unexpected error" in context.exception.detail)
        mock_db.begin.assert_called_once()

if __name__ == "__main__":
    unittest.main()
