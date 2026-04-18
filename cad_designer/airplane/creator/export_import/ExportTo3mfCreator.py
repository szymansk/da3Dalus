import logging
import os

from cadquery import Workplane

from cad_designer.airplane.AbstractShapeCreator import AbstractShapeCreator


class ExportTo3mfCreator(AbstractShapeCreator):
    """Exports shapes to 3MF files with configurable tessellation quality.

    Attributes:
        file_path (str): Directory path where 3MF files will be written.
        shapes_to_export (list[str]): List of shape keys to export.
        tolerance (float): Tessellation chord tolerance in mm.
        angular_tolerance (float): Tessellation angular tolerance in radians.
    """

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
        shapes_of_interest = shapes_of_interest if shapes_of_interest else kwargs

        logging.info(f"converting shapes '{', '.join(shapes_of_interest.keys())}' to .3mf")

        from cadquery import exporters
        #ass = cq.Assembly()
        for name, shape in shapes_of_interest.items():
            step_path = os.path.join(self.file_path, f"{self.identifier}_{name}.3mf")
            logging.debug(f"writing model to '{step_path}'")
            exporters.export(shape, step_path,
                             tolerance=self.tolerance, angularTolerance=self.angular_tolerance)
            #ass.add(shape)

        import gc
        del exporters
        gc.collect()

        return shapes_of_interest
