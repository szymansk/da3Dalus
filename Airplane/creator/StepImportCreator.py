import logging

from OCP import TopoDS
from OCP.BRepBuilderAPI import BRepBuilderAPI_Sewing, BRepBuilderAPI_MakeSolid
from OCP.ShapeFix import ShapeFix_Shape
from OCP.TopAbs import TopAbs_SHELL
from OCP.TopExp import TopExp_Explorer
from OCP.TopOpeBRepBuild import TopOpeBRepBuild_ShellToSolid
from cadquery import Workplane, Solid, Shell

from Airplane.AbstractShapeCreator import AbstractShapeCreator
from Airplane.creator.ScaleRotateTranslateCreator import ScaleRotateTranslateCreator


class StepImportCreator(AbstractShapeCreator):
    """
    Import an iges file as a shape.
    """

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
