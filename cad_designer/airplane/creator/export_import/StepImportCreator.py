import logging

from cadquery import Workplane

from cad_designer.airplane.AbstractShapeCreator import AbstractShapeCreator
from cad_designer.airplane.creator.cad_operations import ScaleRotateTranslateCreator


class StepImportCreator(AbstractShapeCreator):
    """Imports a STEP file as a shape with optional transform.

    Attributes:
        step_file (str): Path to the STEP file to import.
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
        {id} (Workplane): Imported STEP geometry with applied transforms.
    """

    suggested_creator_id = "import_step"

    def __init__(self, creator_id: str, step_file: str,
                 trans_x: float = .0,
                 trans_y: float = .0,
                 trans_z: float = .0,
                 rot_x: float = .0,
                 rot_y: float = .0,
                 rot_z: float = .0,
                 scale: float = 1.0,
                 scale_x=1.0,
                 scale_y=1.0,
                 scale_z=1.0, loglevel=logging.INFO
                 ):
        self.step_file = step_file
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
        logging.info(f"importing step model '{self.step_file}' --> '{self.identifier}'")

        workplane = StepImportCreator.step_importer(self.step_file)
        trans_shape = ScaleRotateTranslateCreator.transform_by(workplane, scale=self.scale,
                                                               rot_x=self.rot_x, rot_y=self.rot_y,
                                                               rot_z=self.rot_z, trans_x=self.trans_x,
                                                               trans_y=self.trans_y, trans_z=self.trans_z,
                                                               scale_x=self.scale_x, scale_y=self.scale_y,
                                                               scale_z=self.scale_z)
        trans_shape.display(name=self.identifier,severity=logging.DEBUG)
        return {self.identifier: trans_shape}

    @classmethod
    def step_importer(cls, path_) -> Workplane:
        from cadquery import importers
        shapes = importers.importStep(path_)
        return shapes
