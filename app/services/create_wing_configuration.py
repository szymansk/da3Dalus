from airplane.aircraft_topology.components import Servo
from airplane.aircraft_topology.wing import WingConfiguration, TrailingEdgeDevice, Spare
from airplane.aircraft_topology.wing import Airfoil
from app.models.wing import Wing as WingModel
from app.models.wing import Airfoil as AirfoilModel
from app.models.wing import Segment as SegmentModel
from app.models.wing import TrailingEdgeDevice as TrailingEdgeDeviceModel
from app.models.wing import Servo as ServoModel
from app.models.wing import Spare as SpareModel


def create_airfoil(airfoil_model: AirfoilModel) -> Airfoil:
    return Airfoil(**airfoil_model.__dict__.copy())


def create_servo(servo_model: ServoModel) -> Servo:
    return Servo(**servo_model.__dict__.copy())


def create_trailing_edge_device(ted_model: TrailingEdgeDeviceModel) -> TrailingEdgeDevice:
    initialization_dict = ted_model.__dict__.copy()
    initialization_dict['servo'] = create_servo(ted_model.servo)
    return TrailingEdgeDevice(**initialization_dict)


def create_spare(spare_model: SpareModel) -> Spare:
    return Spare(**spare_model.__dict__.copy())

def create_segment(segment_model: SegmentModel) -> dict:
    initialization_dict = segment_model.__dict__.copy()
    initialization_dict['sweepIsAngle'] = False
    initialization_dict['tip_airfoil'] = create_airfoil(segment_model.tip_airfoil)
    initialization_dict['spare_list'] = [create_spare(spare) for spare in segment_model.spare_list],
    initialization_dict['trailing_edge_device'] = create_trailing_edge_device(segment_model.trailing_edge_device)
    return initialization_dict


def create_tip_segment(segment_model: SegmentModel) -> dict:
    initialization_dict = segment_model.__dict__.copy()
    initialization_dict['sweepIsAngle'] = False
    initialization_dict['tip_airfoil'] = create_airfoil(segment_model.tip_airfoil)
    return initialization_dict


def create_wing_configuration(wing_model: WingModel) -> WingConfiguration:
    """ Create a WingConfiguration from a Wing model object
    """
    # creating root segment
    initialization_dict = create_root_segment(wing_model)
    wing_config: WingConfiguration = WingConfiguration(**initialization_dict)

    # creating middle segment
    middle_segments = ( segment for segment in wing_model.segments[1:] if segment.tip_type is None )
    for segment in middle_segments:
        wing_config.add_segment( **create_segment(segment) )

    # creating tip segment
    tip_segments = ( segment for segment in wing_model.segments[1:] if segment.tip_type is not None )
    for segment in tip_segments:
        wing_config.add_tip_segment( **create_tip_segment(segment) )

    return wing_config


def create_root_segment(wing_model: WingModel) -> dict:
    initialization_dict = wing_model.__dict__.copy()
    root_segment: SegmentModel = wing_model.segments[0]

    initialization_dict['nose_pnt'] = (
        wing_model.nose_pnt[0],
        wing_model.nose_pnt[1],
        wing_model.nose_pnt[2]
    )
    initialization_dict['sweepIsAngle'] = False
    initialization_dict['root_airfoil'] = create_airfoil(root_segment.root_airfoil)
    initialization_dict['tip_airfoil'] = create_airfoil(root_segment.tip_airfoil)
    initialization_dict['spare_list'] = [create_spare(spare) for spare in root_segment.spare_list]
    initialization_dict['trailing_edge_device'] = create_trailing_edge_device(root_segment.trailing_edge_device)
    return initialization_dict