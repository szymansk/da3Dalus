import logging
import os

import cadquery as cq
from cadquery import Workplane

from cad_designer.airplane.AbstractShapeCreator import AbstractShapeCreator


class ExportToStepCreator(AbstractShapeCreator):
    """Exports shapes to STEP files and a combined assembly in a directory.

    Attributes:
        file_path (str): Directory path where STEP files will be written.
        shapes_to_export (list[str]): List of shape keys to export.

    Returns:
        {id} (pass-through): Exports files and returns input shapes unchanged.
    """

    suggested_creator_id = "export_step"

    def __init__(self, creator_id: str, file_path: str, shapes_to_export: list[str] = None, loglevel=logging.INFO):
        self.file_path: str = file_path
        self.shapes_to_export: list[str] = shapes_to_export
        super().__init__(creator_id, shapes_of_interest_keys=self.shapes_to_export, loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        shapes_of_interest = shapes_of_interest if shapes_of_interest else kwargs
        logging.info(f"exporting step model '{', '.join(shapes_of_interest.keys())}' --> '{self.file_path}'")

        from cadquery import exporters
        ass = cq.Assembly()
        for name, shape in shapes_of_interest.items():
            step_path = os.path.join(self.file_path, f"{self.identifier}_{name}.step")
            exporters.export(shape, step_path)
            ass.add(shape)

        step_path = os.path.join(self.file_path, f"{self.identifier}.step", exporters.ExportTypes.STEP)
        exporters.assembly.exportAssembly(ass, step_path)
        logging.debug(f"writing model to '{step_path}'")

        from OCP.STEPControl import STEPControl_AsIs
        from OCP.IFSelect import IFSelect_RetDone
        step_writer = self._generateStepWriter()
        for name, shape in shapes_of_interest.items():
            # t_shape = ScaleRotateTranslateCreator.transform_by(shape=shape, scale=1000.0)
            if step_writer.Transfer(shape.findSolid().wrapped, STEPControl_AsIs) != IFSelect_RetDone:
                logging.fatal(f"error while exporting '{name}'")
                raise IOError(f"error while exporting '{name}'")

        step_path = os.path.join(self.file_path, f"{self.identifier}.stp")

        aStat = step_writer.Write(step_path)
        if aStat != IFSelect_RetDone:
            logging.error("Step writing error")
            raise IOError("Step writing error")

        return shapes_of_interest

    def _generateStepWriter(self):
        # ===============
        from OCP.STEPControl import STEPControl_Controller, STEPControl_Writer
        _st = STEPControl_Controller()
        step_writer = STEPControl_Writer()
        _dd = step_writer.WS().TransferWriter().FinderProcess()
        return step_writer
