import os
import sys
import json
from pathlib import Path

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cad_designer.airplane.aircraft_topology.wing.WingSegment import WingSegment
from cad_designer.airplane.aircraft_topology.wing.Airfoil import Airfoil
from cad_designer.airplane.aircraft_topology.wing.Spare import Spare
from cad_designer.airplane.aircraft_topology.wing.TrailingEdgeDevice import TrailingEdgeDevice

def test_wing_segment_serialization():
    """Test serialization and deserialization of WingSegment."""
    print("Testing WingSegment serialization and deserialization...")

    # Create a simple root airfoil
    root_airfoil = Airfoil(airfoil="components/airfoils/naca0012.dat", chord=100, incidence=0)

    # Create a simple tip airfoil
    tip_airfoil = Airfoil(airfoil="components/airfoils/naca0012.dat", chord=50, incidence=2)

    # Create a trailing edge device
    trailing_edge_device = TrailingEdgeDevice(
        name="flap", 
        rel_chord_root=0.7, 
        rel_chord_tip=0.7, 
        symmetric=True
    )

    # Create a spare
    spare = Spare(
        spare_support_dimension_width=10,
        spare_support_dimension_height=5,
        spare_position_factor=0.25,
        spare_mode="standard"
    )

    # Create a wing segment
    wing_segment = WingSegment(
        root_airfoil=root_airfoil,
        length=1000,
        sweep=100,
        sweep_is_angle=False,
        tip_airfoil=tip_airfoil,
        spare_list=[spare],
        trailing_edge_device=trailing_edge_device,
        number_interpolation_points=50,
        tip_type=None,
        wing_segment_type='segment'
    )

    # Create output directory if it doesn't exist
    output_dir = Path("./tmp/test_wing_segment_serialization")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Serialize to JSON
    json_path = output_dir / "wing_segment.json"
    with open(json_path, 'w') as f:
        json.dump(wing_segment.__getstate__(), f, indent=4)
    print(f"Saved wing segment to {json_path}")

    # Deserialize from JSON
    with open(json_path, 'r') as f:
        data = json.load(f)
    deserialized_wing_segment = WingSegment.from_json_dict(data)
    print(f"Loaded wing segment from {json_path}")

    # Verify properties
    print(f"Original length: {wing_segment.length}, Deserialized length: {deserialized_wing_segment.length}")
    print(f"Original sweep: {wing_segment.sweep}, Deserialized sweep: {deserialized_wing_segment.sweep}")
    print(f"Original sweep_angle: {wing_segment.sweep_angle}, Deserialized sweep_angle: {deserialized_wing_segment.sweep_angle}")
    print(f"Original root_airfoil.chord: {wing_segment.root_airfoil.chord}, Deserialized root_airfoil.chord: {deserialized_wing_segment.root_airfoil.chord}")
    print(f"Original tip_airfoil.chord: {wing_segment.tip_airfoil.chord}, Deserialized tip_airfoil.chord: {deserialized_wing_segment.tip_airfoil.chord}")
    print(f"Original trailing_edge_device.name: {wing_segment.trailing_edge_device.name}, Deserialized trailing_edge_device.name: {deserialized_wing_segment.trailing_edge_device.name}")
    print(f"Original spare_list[0].spare_support_dimension_width: {wing_segment.spare_list[0].spare_support_dimension_width}, Deserialized spare_list[0].spare_support_dimension_width: {deserialized_wing_segment.spare_list[0].spare_support_dimension_width}")
    print(f"Original spare_list[0].spare_support_dimension_height: {wing_segment.spare_list[0].spare_support_dimension_height}, Deserialized spare_list[0].spare_support_dimension_height: {deserialized_wing_segment.spare_list[0].spare_support_dimension_height}")

    print("Test completed successfully!")

if __name__ == "__main__":
    test_wing_segment_serialization()
