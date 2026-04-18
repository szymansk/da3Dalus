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
        st = STEPControl_Controller()
        # st.Init()
        step_writer = STEPControl_Writer()
        dd = step_writer.WS().TransferWriter().FinderProcess()
        # from OCP.Interface_Static import Interface_Static_SetCVal, Interface_Static_SetIVal
        # defines the version of schema used for the output STEP file:
        # 1 or AP214CD (default): AP214, CD version (dated 26 November 1996),
        # 2 or AP214DIS: AP214, DIS version (dated 15 September 1998).
        # 3 or AP203: AP203, possibly with modular extensions (depending on data written to a file).
        # 4 or AP214IS: AP214, IS version (dated 2002)
        # 5 or AP242DIS: AP242, DIS version.
        # Interface_Static_SetCVal("write.step.schema", "AP214CD")
        # 0 (Off) : (default) writes STEP files without assemblies.
        # 1 (On) : writes all shapes in the form of STEP assemblies.
        # 2 (Auto) : writes shapes having a structure of (possibly nested) TopoDS_Compounds in the form of STEP
        #    assemblies, single shapes are written without assembly structures.
        # Interface_Static_SetIVal("write.step.assembly", 0)
        # Interface_Static_SetCVal("write.step.unit", "")
        # Interface_Static_SetIVal("write.precision.mode", 0)
        return step_writer
