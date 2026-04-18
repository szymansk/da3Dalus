import logging
from pathlib import Path

from cadquery import Workplane

from cad_designer.airplane.AbstractShapeCreator import AbstractShapeCreator
from cad_designer.airplane.creator.export_import.IgesImportCreator import IgesImportCreator
from cad_designer.airplane.aircraft_topology.components.ServoInformation import ServoInformation
from cad_designer.airplane.creator.export_import import StepImportCreator
from cad_designer.airplane.creator.cad_operations import ScaleRotateTranslateCreator


class ServoImporterCreator(AbstractShapeCreator):
    """Imports servo geometry files and positions them based on servo information.

    Attributes:
        servo_feature (str): File path to the servo feature geometry.
        servo_stamp (str): File path to the servo stamp geometry.
        servo_filling (str): File path to the servo filling geometry.
        servo_model (str): File path to the servo 3D model.
        servo_idx (int): Index of the servo in the servo information dictionary.
        reverse_model (bool): Whether to reverse the servo model orientation.
        mirror_model_by_plane (str): Mirror plane: xy, xz, yz, or empty for none.

    Returns:
        {id}.stamp (Workplane): Servo stamp geometry for cutout.
        {id}.filling (Workplane): Servo filling geometry.
        {id}.feature (Workplane): Servo feature geometry for slot.
        {id}.model (Workplane): Full servo 3D model.
    """

    suggested_creator_id = "servo[{servo_idx}]"
    def __init__(self, creator_id: str, servo_feature: str, servo_stamp: str, servo_filling: str, servo_model: str,
                 servo_idx: int, reverse_model=False, servo_information: dict[int, ServoInformation] = None,
                 mirror_model_by_plane="", loglevel=logging.INFO):
        self.mirror_model_by_plane = mirror_model_by_plane
        self.reverse_model = reverse_model
        self.servo_idx = servo_idx
        self.servo_model = servo_model
        self._servo_information = servo_information
        self.servo_filling = servo_filling
        self.servo_stamp = servo_stamp
        self.servo_feature = servo_feature
        super().__init__(creator_id, shapes_of_interest_keys=[], loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        logging.info(f"importing servo model '{self.identifier}' --> '{self.identifier}.stamp, "
                     f"{self.identifier}.filling, {self.identifier}.feature, {self.identifier}.model'")
        servo = self._servo_information[self.servo_idx]
        shapes: list[Workplane] = []
        for file in [self.servo_stamp, self.servo_filling, self.servo_feature]:
            self.import_servo_shape(file, shapes, servo)
        self.import_servo_shape(self.servo_model, shapes, servo, mirroring=self.mirror_model_by_plane)
        dict = {f"{self.identifier}.stamp": shapes[0],
                f"{self.identifier}.filling": shapes[1],
                f"{self.identifier}.feature": shapes[2],
                f"{self.identifier}.model": shapes[3]}
        for k, v in dict.items():
            if v is not None:
                v.display(name=k, severity=logging.DEBUG)

        return dict

    def import_servo_shape(self, file, shapes, servo, mirroring=""):
        if file is None:
            shapes.append(None)
        else:
            if Path(file).suffix.lower() in [".iges", ".igs"]:
                shapes.append(IgesImportCreator.iges_importer(file))
            elif Path(file).suffix.lower() in [".step", ".stp"]:
                shapes.append(StepImportCreator.step_importer(file))
            else:
                logging.fatal(f"cannot load file '{file}'. suffix unknown!")

            shapes[-1] = ScaleRotateTranslateCreator.transform_by(shapes[-1], scale=1, rot_x=servo.rot_x,
                                                                  rot_y=servo.rot_y, rot_z=servo.rot_z,
                                                                  trans_x=servo.trans_x, trans_y=servo.trans_y,
                                                                  trans_z=servo.trans_z,
                                                                  mirroring=mirroring)
