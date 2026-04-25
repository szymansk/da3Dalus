import logging
import os

from cadquery import Workplane

from cad_designer.airplane.AbstractShapeCreator import AbstractShapeCreator
from cad_designer.airplane.types import CreatorId, ShapeId


class ExportToStlCreator(AbstractShapeCreator):
    """Exports shapes to STL files with configurable tessellation quality.

    Attributes:
        file_path (str): Directory path where STL files will be written.
        shapes_to_export (list[str]): List of shape keys to export.
        tolerance (float): Tessellation chord tolerance in mm.
        angular_tolerance (float): Tessellation angular tolerance in radians.

    Returns:
        {id} (pass-through): Exports files and returns input shapes unchanged.
    """

    suggested_creator_id = "export_stl"

    def __init__(self, creator_id: CreatorId, file_path: str, shapes_to_export: list[ShapeId] = None,
                 tolerance: float = 0.1, angular_tolerance: float = 0.1, loglevel=logging.INFO):
        self.file_path: str = file_path
        self.tolerance = tolerance
        self.angular_tolerance = angular_tolerance
        self.shapes_to_export: list[ShapeId] = shapes_to_export
        super().__init__(creator_id, shapes_of_interest_keys=self.shapes_to_export, loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        shapes_of_interest = shapes_of_interest if shapes_of_interest else kwargs
        logging.info(f"exporting stl model '{', '.join(shapes_of_interest.keys())}' --> '{self.file_path}'")

        from cadquery import exporters
        for name, shape in shapes_of_interest.items():
            step_path = os.path.join(self.file_path, f"{self.identifier}_{name}.stl")
            logging.debug(f"writing model to '{step_path}'")
            exporters.export(shape, step_path,
                             tolerance=self.tolerance, angularTolerance=self.angular_tolerance)

        import gc
        del exporters
        gc.collect()

        return shapes_of_interest
