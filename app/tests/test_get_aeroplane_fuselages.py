import unittest
import asyncio
import uuid
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from app.api.v2.endpoints.aeroplane.fuselages import get_aeroplane_fuselages
from app.core.exceptions import InternalError, NotFoundError


class TestGetAeroplaneFuselages(unittest.TestCase):
    def test_get_aeroplane_fuselages_success(self):
        test_id = uuid.uuid4()
        mock_db = MagicMock()

        with patch(
            'app.services.fuselage_service.list_fuselage_names',
            return_value=["fuselage1", "fuselage2"],
        ) as mock_list:
            result = asyncio.run(get_aeroplane_fuselages(aeroplane_id=test_id, db=mock_db))

        mock_list.assert_called_once_with(mock_db, test_id)
        self.assertEqual(result, ["fuselage1", "fuselage2"])

    def test_get_aeroplane_fuselages_not_found(self):
        test_id = uuid.uuid4()
        mock_db = MagicMock()

        with patch(
            'app.services.fuselage_service.list_fuselage_names',
            side_effect=NotFoundError(message="Aeroplane not found"),
        ):
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(get_aeroplane_fuselages(aeroplane_id=test_id, db=mock_db))

            self.assertEqual(ctx.exception.status_code, 404)
            self.assertIn("not found", ctx.exception.detail.lower())

    def test_get_aeroplane_fuselages_db_error(self):
        test_id = uuid.uuid4()
        mock_db = MagicMock()

        with patch(
            'app.services.fuselage_service.list_fuselage_names',
            side_effect=InternalError(message="Database error: DB down"),
        ):
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(get_aeroplane_fuselages(aeroplane_id=test_id, db=mock_db))

            self.assertEqual(ctx.exception.status_code, 500)
            self.assertIn("Database error", ctx.exception.detail)

    def test_get_aeroplane_fuselages_unexpected_error(self):
        test_id = uuid.uuid4()
        mock_db = MagicMock()

        with patch(
            'app.services.fuselage_service.list_fuselage_names',
            side_effect=InternalError(message="Unexpected error: oops"),
        ):
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(get_aeroplane_fuselages(aeroplane_id=test_id, db=mock_db))

            self.assertEqual(ctx.exception.status_code, 500)
            self.assertIn("Unexpected error", ctx.exception.detail)


if __name__ == "__main__":
    unittest.main()
