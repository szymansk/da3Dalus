import logging

import cadquery as cq
from cadquery import Workplane

from cad_designer.airplane.AbstractShapeCreator import AbstractShapeCreator
from cad_designer.airplane.types import CreatorId, ShapeId

class ScaleRotateTranslateCreator(AbstractShapeCreator):
    """Applies scale, rotation, and translation transforms to a shape.

    Attributes:
        shape_id (str): Key of the shape to transform.
        scale (float): Uniform scale factor applied before per-axis scaling.
        rot_x (float): Rotation around X axis in degrees.
        rot_y (float): Rotation around Y axis in degrees.
        rot_z (float): Rotation around Z axis in degrees.
        trans_x (float): Translation along X axis in mm.
        trans_y (float): Translation along Y axis in mm.
        trans_z (float): Translation along Z axis in mm.
        scale_x (float): Scale factor along X axis.
        scale_y (float): Scale factor along Y axis.
        scale_z (float): Scale factor along Z axis.
        mirroring (str): Mirror plane: xy, xz, yz, or empty for none.

    Returns:
        {id} (Workplane): Transformed shape after scale, rotation, and translation.
    """

    suggested_creator_id = "transform.{shape_id}"

    def __init__(self, creator_id: CreatorId, shape_id: ShapeId, scale: float = 1.0, rot_x: float = .0, rot_y: float = .0,
                 rot_z: float = .0, trans_x: float = .0, trans_y: float = .0, trans_z: float = .0, scale_x=1.0,
                 scale_y=1.0, scale_z=1.0, mirroring="", loglevel=logging.INFO):
        self.mirroring = mirroring
        self.shape_id = shape_id
        self.trans_x = trans_x
        self.trans_y = trans_y
        self.trans_z = trans_z
        self.rot_x = rot_x
        self.rot_y = rot_y
        self.rot_z = rot_z
        self.scale = scale
        self.scale_x = scale_x
        self.scale_y = scale_y
        self.scale_z = scale_z

        if self.scale != 1.0:
            self.scale_x = self.scale_y = self.scale_z = self.scale

        super().__init__(creator_id, shapes_of_interest_keys=[self.shape_id], loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        shape_list = list(shapes_of_interest.values())
        shape = shape_list[0]
        logging.info(
            f"scale ({self.scale_x}, {self.scale_y}, {self.scale_z}), rotate ({self.rot_x}, {self.rot_y}, {self.rot_z}) "
            f"and translate ({self.trans_x}, {self.trans_y}, {self.trans_z}) '{list(shapes_of_interest.keys())[0]}' "
            f"--> '{self.identifier}'")
        trans_shape = self.transform_by(shape, scale=self.scale, rot_x=self.rot_x, rot_y=self.rot_y, rot_z=self.rot_z,
                                        trans_x=self.trans_x, trans_y=self.trans_y, trans_z=self.trans_z,
                                        mirroring=self.mirroring)
        trans_shape.display(name=self.identifier, severity=logging.DEBUG)

        return {self.identifier: trans_shape}

    @classmethod
    def transform_by(cls, shape: Workplane, scale: float = 1.0, rot_x: float = .0, rot_y: float = .0,
                     rot_z: float = .0, trans_x: float = .0, trans_y: float = .0, trans_z: float = .0, scale_x=1.0,
                     scale_y=1.0, scale_z=1.0, mirroring="") -> Workplane:
        if scale != 1.0:
            logging.debug(f"setting all scale dimensions to factor: {scale}")
            scale_x = scale_y = scale_z = scale

        shape = cq.CQ(shape.findSolid()\
            .scale(scale)\
            .rotate((0,0,0),(1,0,0),rot_x)\
            .rotate((0,0,0),(0,1,0),rot_y)\
            .rotate((0,0,0),(0,0,1),rot_z)\
            .translate((trans_x, trans_y, trans_z)))

        return shape
