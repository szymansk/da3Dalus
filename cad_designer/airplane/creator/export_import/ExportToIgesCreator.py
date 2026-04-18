import logging
import os

from OCP.IGESControl import IGESControl_Writer
from OCP.Interface import Interface_Static
from cadquery import Workplane

from cad_designer.airplane.AbstractShapeCreator import AbstractShapeCreator


class ExportToIgesCreator(AbstractShapeCreator):
    """Exports shapes to IGES files in a directory.

    Attributes:
        file_path (str): Directory path where IGES files will be written.
        shapes_to_export (list[str]): List of shape keys to export.
    """

    def __init__(self, creator_id: str, file_path: str, shapes_to_export: list[str] = None, loglevel=logging.INFO):
        self.file_path: str = file_path
        self.shapes_to_export: list[str] = shapes_to_export
        super().__init__(creator_id, shapes_of_interest_keys=self.shapes_to_export, loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        shapes_of_interest = shapes_of_interest if shapes_of_interest else kwargs

        for key, shape in shapes_of_interest.items():
            path = os.path.join(self.file_path, f"{self.identifier}_{key}.igs")
            logging.info(f"exporting iges model '{key}' --> '{path}'")
            self.export_iges_file(shape, path)
        return shapes_of_interest

    @classmethod
    def export_iges_file(cls, shape, filename, author=None, organization=None):
        """ Exports a shape to an IGES file.  """
        # initialize iges writer in BRep mode
        writer = IGESControl_Writer("MM", 1)
        Interface_Static.SetIVal("write.iges.brep.mode", 1)
        # write surfaces with iges 5.3 entities
        Interface_Static.SetIVal("write.convertsurface.mode", 1)
        Interface_Static.SetIVal("write.precision.mode", 1)
        if author is not None:
           Interface_Static.SetCVal("write.iges.header.author", author)
        if organization is not None:
           Interface_Static.SetCVal("write.iges.header.company", organization)
        writer.AddShape(shape.val().wrapped)
        writer.ComputeModel()
        writer.Write(filename)
