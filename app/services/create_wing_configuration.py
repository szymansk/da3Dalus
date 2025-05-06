from cad_designer.airplane.aircraft_topology.components import Servo
from cad_designer.airplane.aircraft_topology.wing import WingConfiguration, TrailingEdgeDevice, Spare
from cad_designer.airplane.aircraft_topology.wing import Airfoil
from app.schemas.wing import Wing as WingModel
from app.schemas.wing import Airfoil as AirfoilModel
from app.schemas.wing import Segment as SegmentModel
from app.schemas.wing import TrailingEdgeDevice as TrailingEdgeDeviceModel
from app.schemas.wing import Servo as ServoModel
from app.schemas.wing import Spare as SpareModel


def create_airfoil(airfoil_model: AirfoilModel) -> Airfoil | None:
    return Airfoil(**airfoil_model.__dict__.copy()) if airfoil_model is not None else None


def create_servo(servo_model: ServoModel) -> Servo | int | None:
    if type(servo_model) is int:
        return servo_model
    elif servo_model is None:
        return None
    return Servo(**servo_model.__dict__.copy())


def create_trailing_edge_device(ted_model: TrailingEdgeDeviceModel) -> TrailingEdgeDevice | None:
    if ted_model is None:
        return None
    initialization_dict = ted_model.__dict__.copy()
    initialization_dict['servo'] = create_servo(ted_model.servo)
    return TrailingEdgeDevice(**initialization_dict)


def create_spare(spare_model: SpareModel) -> Spare | None:
    return Spare(**spare_model.__dict__.copy()) if spare_model is not None else None

def create_segment(segment_model: SegmentModel) -> dict | None:
    if segment_model is None:
        return None
    initialization_dict = segment_model.__dict__.copy()
    initialization_dict['sweep_is_angle'] = False
    initialization_dict['tip_airfoil'] = create_airfoil(segment_model.tip_airfoil)
    if segment_model.spare_list is not None:
        initialization_dict['spare_list'] = *[create_spare(spare) for spare in segment_model.spare_list],
    else:
        initialization_dict['spare_list'] = None
    initialization_dict['trailing_edge_device'] = create_trailing_edge_device(segment_model.trailing_edge_device) if segment_model.trailing_edge_device is not None else None

    del initialization_dict['root_airfoil']
    del initialization_dict['tip_type']

    return initialization_dict


def create_tip_segment(segment_model: SegmentModel) -> dict | None:
    if segment_model is None:
        return None
    initialization_dict = segment_model.__dict__.copy()
    initialization_dict['tip_airfoil'] = create_airfoil(segment_model.tip_airfoil)

    del initialization_dict['root_airfoil']
    del initialization_dict['spare_list']
    del initialization_dict['trailing_edge_device']

    return initialization_dict


def create_wing_configuration(wing_model: WingModel) -> WingConfiguration:
    """ Create a WingConfiguration from a Wing model object
    """
    # creating root segment
    wing_config: WingConfiguration = WingConfiguration(**create_root_segment(wing_model))

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
    root_segment: SegmentModel = wing_model.segments[0]
    initialization_dict = root_segment.__dict__.copy()

    initialization_dict['nose_pnt'] = (
        wing_model.nose_pnt[0],
        wing_model.nose_pnt[1],
        wing_model.nose_pnt[2]
    )
    initialization_dict['sweep_is_angle'] = False
    initialization_dict['root_airfoil'] = create_airfoil(root_segment.root_airfoil)
    initialization_dict['tip_airfoil'] = create_airfoil(root_segment.tip_airfoil)
    initialization_dict['spare_list'] = [create_spare(spare) for spare in root_segment.spare_list if spare is not None] if root_segment.spare_list is not None else None
    initialization_dict['trailing_edge_device'] = create_trailing_edge_device(root_segment.trailing_edge_device) if root_segment.trailing_edge_device is not None else None

    del initialization_dict['tip_type']

    return initialization_dict