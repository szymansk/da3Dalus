import logging

from cadquery import Workplane

from cad_designer.airplane.AbstractShapeCreator import AbstractShapeCreator
from cad_designer.airplane.creator.export_import.IgesImportCreator import IgesImportCreator
from cad_designer.airplane.aircraft_topology.components.ComponentInformation import ComponentInformation
from cad_designer.airplane.creator.export_import import StepImportCreator
from cad_designer.airplane.creator.cad_operations import ScaleRotateTranslateCreator


class ComponentImporterCreator(AbstractShapeCreator):
    """Imports a component geometry file with positioning from component information.

    Attributes:
        component_idx (str): Identifier of the component in the component information.
        component_file (str): Path to the component geometry file (STEP or IGES).
        mirror_model_by_plane (str): Mirror plane: xy, xz, yz, or empty for none.

    Returns:
        {id} (Workplane): Imported and positioned component geometry.
    """

    def __init__(self,
                 creator_id: str,
                 component_idx: str,
                 component_file: str,
                 mirror_model_by_plane="",
                 component_information: dict[str, ComponentInformation] = None,
                 loglevel=logging.INFO):
        self.component_idx = component_idx
        self._component_information = component_information
        self.component_file = component_file
        self.mirror_model_by_plane = mirror_model_by_plane

        super().__init__(creator_id, shapes_of_interest_keys=[], loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        logging.info(f"importing component '{self.component_idx}' with model '{self.component_file}'"
                     f" --> '{self.identifier}'")
        from pathlib import Path

        component = self._component_information[self.component_idx]
        file = self.component_file
        if Path(file).suffix.lower() in [".iges", ".igs"]:
            shape = IgesImportCreator.iges_importer(file)
        elif Path(file).suffix.lower() in [".step", ".stp"]:
            shape = StepImportCreator.step_importer(file)
        else:
            logging.fatal(f"cannot load file '{file}'. suffix unknown!")
            raise RuntimeError(f"cannot load file '{file}'. suffix unknown!")

        shape = ScaleRotateTranslateCreator.transform_by(shape,
                                                         scale=1,
                                                         rot_x=component.rot_x,
                                                         rot_y=component.rot_y,
                                                         rot_z=component.rot_z,
                                                         trans_x=component.trans_x,
                                                         trans_y=component.trans_y,
                                                         trans_z=component.trans_z,
                                                         mirroring=self.mirror_model_by_plane) \
            .display(self.identifier, logging.DEBUG)

        return {f"{self.identifier}": shape}
