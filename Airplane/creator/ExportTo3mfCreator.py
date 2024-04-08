import logging
import os

import cadquery as cq
from cadquery import Workplane

from Airplane.AbstractShapeCreator import AbstractShapeCreator


class ExportTo3mfCreator(AbstractShapeCreator):
    def __init__(self, creator_id: str, file_path: str, shapes_to_export: list[str],
                 tolerance: float = 0.1, angular_tolerance: float = 0.1, loglevel=logging.INFO):
        self.file_path: str = file_path
        self.tolerance = tolerance
        self.angular_tolerance = angular_tolerance
        self.shapes_to_export: list[str] = shapes_to_export \
            if shapes_to_export is not None else [None]
        super().__init__(creator_id, shapes_of_interest_keys=self.shapes_to_export, loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        logging.info(f"converting shapes '{', '.join(shapes_of_interest.keys())}' to .3mf")

        from cadquery import exporters
        ass = cq.Assembly()
        for name, shape in shapes_of_interest.items():
            step_path = os.path.join(self.file_path, f"{self.identifier}_{name}.3mf")
            logging.debug(f"writing model to '{step_path}'")
            exporters.export(shape, step_path,
                             tolerance=self.tolerance, angularTolerance=self.angular_tolerance)
            ass.add(shape)

        #step_path = os.path.join(self.file_path, f"{self.identifier}.3mf", exporters.ExportTypes.STEP)
        #exporters.assembly.exportAssembly(ass, step_path,
        #                 tolerance=self.tolerance, angularTolerance=self.angular_tolerance)
        #logging.debug(f"writing model to '{step_path}'")

        return shapes_of_interest
