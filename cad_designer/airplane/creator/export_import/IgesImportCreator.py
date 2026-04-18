import logging

import OCP
import cadquery as cq
from OCP.IGESControl import IGESControl_Reader
from cadquery import Workplane, Shape

from cad_designer.airplane.AbstractShapeCreator import AbstractShapeCreator
from cad_designer.airplane.creator.cad_operations import ScaleRotateTranslateCreator


class IgesImportCreator(AbstractShapeCreator):
    """Imports an IGES file as a shape with optional transform.

    Attributes:
        iges_file (str): Path to the IGES file to import.
        trans_x (float): Translation along X axis in mm.
        trans_y (float): Translation along Y axis in mm.
        trans_z (float): Translation along Z axis in mm.
        rot_x (float): Rotation around X axis in degrees.
        rot_y (float): Rotation around Y axis in degrees.
        rot_z (float): Rotation around Z axis in degrees.
        scale (float): Uniform scale factor applied before per-axis scaling.
        scale_x (float): Scale factor along X axis.
        scale_y (float): Scale factor along Y axis.
        scale_z (float): Scale factor along Z axis.

    Returns:
        {id} (Workplane): Imported IGES geometry with applied transforms.
    """

    suggested_creator_id = "import_iges"

    def __init__(self, creator_id: str, iges_file: str, trans_x: float = .0, trans_y: float = .0, trans_z: float = .0,
                 rot_x: float = .0, rot_y: float = .0, rot_z: float = .0, scale: float = 1.0, scale_x=1.0, scale_y=1.0,
                 scale_z=1.0, loglevel=logging.INFO):
        self.iges_file = iges_file
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

        super().__init__(creator_id, shapes_of_interest_keys=None, loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        logging.info(f"importing iges model '{self.iges_file}' --> '{self.identifier}'")

        shape = IgesImportCreator.iges_importer(self.iges_file)
        trans_shape = ScaleRotateTranslateCreator.transform_by(shape, rot_x=self.rot_x, rot_y=self.rot_y,
                                                               rot_z=self.rot_z, trans_x=self.trans_x,
                                                               trans_y=self.trans_y, trans_z=self.trans_z,
                                                               scale_x=self.scale_x, scale_y=self.scale_y,
                                                               scale_z=self.scale_z)

        return {self.identifier: trans_shape}

    @classmethod
    def iges_importer(cls, filename) -> Workplane:
        """Imports a IGES file as a new CQ Workplane object."""
        reader = IGESControl_Reader()
        # with suppress_stdout_stderr():
        read_status = reader.ReadFile(filename)
        if read_status != OCP.IFSelect.IFSelect_RetDone:
            raise ValueError("IGES file %s could not be loaded" % (filename))
        reader.TransferRoots()
        occ_shapes = []
        for i in range(reader.NbShapes()):
            occ_shapes.append(reader.Shape(i + 1))
        solids = []
        for shape in occ_shapes:
            solids.append(Shape.cast(shape))

        return cq.Workplane("XY").newObject(solids)
