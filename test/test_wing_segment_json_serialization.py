import os
import sys
import json
from pathlib import Path

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cad_designer.airplane.aircraft_topology.wing.WingSegment import WingSegment
from cad_designer.airplane.aircraft_topology.wing.Airfoil import Airfoil

def test_simple_wing_segment_serialization():
    """Test serialization and deserialization of a simple WingSegment."""
    print("Testing simple WingSegment serialization and deserialization...")
    
    # Create a simple root airfoil
    root_airfoil = Airfoil(airfoil="components/airfoils/naca0012.dat", chord=100, incidence=0)
    
    # Create a simple tip airfoil
    tip_airfoil = Airfoil(airfoil="components/airfoils/naca0012.dat", chord=50, incidence=2)
    
    # Create a wing segment with minimal dependencies
    wing_segment = WingSegment(
        root_airfoil=root_airfoil,
        length=1000,
        sweep=100,
        tip_airfoil=tip_airfoil
    )
    
    # Create output directory if it doesn't exist
    output_dir = Path("./tmp/test_wing_segment_json_serialization")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Serialize to JSON
    json_path = output_dir / "simple_wing_segment.json"
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
    
    print("Test completed successfully!")

if __name__ == "__main__":
    test_simple_wing_segment_serialization()