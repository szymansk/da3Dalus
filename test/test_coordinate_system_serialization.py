import os
import sys
import json
from pathlib import Path

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cad_designer.airplane.aircraft_topology.wing.CoordinateSystem import CoordinateSystem

def test_coordinate_system_serialization():
    """Test serialization and deserialization of a CoordinateSystem."""
    print("Testing CoordinateSystem serialization and deserialization...")
    
    # Create a coordinate system
    coordinate_system = CoordinateSystem(
        xDir=[1, 0, 0],
        yDir=[0, 1, 0],
        zDir=[0, 0, 1],
        origin=[10, 20, 30]
    )
    
    # Create output directory if it doesn't exist
    output_dir = Path("./tmp/test_coordinate_system_serialization")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Serialize to JSON
    json_path = output_dir / "coordinate_system.json"
    coordinate_system.save_to_json(str(json_path))
    print(f"Saved coordinate system to {json_path}")
    
    # Deserialize from JSON
    deserialized_coordinate_system = CoordinateSystem.from_json(str(json_path))
    print(f"Loaded coordinate system from {json_path}")
    
    # Verify properties
    print(f"Original xDir: {coordinate_system.xDir}, Deserialized xDir: {deserialized_coordinate_system.xDir}")
    print(f"Original yDir: {coordinate_system.yDir}, Deserialized yDir: {deserialized_coordinate_system.yDir}")
    print(f"Original zDir: {coordinate_system.zDir}, Deserialized zDir: {deserialized_coordinate_system.zDir}")
    print(f"Original origin: {coordinate_system.origin}, Deserialized origin: {deserialized_coordinate_system.origin}")
    print(f"Original euler_xyz: {coordinate_system.euler_xyz}, Deserialized euler_xyz: {deserialized_coordinate_system.euler_xyz}")
    
    # Test with a rotated coordinate system
    print("\nTesting with a rotated coordinate system...")
    rotated_coordinate_system = CoordinateSystem(
        xDir=[0, 1, 0],
        yDir=[-1, 0, 0],
        zDir=[0, 0, 1],
        origin=[5, 10, 15]
    )
    
    # Serialize to JSON
    json_path = output_dir / "rotated_coordinate_system.json"
    rotated_coordinate_system.save_to_json(str(json_path))
    print(f"Saved rotated coordinate system to {json_path}")
    
    # Deserialize from JSON
    deserialized_rotated_coordinate_system = CoordinateSystem.from_json(str(json_path))
    print(f"Loaded rotated coordinate system from {json_path}")
    
    # Verify properties
    print(f"Original xDir: {rotated_coordinate_system.xDir}, Deserialized xDir: {deserialized_rotated_coordinate_system.xDir}")
    print(f"Original yDir: {rotated_coordinate_system.yDir}, Deserialized yDir: {deserialized_rotated_coordinate_system.yDir}")
    print(f"Original zDir: {rotated_coordinate_system.zDir}, Deserialized zDir: {deserialized_rotated_coordinate_system.zDir}")
    print(f"Original origin: {rotated_coordinate_system.origin}, Deserialized origin: {deserialized_rotated_coordinate_system.origin}")
    print(f"Original euler_xyz: {rotated_coordinate_system.euler_xyz}, Deserialized euler_xyz: {deserialized_rotated_coordinate_system.euler_xyz}")
    
    print("Test completed successfully!")

if __name__ == "__main__":
    test_coordinate_system_serialization()