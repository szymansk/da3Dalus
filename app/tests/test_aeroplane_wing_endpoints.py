import unittest
import asyncio
import uuid
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.api.v2.endpoints.aeroplane import (
    create_aeroplane_wing,
    update_aeroplane_wing,
    get_aeroplane_wing,
    delete_aeroplane_wing,
)
from app.models.aeroplanemodel import WingModel
from app import schemas

class TestAeroplaneWingEndpoints(unittest.TestCase):
    def setUp(self):
        self.test_plane_id = uuid.uuid4()
        self.test_wing_name = "this is a test wing"

    def test_create_wing_success(self):
        mock_db = MagicMock()
        plane = MagicMock()
        plane.wings = []
        mock_db.query.return_value.filter.return_value.first.return_value = plane

        request_schema = schemas.aeroplane.AsbWingSchema.model_construct(name=str(self.test_wing_name))

        with patch('app.api.v2.endpoints.aeroplane.Wing', autospec=True) as WingModel, \
             patch('app.api.v2.endpoints.aeroplane.schemas.aeroplane.Wing.model_validate', return_value=request_schema) as validate:
            # WingModel(uuid, **data) returns an instance
            wing_instance = MagicMock(name=str(self.test_wing_name))
            WingModel.return_value = wing_instance
            result = asyncio.run(
                create_aeroplane_wing(
                    aeroplane_id=self.test_plane_id,
                    wing_name=self.test_wing_name,
                    request=request_schema,
                    db=mock_db
                )
            )
            # Ensure we convert via model_validate
            validate.assert_called_once_with(wing_instance, from_attributes=True)

    def test_update_wing_not_found_plane(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(
                update_aeroplane_wing(
                    aeroplane_id=self.test_plane_id,
                    wing_name=self.test_wing_name,
                    request=schemas.aeroplane.AsbWingSchema.model_construct(name=str(self.test_wing_name)),
                    db=mock_db
                )
            )
        self.assertEqual(ctx.exception.status_code, 404)

    def test_get_wing_success(self):
        mock_db = MagicMock()
        # Simulate plane with a wing
        wing_model = MagicMock(name=self.test_wing_name, x_secs=[MagicMock(), MagicMock()])
        plane = MagicMock()
        plane.wings = [wing_model]
        mock_db.query.return_value.filter.return_value.first.return_value = plane

        schema = schemas.aeroplane.AsbWingSchema.model_construct(name=str(self.test_wing_name), x_secs=[{'a':1}, {'b':2}])
        with patch('app.api.v2.endpoints.aeroplane.schemas.aeroplane.Wing.model_validate', return_value=schema) as validate:
            result = asyncio.run(
                get_aeroplane_wing(
                    aeroplane_id=self.test_plane_id,
                    wing_name=self.test_wing_name,
                    db=mock_db
                )
            )

        validate.assert_called_once_with(wing_model, from_attributes=True)
        self.assertEqual(result, schema)

    def test_delete_wing_db_error(self):
        mock_db = MagicMock()
        mock_db.query.side_effect = SQLAlchemyError("fail")

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(
                delete_aeroplane_wing(
                    aeroplane_id=self.test_plane_id,
                    wing_name=self.test_wing_name,
                    db=mock_db
                )
            )
        self.assertEqual(ctx.exception.status_code, 500)

if __name__ == "__main__":
    unittest.main()