import unittest
import asyncio
import uuid
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.api.v2.endpoints.aeroplane.fuselages import (
    create_aeroplane_fuselage,
    update_aeroplane_fuselage,
    get_aeroplane_fuselage,
    delete_aeroplane_fuselage,
)
from app.models.aeroplanemodel import FuselageModel
from app import schemas

class TestAeroplaneFuselageEndpoints(unittest.TestCase):
    def setUp(self):
        self.test_plane_id = uuid.uuid4()
        self.test_fuselage_name = "this is a test fuselage"

    def test_create_fuselage_success(self):
        mock_db = MagicMock()
        plane = MagicMock()
        plane.fuselages = []
        mock_db.query.return_value.filter.return_value.first.return_value = plane

        request_schema = schemas.FuselageSchema.model_construct(name=str(self.test_fuselage_name))

        with patch('app.models.aeroplanemodel.FuselageModel.from_dict', autospec=True) as from_dict:
            # FuselageModel.from_dict returns an instance
            fuselage_instance = MagicMock(name=str(self.test_fuselage_name))
            from_dict.return_value = fuselage_instance
            result = asyncio.run(
                create_aeroplane_fuselage(
                    aeroplane_id=self.test_plane_id,
                    fuselage_name=self.test_fuselage_name,
                    request=request_schema,
                    db=mock_db
                )
            )
            # Ensure from_dict was called with the correct parameters
            from_dict.assert_called_once_with(name=self.test_fuselage_name, data=request_schema.model_dump())

    def test_update_fuselage_not_found_plane(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(
                update_aeroplane_fuselage(
                    aeroplane_id=self.test_plane_id,
                    fuselage_name=self.test_fuselage_name,
                    request=schemas.FuselageSchema.model_construct(name=str(self.test_fuselage_name)),
                    db=mock_db
                )
            )
        self.assertEqual(ctx.exception.status_code, 404)

    def test_get_fuselage_success(self):
        mock_db = MagicMock()
        # Simulate plane with a fuselage
        fuselage_model = MagicMock()
        fuselage_model.name = self.test_fuselage_name
        fuselage_model.x_secs = [MagicMock(), MagicMock()]
        plane = MagicMock()
        plane.fuselages = [fuselage_model]
        mock_db.query.return_value.filter.return_value.first.return_value = plane

        schema = schemas.FuselageSchema.model_construct(name=str(self.test_fuselage_name), x_secs=[{'a':1}, {'b':2}])
        with patch('app.schemas.FuselageSchema.model_validate', return_value=schema) as validate:
            result = asyncio.run(
                get_aeroplane_fuselage(
                    aeroplane_id=self.test_plane_id,
                    fuselage_name=self.test_fuselage_name,
                    db=mock_db
                )
            )

        validate.assert_called_once_with(fuselage_model, from_attributes=True)
        self.assertEqual(result, schema)

    def test_delete_fuselage_db_error(self):
        mock_db = MagicMock()
        mock_db.query.side_effect = SQLAlchemyError("fail")

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(
                delete_aeroplane_fuselage(
                    aeroplane_id=self.test_plane_id,
                    fuselage_name=self.test_fuselage_name,
                    db=mock_db
                )
            )
        self.assertEqual(ctx.exception.status_code, 500)

    def test_delete_fuselage_success(self):
        mock_db = MagicMock()
        # Simulate plane with a fuselage
        fuselage_model = MagicMock()
        fuselage_model.name = self.test_fuselage_name
        plane = MagicMock()
        plane.fuselages = [fuselage_model]
        mock_db.query.return_value.filter.return_value.first.return_value = plane
        
        # Context manager for transaction
        begin_cm = mock_db.begin.return_value
        begin_cm.__enter__.return_value = None
        
        result = asyncio.run(
            delete_aeroplane_fuselage(
                aeroplane_id=self.test_plane_id,
                fuselage_name=self.test_fuselage_name,
                db=mock_db
            )
        )
        
        mock_db.query.assert_called_once()
        mock_db.delete.assert_called_once_with(fuselage_model)
        # Ensure transaction was entered
        begin_cm.__enter__.assert_called_once()
        self.assertIsNone(result)

if __name__ == "__main__":
    unittest.main()