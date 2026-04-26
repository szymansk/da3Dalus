from cad_designer.airplane.aircraft_topology.components import Servo
from cad_designer.airplane.aircraft_topology.wing import WingConfiguration, TrailingEdgeDevice, Spare
from cad_designer.airplane.aircraft_topology.wing import Airfoil
from app.schemas.wing import Wing as WingModel
from app.schemas.wing import Airfoil as AirfoilModel
from app.schemas.wing import Segment as SegmentModel
from app.schemas.wing import TrailingEdgeDevice as TrailingEdgeDeviceModel
from app.schemas.wing import Servo as ServoModel
from app.schemas.wing import Spare as SpareModel
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[2]
_AIRFOILS_DIR = _REPO_ROOT / "components" / "airfoils"


_airfoil_map: dict[str, Path] | None = None


def _get_airfoil_map() -> dict[str, Path]:
    """Build a lowercase→Path lookup map for components/airfoils/ (cached)."""
    global _airfoil_map
    if _airfoil_map is None:
        if _AIRFOILS_DIR.is_dir():
            _airfoil_map = {
                e.name.lower(): e
                for e in _AIRFOILS_DIR.iterdir()
                if e.is_file() and e.suffix.lower() == ".dat"
            }
        else:
            _airfoil_map = {}
    return _airfoil_map


def _find_airfoil_case_insensitive(name: str) -> Path | None:
    """Find an airfoil .dat file by name, case-insensitive.

    Accepts bare names ("mh32", "MH32"), names with extension
    ("mh32.dat", "MH32.DAT"), or paths containing "components/airfoils/".
    """
    if not name.lower().endswith(".dat"):
        name = f"{name}.dat"
    return _get_airfoil_map().get(name.lower())


def _resolve_airfoil_reference(airfoil_reference: str) -> str:
    if not airfoil_reference or "://" in airfoil_reference:
        return airfoil_reference

    # 1. Exact path exists (absolute or relative)
    reference_path = Path(airfoil_reference)
    if reference_path.is_absolute() and reference_path.exists():
        return str(reference_path)
    if reference_path.exists():
        return str(reference_path.resolve())

    # 2. Extract filename from paths like "./components/airfoils/mh32.dat"
    normalized = airfoil_reference.replace("\\", "/")
    marker = "components/airfoils/"
    if marker in normalized:
        bare_name = normalized.split(marker, maxsplit=1)[1]
    else:
        bare_name = Path(normalized).name

    # 3. Case-insensitive lookup in components/airfoils/
    found = _find_airfoil_case_insensitive(bare_name)
    if found:
        return str(found)

    # 4. Try repo-relative path
    repo_relative = (_REPO_ROOT / airfoil_reference).resolve()
    if repo_relative.exists():
        return str(repo_relative)

    return airfoil_reference


def create_airfoil(airfoil_model: AirfoilModel) -> Airfoil | None:
    if airfoil_model is None:
        return None
    initialization_dict = airfoil_model.__dict__.copy()
    initialization_dict["airfoil"] = _resolve_airfoil_reference(initialization_dict["airfoil"])
    return Airfoil(**initialization_dict)


def create_servo(servo_model: ServoModel) -> Servo | int | None:
    if type(servo_model) is int:
        return servo_model
    elif servo_model is None:
        return None
    d = servo_model.__dict__.copy()
    d.pop("component_id", None)  # API-only field, not in topology Servo
    return Servo(**d)


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
    initialization_dict.pop('wing_segment_type', None)

    return initialization_dict


def create_tip_segment(segment_model: SegmentModel) -> dict | None:
    if segment_model is None:
        return None
    initialization_dict = segment_model.__dict__.copy()
    initialization_dict['tip_airfoil'] = create_airfoil(segment_model.tip_airfoil)

    del initialization_dict['root_airfoil']
    del initialization_dict['spare_list']
    del initialization_dict['trailing_edge_device']
    initialization_dict.pop('wing_segment_type', None)

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
    initialization_dict['symmetric'] = getattr(wing_model, 'symmetric', True)
    initialization_dict['sweep_is_angle'] = False
    initialization_dict['root_airfoil'] = create_airfoil(root_segment.root_airfoil)
    initialization_dict['tip_airfoil'] = create_airfoil(root_segment.tip_airfoil)
    initialization_dict['spare_list'] = [create_spare(spare) for spare in root_segment.spare_list if spare is not None] if root_segment.spare_list is not None else None
    initialization_dict['trailing_edge_device'] = create_trailing_edge_device(root_segment.trailing_edge_device) if root_segment.trailing_edge_device is not None else None

    del initialization_dict['tip_type']
    initialization_dict.pop('wing_segment_type', None)

    return initialization_dict
